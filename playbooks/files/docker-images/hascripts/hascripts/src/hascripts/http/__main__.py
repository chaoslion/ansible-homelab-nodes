# PYTHON_ARGCOMPLETE_OK
import argparse
import asyncio
import contextlib
import os
from datetime import datetime, timezone
from pathlib import Path

import aiohttp
import aiohttp.web
import aiohttp_jinja2
import jinja2
import pydantic

import hascripts.apps
from hascripts.cli import (
    setup_logging_and_parse_args,
)
from hascripts.scanner import (
    AppsModuleHiddenException,
    AppsModuleInvalidException,
    AppsModuleValidationException,
    AppSocket,
    AppsScanner,
)
from hascripts.validate import ConfigModel


class RouteIndexPostRequestConfig(ConfigModel):
    check: bool = False
    force: bool = False


APPKEY_APPS_SYNC_SCANNER = aiohttp.web.AppKey("APPS_SYNC_SCANNER", AppsScanner)
APPKEY_APPS_SYNC_COOLDOWN = aiohttp.web.AppKey("APPS_SYNC_COOLDOWN", int)


# @aiohttp_jinja2.template("index.html.j2")
async def route_index(request):
    scanner: AppsScanner = request.app[APPKEY_APPS_SYNC_SCANNER]
    return aiohttp.web.json_response({"items": list(scanner.cache)})


@contextlib.asynccontextmanager
async def route_index_post_response(syncfile: Path):
    response = aiohttp.web.StreamResponse(
        status=200,
        headers={"Content-Type": "text/plain"},
    )
    try:
        yield response
    finally:
        syncfile.unlink(missing_ok=True)
        await response.write_eof()


