#!/usr/bin/env python3

import argparse
import datetime
import enum
import logging
import platform
import re
import signal
import subprocess
import threading
import typing
from itertools import chain
from pathlib import Path
from typing import Literal, NamedTuple

import prometheus_client
import yaml


class ProjectScript(NamedTuple):
    command: list[str]
    cwd: str | None
    daily: bool
    host: bool = False


class ContainerInfo(NamedTuple):
    id: str
    name: str
    project: str
    status: str
    started: datetime.datetime


type ContainerSnapshotStatsNames = Literal[
    "cpu",
    "memory",
]

type ContainerSnapshotStats = dict[ContainerSnapshotStatsNames, float]


class ContainerSnapshot(NamedTuple):
    name: str
    running: bool
    stats: ContainerSnapshotStats


class ProjectStatus(enum.IntEnum):
    DOWN = 0
    HEALTHY = 1
    UNHEALTHY = 2
    ERROR = 3


class Project(NamedTuple):
    containers_expected: list[str]
    containers_detected: dict[str, ContainerInfo]
    scripts: dict[str, ProjectScript]

    def healthy(self) -> ProjectStatus:
        if set(self.containers_expected) != set(self.containers_detected.keys()):
            return ProjectStatus.ERROR
        if not self.containers_detected:
            return ProjectStatus.DOWN
        return (
            ProjectStatus.HEALTHY
            if all(
                container.status == "running"
                for container in self.containers_detected.values()
            )
            else ProjectStatus.UNHEALTHY
        )


class StatsSnapshot(NamedTuple):
    lock: threading.Lock
    # project -> list of container snapshots
    snapshots: dict[str, list[ContainerSnapshot]]
    # detected projects
    projects: list[str]
    # project -> health status
    statuses: dict[str, ProjectStatus]
    workspace: Path


class WireguardPeerStats(NamedTuple):
    handshake: float
    tx: int
    rx: int


class WireguardStats(NamedTuple):
    key: str
    peers: dict[str, WireguardPeerStats]


class WireguardCollector(prometheus_client.registry.Collector):
    @typing.override
    def collect(self):
        try:
            result = subprocess.run(
                ["wg", "show", "all", "dump"],
                check=True,
                capture_output=True,
            )
        except FileNotFoundError:
            return

        interfaces: dict[str, WireguardStats] = {}
        current_interface: str | None = None
        current_time = datetime.datetime.now(datetime.UTC)
        for line in result.stdout.decode().splitlines():
            values = line.split()
            if len(values) == 5:
                current_interface = values[0]
                interfaces.update(
                    {current_interface: WireguardStats(key=values[2], peers={})}
                )
            elif len(values) == 9:
                if current_interface is None:
                    raise ValueError("wg error: current_interface is undefined")
                handshake = float(
                    values[5],
                )
                handshake_time_diff = (
                    (current_time.timestamp() - handshake) if handshake else -1
                )

                interfaces[current_interface].peers.update(
                    {
                        values[1]: WireguardPeerStats(
                            handshake=handshake_time_diff,
                            tx=int(
                                values[7],
                            ),
                            rx=int(values[6]),
                        )
                    }
                )
            else:
                raise ValueError(f"wg error: unexpected line: {line}")

            prom_wg_handshake = prometheus_client.metrics_core.GaugeMetricFamily(
                "homelab_nodes_wireguard_peer_handshake_seconds",
                "Homelab Nodes Wireguard Peer Last Handshake Age Seconds",
                labels=[
                    "name",
                    "interface",
                    "peer",
                ],
            )
            prom_wg_tx = prometheus_client.metrics_core.CounterMetricFamily(
                "homelab_nodes_wireguard_peer_tx_bytes_total",
                "Homelab Nodes Wireguard Peer Transmitted Bytes Total",
                labels=[
                    "name",
                    "interface",
                    "peer",
                ],
            )
            prom_wg_rx = prometheus_client.metrics_core.CounterMetricFamily(
                "homelab_nodes_wireguard_peer_rx_bytes_total",
                "Homelab Nodes Wireguard Peer Received Bytes Total",
                labels=[
                    "name",
                    "interface",
                    "peer",
                ],
            )
            for wg_name, wg_stats in interfaces.items():
                for wg_peer_key, wg_peer_stats in wg_stats.peers.items():
                    prom_wg_handshake.add_metric(
                        labels=[
                            wg_name,
                            wg_stats.key,
                            wg_peer_key,
                        ],
                        value=wg_peer_stats.handshake,
                    )
                    prom_wg_tx.add_metric(
                        labels=[
                            wg_name,
                            wg_stats.key,
                            wg_peer_key,
                        ],
                        value=wg_peer_stats.tx,
                    )
                    prom_wg_rx.add_metric(
                        labels=[
                            wg_name,
                            wg_stats.key,
                            wg_peer_key,
                        ],
                        value=wg_peer_stats.rx,
                    )
            yield prom_wg_handshake
            yield prom_wg_tx
            yield prom_wg_rx


