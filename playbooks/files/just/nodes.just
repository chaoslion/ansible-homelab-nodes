workspace := invocation_directory()

enter:
    #!/bin/bash
    source "ansible-homelab.sh"
    cd {{ workspace }}
    node=$(ansible_pick_node | sed 's/^homelab_nodes_host__//')
    host=$(ansible_get_var homelab_nodes_host__${node} ansible_host)
    ssh "homelab@${host}"

console:
    #!/bin/bash
    source "ansible-homelab.sh"
    cd {{ workspace }}
    nodes=$(ansible_pick_nodes)
    ansible-console --limit "${nodes}"

ping:
    #!/bin/bash
    source "ansible-homelab.sh"
    cd {{ workspace }}
    nodes=$(ansible_pick_nodes)
    ansible -mansible.builtin.ping group_homelab_nodes_hosts --limit "${nodes}"

prune:
    #!/bin/bash
    source "ansible-homelab.sh"
    cd {{ workspace }}
    nodes=$(ansible_pick_nodes)
    ansible-playbook homelab.nodes.nodes_docker_prune --limit "${nodes}"