async def route_index_post(request: aiohttp.web.Request):
    if request.content_type != "application/x-www-form-urlencoded":
        raise aiohttp.web.HTTPUnsupportedMediaType(text="invalid content-type")

    try:
        request_payload = RouteIndexPostRequestConfig.model_validate(
            dict(await request.post())
        )
    except pydantic.ValidationError as exc:
        raise aiohttp.web.HTTPBadRequest(text=str(exc))

    scanner: AppsScanner = request.app[APPKEY_APPS_SYNC_SCANNER]
    supervisord_apps_sync_cooldown: int = request.app[APPKEY_APPS_SYNC_COOLDOWN]
    supervisord_apps_sync_path: Path = scanner.config.supervisor.sync
    supervisord_apps_sync_path_last: Path = scanner.config.supervisor.sync_last

    async with route_index_post_response(supervisord_apps_sync_path) as response:
        await response.prepare(request)

        try:
            supervisord_apps_sync_path.touch(exist_ok=False)
        except FileExistsError:
            await response.write("sync already running\n".encode())
            return response

        for app_module_info in scanner.scan():
            try:
                app_module_info.parse()
            except AppsModuleHiddenException:
                await response.write(
                    f"module hidden: {app_module_info.name}\n".encode()
                )
                continue
            except AppsModuleValidationException as exc:
                await response.write(
                    f"module invalid: {app_module_info.name}\n".encode()
                )
                await response.write(str(exc).strip().encode())
                await response.write("\n".encode())
                continue
            except AppsModuleInvalidException as exc:
                await response.write(
                    f"module hidden: {app_module_info.name}\n".encode()
                )
                await response.write(str(exc).strip().encode())
                await response.write("\n".encode())
                continue

            await response.write(f"module valid: {app_module_info.name}\n".encode())

        if request_payload.check:
            return response

        if not request_payload.force:
            sync_last_timestamp = 0
            if supervisord_apps_sync_path_last.exists():
                sync_last_timestamp = float(supervisord_apps_sync_path_last.read_text())

            now_timestamp = datetime.now(tz=timezone.utc).timestamp()
            timestamp_diff = now_timestamp - sync_last_timestamp
            if timestamp_diff < supervisord_apps_sync_cooldown:
                countdown = supervisord_apps_sync_cooldown - timestamp_diff
                await response.write(f"sync ratelimit: {countdown:.2f} s\n".encode())
                return response

        await response.write("purge modules\n".encode())
        scanner.supervisor_purge()

        for app_module_name, config_apps in scanner.cache.items():
            await response.write(f"write module: {app_module_name}\n".encode())
            scanner.supervisor_write(
                app_module_name,
                config_apps,
            )

        await response.write("reload modules\n".encode())
        process = await asyncio.create_subprocess_exec(
            "/usr/local/bin/supervisorctl",
            "update",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        if process.stdout is not None:
            async for line in process.stdout:
                await response.write(line)
        await process.wait()

        now_timestamp = datetime.now(tz=timezone.utc).timestamp()
        supervisord_apps_sync_path_last.write_text(f"{now_timestamp}")

        return response


async def route_app_index(request):
    scanner: AppsScanner = request.app[APPKEY_APPS_SYNC_SCANNER]
    url_module = request.match_info.get("module")
    if url_module not in scanner.cache:
        raise aiohttp.web.HTTPBadRequest(text=f"unknown module: {url_module}")
    return aiohttp.web.json_response({"items": list(scanner.cache[url_module].apps)})


async def route_app_proxy(request):
    scanner: AppsScanner = request.app[APPKEY_APPS_SYNC_SCANNER]
    url_module = request.match_info.get("module")
    if url_module not in scanner.cache:
        raise aiohttp.web.HTTPBadRequest(text=f"unknown module: {url_module}")

    url_app = request.match_info.get("app")
    if url_app not in scanner.cache[url_module].apps:
        raise aiohttp.web.HTTPBadRequest(text=f"unknown module: {url_app}")

    url_prefix = f"{url_module}-{url_app}"
    app_socket: AppSocket = AppSocket(
        url_prefix,
        scanner.config.socket_path,
    )
    connector = aiohttp.UnixConnector(path=str(app_socket.path))
    async with aiohttp.ClientSession(connector=connector) as session:
        target_url = request.path_qs.replace(
            f"/{url_module}/{url_app}",
            "http://localhost",
        )
        async with session.request(
            method=request.method,
            url=target_url,
            headers=request.headers,
            data=request.content,
        ) as resp:
            proxy_resp = aiohttp.web.StreamResponse(
                status=resp.status,
                headers=resp.headers,
            )
            await proxy_resp.prepare(request)

            async for chunk in resp.content.iter_any():
                await proxy_resp.write(chunk)

            return proxy_resp


async def main_async(config: Path | None = None, data: Path | None = None):
    app = aiohttp.web.Application(
        middlewares=[
            aiohttp.web.normalize_path_middleware(
                append_slash=True,
                merge_slashes=True,
            )
        ]
    )
    aiohttp_jinja2.setup(
        app,
        loader=jinja2.PackageLoader(
            package_name="hascripts",
        ),
    )
    app.add_routes(
        [
            aiohttp.web.get("/", route_index),
            aiohttp.web.post("/", route_index_post),
            aiohttp.web.get("/{module}/", route_app_index),
            aiohttp.web.route("*", "/{module}/{app}/{path:.*}", route_app_proxy),
        ]
    )

    app[APPKEY_APPS_SYNC_SCANNER] = AppsScanner(hascripts.apps)
    app[APPKEY_APPS_SYNC_SCANNER].supervisor_purge(clean=True)
    app[APPKEY_APPS_SYNC_COOLDOWN] = 15
    return app


def main():
    argsp = argparse.ArgumentParser()
    argsp.add_argument("-p", "--port", type=int, default=8080)
    argsp.add_argument("--dev", action="store_true")
    with setup_logging_and_parse_args(argsp, "hascripts-http") as (args, logger):
        if args.dev:
            aiohttp.web.run_app(main_async())
        else:
            os.execvp(
                "/usr/local/bin/gunicorn",
                [
                    "gunicorn",
                    "hascripts.http.__main__:main_async",
                    "--bind",
                    f"0.0.0.0:{args.port}",
                    "--worker-class",
                    "aiohttp.GunicornWebWorker",
                ],
            )


if __name__ == "__main__":
    main()
