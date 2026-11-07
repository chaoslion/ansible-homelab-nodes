set -euxo pipefail
export FZF_DEFAULT_OPTS="--bind 'ctrl-a:select-all'"

function ansible_get_var() {
    host=$1
    name=$2
    result=$(ansible-inventory --host ${host} | jq -r ".$name")
    if test -z "$result"; then
        return 1
    else
        echo $result
    fi
}

function ansible_pick_inventories() {
    group=$1
    prefix=$2
    result=$(ansible --list-hosts $group | tail -n +2 | sort | fzf -m --delimiter="${prefix}" --with-nth=2 | sed 's/^[[:space:]]*//' | tr '\n' ',')
    if test -z "$result"; then
        return 1
    else
        echo $result
    fi
}

function ansible_pick_inventory() {
    group=$1
    prefix=$2
    result=$(ansible --list-hosts $group | tail -n +2 | sort | fzf --delimiter="${prefix}" --with-nth=2 | sed 's/^[[:space:]]*//')
    if test -z "$result"; then
        return 1
    else
        echo $result
    fi
}

function ansible_pick_node() {
    ansible_pick_inventory group_homelab_nodes_hosts homelab_nodes_host__
}

function ansible_pick_nodes() {
    ansible_pick_inventories group_homelab_nodes_hosts homelab_nodes_host__
}

function ansible_pick_project() {
    ansible_pick_inventory group_homelab_nodes_projects homelab_nodes_host__
}

function ansible_pick_projects() {
    ansible_pick_inventories group_homelab_nodes_projects homelab_nodes_host__
}

function ansible_projects_bump() {
    ansible-playbook homelab.nodes.projects_provision -tbump "$@"
}
