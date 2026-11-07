workspace := invocation_directory()

nodes:
    #!/bin/bash
    source "ansible-homelab.sh"
    cd {{ workspace }}
    nodes=$(ansible_pick_nodes)
    ansible-playbook homelab.nodes.nodes_provision --limit "${nodes}"
    ansible-playbook homelab.nodes.nodes_setup --limit "${nodes}"

projects:
    #!/bin/bash
    source "ansible-homelab.sh"
    cd {{ workspace }}
    projects=$(ansible_pick_projects)
    ansible-playbook homelab.nodes.projects_provision --limit "${projects}"

projects-bump:
    #!/bin/bash
    source "ansible-homelab.sh"
    cd {{ workspace }}
    projects=$(ansible_pick_projects)
    ansible-playbook homelab.nodes.projects_provision --tag bump --limit "${projects}"

images:
    #!/bin/bash
    source "ansible-homelab.sh"
    cd {{ workspace }}
    images=$(ansible_pick_inventories group_homelab_nodes_images homelab_nodes_image__)
    ansible-playbook homelab.nodes.images_provision --limit "${images}"
    docker image prune -af