class StatsSnapshotCollector(prometheus_client.registry.Collector):
    def __init__(self, stats: StatsSnapshot):
        super().__init__()
        self._stats: StatsSnapshot = stats

    @typing.override
    def collect(self):
        with self._stats.lock:
            yield prometheus_client.metrics_core.GaugeMetricFamily(
                "homelab_nodes_projects_detected",
                "Homelab Nodes Projects Detected",
                value=len(self._stats.projects),
            )
            prom_project_running = prometheus_client.metrics_core.GaugeMetricFamily(
                "homelab_nodes_project_running",
                "Homelab Nodes Project Running Status",
                labels=[
                    "project",
                ],
            )
            for project, snapshots in self._stats.snapshots.items():
                # skip empty projects
                if not snapshots:
                    continue
                running = all(c.running for c in snapshots)
                prom_project_running.add_metric(
                    [project],
                    value=1 if running else 0,
                )
            yield prom_project_running

            prom_project_status = prometheus_client.metrics_core.GaugeMetricFamily(
                "homelab_nodes_project_status",
                "Homelab Nodes Project Status (0=down,1=healthy,2=unhealthy,3=error)",
                labels=[
                    "project",
                ],
            )
            for project, status in self._stats.statuses.items():
                prom_project_status.add_metric([project], value=status.value)
            yield prom_project_status

            project_container_gauges_prefix = "homelab_nodes_project_container"
            project_container_gauges_description_prefix = (
                "Homelab Nodes Project Container"
            )
            project_container_gauges = [
                prometheus_client.metrics_core.GaugeMetricFamily(
                    f"{project_container_gauges_prefix}_running",
                    f"{project_container_gauges_description_prefix} Running Status",
                    labels=[
                        "project",
                        "name",
                    ],
                ),
                prometheus_client.metrics_core.GaugeMetricFamily(
                    f"{project_container_gauges_prefix}_cpu_percent",
                    f"{project_container_gauges_description_prefix} CPU Usage Percent",
                    labels=[
                        "project",
                        "name",
                    ],
                ),
                prometheus_client.metrics_core.GaugeMetricFamily(
                    f"{project_container_gauges_prefix}_memory_percent",
                    f"{project_container_gauges_description_prefix} Memory Usage Percent",
                    labels=[
                        "project",
                        "name",
                    ],
                ),
            ]

            gauge_running, gauge_cpu, gauge_memory = project_container_gauges

            for project, snapshots in self._stats.snapshots.items():
                for snapshot in snapshots:
                    gauge_running.add_metric(
                        [
                            project,
                            snapshot.name,
                        ],
                        value=snapshot.running,
                    )
                    gauge_cpu.add_metric(
                        [
                            project,
                            snapshot.name,
                        ],
                        value=snapshot.stats["cpu"],
                    )
                    gauge_memory.add_metric(
                        [
                            project,
                            snapshot.name,
                        ],
                        value=snapshot.stats["memory"],
                    )
            yield from project_container_gauges


def compose_run(
    workspace: Path,
    argv: list[str],
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "docker",
            "compose",
            "--env-file",
            str(workspace / "homelab.env"),
            *argv,
        ],
        check=True,
        capture_output=True,
        text=True,
        cwd=cwd,
    )


def collect_project_container(
    project: str,
    name: str,
    container: str,
) -> ContainerInfo | None:
    try:
        inspect_result = subprocess.run(
            [
                "docker",
                "container",
                "inspect",
                "--format",
                "{{.ID}},{{.State.Status}},{{.State.StartedAt}}",
                container,
            ],
            capture_output=True,
            check=True,
            text=True,
        )
    except subprocess.CalledProcessError:
        return None
    cid, cstatus, cstarted = inspect_result.stdout.strip().split(",")
    return ContainerInfo(
        cid,
        name,
        project,
        cstatus,
        datetime.datetime.fromisoformat(cstarted),
    )


