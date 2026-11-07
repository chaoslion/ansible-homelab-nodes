download:
    #!/bin/bash
    source "./scripts/ansible-homelab.sh"
    projects=$(ansible_pick_projects)
    ansible-playbook homelab.nodes.projects_download --limit "${projects}"

upload:
    #!/bin/bash
    source "./scripts/ansible-homelab.sh"
    projects=$(ansible_pick_projects)
    ansible-playbook homelab.nodes.projects_upload --limit "${projects}"

up:
    #!/bin/bash
    source "./scripts/ansible-homelab.sh"
    projects=$(ansible_pick_projects)
    ansible-playbook homelab.nodes.projects_up --limit "${projects}"

down:
    #!/bin/bash
    source "./scripts/ansible-homelab.sh"
    projects=$(ansible_pick_projects)
    ansible-playbook homelab.nodes.projects_down --limit "${projects}"

enter:
    #!/bin/bash
    source "./scripts/ansible-homelab.sh"
    project=$(ansible_pick_project)
    node=$(ansible_get_var ${project} vars_host_homelab_nodes_projects__node_name)
    workspace=$(ansible_get_var ${project} vars_host_homelab_nodes_projects__workspace)
    host=$(ansible_get_var homelab_nodes_host__${node} ansible_host)
    ssh -t "homelab@${host}" "cd ${workspace} && exec bash -l"
