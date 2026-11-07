enter:
    #!/bin/bash
    source "./scripts/ansible-homelab.sh"
    node=$(ansible_pick_node | sed 's/^homelab_nodes_host__//')
    host=$(ansible_get_var homelab_nodes_host__${node} ansible_host)
    ssh "homelab@${host}"

console:
    #!/bin/bash
    source "./scripts/ansible-homelab.sh"
    nodes=$(ansible_pick_nodes)
    ansible-console --limit "${nodes}"

ping:
    #!/bin/bash
    source "./scripts/ansible-homelab.sh"
    nodes=$(ansible_pick_nodes)
    ansible -mansible.builtin.ping group_homelab_nodes_hosts --limit "${nodes}"

prune:
    #!/bin/bash
    source "./scripts/ansible-homelab.sh"
    nodes=$(ansible_pick_nodes)
    ansible-playbook homelab.nodes.nodes_docker_prune --limit "${nodes}"