def collect_projects(logger: logging.Logger, workspace: Path) -> dict[str, Project]:
    projects: dict[str, Project] = {}
    for item in filter(
        lambda i: i.is_dir() and i.name.startswith("homelab-"),
        workspace.iterdir(),
    ):
        compose_config = item / "docker-compose.yaml"
        if not compose_config.is_file():
            continue
        try:
            compose_config_result = compose_run(
                workspace,
                ["-f", str(compose_config), "config", "--format", "json"],
            )
        except subprocess.CalledProcessError:
            logger.warning(f"project is not configured: {item.name}")
            continue

        compose_config_result_values = yaml.load(
            compose_config_result.stdout, Loader=yaml.SafeLoader
        )

        compose_scripts = compose_config_result_values.get("x-homelab-scripts", {})

        containers_expected: list[str] = []
        compose_config_services = compose_config_result_values.get("services", {})
        for (
            compose_config_service_name,
            compose_config_service,
        ) in compose_config_services.items():
            replicas = compose_config_service.get("replicas", 1)
            for i in range(replicas):
                containers_expected.append(
                    f"{item.stem}-{compose_config_service_name}-{i + 1}"
                )

        containers_detected: dict[str, ContainerInfo] = {}
        for container_name in containers_expected:
            container_info = collect_project_container(
                item.stem.replace("homelab-", ""),
                container_name.replace(f"{item.stem}-", ""),
                container_name,
            )
            if container_info is None:
                continue
            containers_detected.update({container_name: container_info})

        projects.update(
            {
                item.name.replace("homelab-", ""): Project(
                    containers_expected=containers_expected,
                    containers_detected=containers_detected,
                    scripts={
                        name: ProjectScript(**config_script)
                        for name, config_script in compose_scripts.items()
                    },
                )
            }
        )
    return projects


STATS_RE_PERCENT = re.compile(r"^(.+)%$")


def collect_projects_container_snapshot_parse(
    cpu: str,
    mem: str,
) -> ContainerSnapshotStats:
    return {
        "cpu": float(re.sub(STATS_RE_PERCENT, r"\1", cpu)),
        "memory": float(re.sub(STATS_RE_PERCENT, r"\1", mem)),
    }


def collect_projects_container_snapshot(
    projects: dict[str, Project],
) -> dict[str, list[ContainerSnapshot]]:
    # mapping of containers
    node_containers_mapping = {
        container.id: container
        for container in list(
            chain.from_iterable(
                [project.containers_detected.values() for project in projects.values()]
            )
        )
    }

    stats_result = subprocess.run(
        [
            "docker",
            "stats",
            "--all",
            "--no-stream",
            "--no-trunc",
            "--format",
            "{{.ID}},{{.CPUPerc}},{{.MemPerc}}",
        ]
        + list(node_containers_mapping),
        capture_output=True,
        check=True,
        text=True,
    )

    result: dict[str, list[ContainerSnapshot]] = {}
    for line in stats_result.stdout.splitlines():
        cs_id, cs_cpu, cs_mem = line.split(",")
        container_info = node_containers_mapping[cs_id]
        if container_info.project not in result:
            result[container_info.project] = []

        result[container_info.project].append(
            ContainerSnapshot(
                name=container_info.name,
                running=container_info.status == "running",
                stats=collect_projects_container_snapshot_parse(
                    cs_cpu,
                    cs_mem,
                ),
            )
        )

    # a container that was expected (declared in compose) but never even
    # got created has no ContainerInfo, since inspect failed in
    # collect_project_container, so it never shows up in `docker stats`
    # output. report it as an explicit down snapshot instead of silently
    # omitting it, otherwise a container that never came up is invisible
    # to alerts that key off homelab_nodes_project_container_running.
    for project_key, project in projects.items():
        missing = set(project.containers_expected) - project.containers_detected.keys()
        for full_name in missing:
            short_name = full_name.replace(f"homelab-{project_key}-", "")
            result.setdefault(project_key, []).append(
                ContainerSnapshot(
                    name=short_name,
                    running=False,
                    stats={
                        "cpu": -1,
                        "memory": -1,
                    },
                )
            )
    return result


def command_metrics_worker(
    logger: logging.Logger,
    terminate: threading.Event,
    snapshot: StatsSnapshot,
):
    initial = True
    while True:
        if not initial and terminate.wait(timeout=10):
            break
        initial = False
        logger.debug("taking project snapshot")
        projects = collect_projects(logger, snapshot.workspace)
        try:
            snapshots = collect_projects_container_snapshot(projects)
        except subprocess.CalledProcessError as e:
            # containers can appear/disappear between the inspect and stats
            logger.warning(
                f"failed to collect project snapshot, retrying next cycle: {e}"
            )
            continue
        statuses = {name: project.healthy() for name, project in projects.items()}

        with snapshot.lock:
            snapshot.snapshots.clear()
            snapshot.snapshots.update(snapshots)
            snapshot.projects.clear()
            snapshot.projects.extend(list(projects))
            snapshot.statuses.clear()
            snapshot.statuses.update(statuses)
        logger.debug("updating project snapshot")


def command_metrics(
    logger: logging.Logger,
    workspace: Path,
    server_bind: str,
    server_port: int,
):
    terminate = threading.Event()
    stats_snapshot = StatsSnapshot(
        threading.Lock(),
        {},
        [],
        {},
        workspace,
    )

    thread_stats = threading.Thread(
        target=command_metrics_worker,
        args=(logger, terminate, stats_snapshot),
    )
    threads = [
        thread_stats,
    ]

    # two registries
    stats_registry = prometheus_client.CollectorRegistry()
    stats_registry.register(StatsSnapshotCollector(stats_snapshot))

    wireguard_registry = prometheus_client.CollectorRegistry()
    wireguard_registry.register(WireguardCollector())

    servers = []
    for index, registry in enumerate([stats_registry, wireguard_registry]):
        server_port_instance = server_port + index
        server, thread = prometheus_client.start_http_server(
            server_port_instance,
            server_bind,
            registry=registry,
        )
        logger.debug(f"metrics server started on port {server_port}")
        servers.append(server)
        threads.append(thread)

    thread_stats.start()

    def __terminate(signum: int, frame):
        logger.debug(f"sig received: {signum}, terminating")
        terminate.set()
        for server in servers:
            server.shutdown()

    signal.signal(
        signal.SIGINT,
        __terminate,
    )
    signal.signal(
        signal.SIGTERM,
        __terminate,
    )
    for thread in threads:
        thread.join()


def command_run_execute(
    logger: logging.Logger,
    workspace: Path,
    project: str,
    container: str,
    script: ProjectScript,
):
    if script.host:
        logger.debug(f"running script on host: {script.command}")
        _ = subprocess.run(script.command, cwd=script.cwd, check=True)
    else:
        argv = ["exec"]
        if script.cwd is not None:
            argv.extend(["-w", script.cwd])
        argv.append(container)
        argv.extend(script.command)
        logger.debug(f"running script on container: {argv}")
        _ = compose_run(workspace, argv, cwd=workspace / f"homelab-{project}")


def main():
    logging_map = logging.getLevelNamesMapping()
    argsp = argparse.ArgumentParser()
    argsp.add_argument(
        "-l",
        "--log-level",
        choices=list(logging_map),
        default=logging.getLevelName(logging.INFO),
    )
    argsp.add_argument(
        "-w", "--workspace", type=Path, default=Path("/home/homelab/workspace")
    )

    argsp_command = argsp.add_subparsers(
        dest="command",
    )

    argsp_metrics = argsp_command.add_parser("metrics")
    argsp_metrics.add_argument("-p", "--port", type=int, default=9050)
    argsp_metrics.add_argument("-b", "--bind", default="0.0.0.0")

    argsp_state = argsp_command.add_parser("state")
    argsp_state.add_argument("-p", "--project")
    argsp_state.add_argument(
        "state",
        choices=[
            "up",
            "down",
            "restart",
            "start",
            "stop",
        ],
    )
    argsp_ls = argsp_command.add_parser("ls")
    argsp_ls.add_argument("-s", "--status", action="store_true")

    argsp_run = argsp_command.add_parser("run")
    argsp_run.add_argument("project")
    argsp_run.add_argument("script")

    argsp_run_daily = argsp_command.add_parser("run-daily")
    argsp_run_daily.add_argument("-p", "--project")

    args = argsp.parse_args()

    logging.basicConfig(
        level=logging_map[args.log_level],
    )
    logging.getLogger("docker").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logger = logging.getLogger("main")

    if args.command is None:
        print(platform.node().replace("node-", ""))
    elif args.command == "metrics":
        command_metrics(logger, args.workspace, args.bind, args.port)
    elif args.command == "state":
        for project in list(collect_projects(logger, args.workspace)):
            if args.project is not None and args.project != project:
                continue
            argv = [args.state]
            if args.state == "up":
                argv.append("-d")
            logger.debug(f"running state command for  {project}: {argv}")
            _ = compose_run(
                args.workspace,
                argv,
                cwd=args.workspace / f"homelab-{project}",
            )
    elif args.command == "run":
        for project, config in collect_projects(logger, args.workspace).items():
            if args.project != project:
                continue
            container, *_ = args.script.split(":", maxsplit=1)
            command_run_execute(
                logger,
                args.workspace,
                project,
                container,
                config.scripts[args.script],
            )
    elif args.command == "run-daily":
        for project, config in collect_projects(logger, args.workspace).items():
            if args.project is not None and args.project != project:
                continue
            for script_name, script in config.scripts.items():
                if not script.daily:
                    continue
                container, *_ = script_name.split(":", maxsplit=1)
                command_run_execute(
                    logger,
                    args.workspace,
                    project,
                    container,
                    script,
                )
    elif args.command == "ls":
        for name, project in dict(
            sorted(collect_projects(logger, args.workspace).items())
        ).items():
            if args.status:
                print(name, project.healthy().name)
            else:
                print(name)


if __name__ == "__main__":
    main()
