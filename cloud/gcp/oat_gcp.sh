#!/bin/bash
#
# This script can be used to perform some basic management of a GCP VM running
# an OAT deployment (currently just using Docker, not K8S/minikube).
# 
# Supported operations:
#  - create a VM, install OAT dependencies, clone OAT, run setup script
#  - run the tester container against an active deployment
#  - view docker compose logs
#  - run an arbitrary command (using gcloud compute ssh)
#  - delete an existing VM

set -o errexit   # abort on nonzero exitstatus
set -o nounset   # abort on unbound variable
set -o pipefail  # don't hide errors within pipes

# define some friendly names for ANSII colour escape codes
RED="\e[31m"
GREEN="\e[32m"
YELLOW="\e[33m"
BLUE="\e[34m"
PURPLE="\e[35m"
CYAN="\e[36m"
NC="\e[0m"

script_path="$( dirname -- "$0"; )"

# used to determine if the "create" steps finished successfully,
# see exit_handler function
declare deployment_ok=false
# path to temp directory used by "create", helps to clean
# up in exit_handler if an error occurs before it's 
# deleted the normal way
declare tmp=""

exit_handler() {
    # Handler for the bash EXIT signal. The script is set up to exit
    # if a command returns an unsuccessful status code, but depending
    # on when/how that happens it might not be immediately obvious to 
    # the user that something went wrong. 
    #
    # This handler just uses the exit_ok variable to check if the
    # exit event happened prematurely due to an error, and reports
    # that to the user (currently only for the deployment phase, 
    # as that's by far the most complex).
    
    # clean up temp folder if needed
    if [[ -d "${tmp}" ]]
    then
        echo_color "Removing temp folder ${tmp}" "${YELLOW}"
        rm -fr "${tmp}"
    fi

    if [[ "${deployment_ok}" == false ]]
    then
        echo_color "\n\n*** The selected OAT deployment steps were NOT successfully completed!\n" "${YELLOW}"
        echo_color "*** Check the output above for error messages\n" "${YELLOW}"
    else
        echo_color "\n\nThe selected OAT deployment steps were successfully completed!\n" 
    fi
}

echo_color() {
    # Simple wrapper for the echo command to print coloured messages
    #
    # Arguments:
    #   $1 = message to print
    #   $2 = color sequence (optional, defaults to green)
    #
    # Return value: ignored

    # this syntax sets "color" to ${GREEN} if a 2nd argument is not passed
    # to the function
    local color="${2:-${GREEN}}"
    echo -en "${color}${1}${NC}"
}

is_response_not_empty() {
    # Check if a gcloud response is empty or not
    #
    # Arguments:
    #   $1 = response text
    #
    # Return value: 0 if argument is NOT empty, 1 if it IS empty
    [[ -n "${1}" ]]
}

is_gcp_service_enabled() {
    # Checks if a named GCP service is already enabled in the current account/project
    #
    # Arguments:
    #   $1 = name of service to check, e.g. compute.googleapis.com
    #
    # Return value: 0 if service is enabled, 1 if not

    # response to this will be an empty string if the service is not enabled
    resp=$(gcloud services list --enabled --format=yaml --filter=config.name="${1}")
    is_response_not_empty "${resp}"
}

does_vm_exist() {
    # Checks if a named VM is already active in the current account/project
    # 
    # Arguments:
    #   $1 = name of the VM to check
    #   $2 = GCP zone to use
    #
    # Return value: 0 if VM exists, 1 if it doesn't
    resp=$(gcloud compute instances list --zones="${2}" --filter=name="${1}" 2> /dev/null)
    is_response_not_empty "${resp}"
}

check_and_enable_required_services() {
    # For each of the services required for a OAT deployment, check if it 
    # has already been enabled and enable it if required.
    #
    # Return value: ignored (should exit on error)

    for service in "${required_services[@]}"
    do 
        echo_color "> Checking if service ${service} is enabled..." 
        if is_gcp_service_enabled "${service}"
        then
            echo_color "already enabled!\n"
        else 
            echo_color "needs to be enabled\n"
            echo_color "> Enabling service ${service}..."
            gcloud services enable "${service}"
            if is_gcp_service_enabled "${service}"
            then
                echo_color "Service enabled!\n"
            else
                echo_color "Failed to enable service!\n" "${RED}"
                exit 1
            fi
        fi
    done
}

configure_ssh() {
    # check SSH access works for a newly created VM, (and generate a key 
    # silently with --quiet) this might fail if the VM is still booting, 
    # try a few times with a delay between attempts
    #
    # Arguments:
    #   $1 = VM name
    #
    # Return value: 0 if successful, 1 if not
    declare num_retries=4
    declare retry_delay=10
    declare return_code=1

    for (( i=1; i<=num_retries; i++ )) 
    do
        echo "> Generating SSH keys and logging into VM..."
        if ! gcloud compute config-ssh 2>&1
        then
            echo "    (retry #${i}/${num_retries})"
            sleep "${retry_delay}"
        else
            return_code=0
            break
        fi
    done

    return ${return_code}
}

run_ssh_command() {
    # runs a command in a VM over SSH, with auto-retry if it fails since this
    # happens occasionally for no apparent reason
    #
    # Arguments:
    #   $1 = VM name
    #   $2 = GCP zone
    #   $3 = SSH command string
    #   $4 = message to display describing command
    #   $5 = number of times to retry (default 2)
    #   $6 = retry interval (default 3s)
    #
    # Return value: 0 if successful, 1 if not

    declare num_retries=${5:-2}
    declare retry_delay=${6:-3}
    declare return_code=1

    for (( i=1; i<=num_retries; i++ )) 
    do
        echo "${4}"
        if ! gcloud compute ssh "${1}" --zone="${2}" --command "${3}"
        then
            echo_color "    (retry #${i}/${num_retries})" "${YELLOW}"
            sleep "${retry_delay}"
        else
            return_code=0
            break
        fi
    done

    return ${return_code}
}

check_gcloud() {
    # check for gcloud binary
    if ! command -v gcloud &> /dev/null 
    then
        echo_color "> gcloud binary not installed or not on PATH - you might need to install the Google Cloud SDK" "${YELLOW}"
        exit 1
    fi
}

###

# Check if gcloud binary is available 
check_gcloud
declare gcloud_project_id
gcloud_project_id=$(gcloud config get-value project)
echo_color "> Using gcloud project ID: ${gcloud_project_id}\n"

# source user-defined variables (VSCode: if this generates a shellcheck warning 
# add "-x" as a custom argument in the extension settings)
# shellcheck source=cloud/gcp/oat_gcp_config
source "${script_path}/oat_gcp_config"

# require a parameter to be passed to perform any actions
if [[ $# -lt 1 ]]
then
    echo "Usage: oat_gcp_config.sh <create|tests|logs|cmd|destroy>"
    echo ""
    echo "Available commands:"
    echo -e "   ${GREEN}create${NC}: create a new VM instance and start an OAT deployment from a selected branch"
    echo -e "   ${GREEN}tests${NC}: run the tester container on the VM instance"
    echo -e "   ${GREEN}logs${NC}: run 'docker compose logs' on the VM instance"
    echo -e "   ${GREEN}cmd${NC}: run a command in the VM (e.g. ./oat_gcp.sh cmd sudo docker ps)"
    echo -e "   ${GREEN}destroy${NC}: delete an active VM instance"
    exit 0
fi

pushd "${script_path}" > /dev/null

if [[ "${1}" == "destroy" ]]
then
    # dispose of VM
    echo_color "> Deleting VM instance ${vm_name}...\n"
     if ! gcloud compute instances delete "${vm_name}" --zone="${zone}" --quiet 
    then
        echo_color "> Failed to delete VM instance\n" "${YELLOW}"
    fi
elif [[ "${1}" == "create" ]]
then
    # hook up the function above to the bash "EXIT" signal, so it will
    # be called when the script exits (for any reason)
    deployment_ok=false
    trap exit_handler EXIT

    check_and_enable_required_services

    if ! does_vm_exist "${vm_name}" "${zone}"
    then
        echo_color "> Creating a VM instance called ${vm_name}...\n"
        gcloud compute instances create "${vm_name}" \
            --boot-disk-size="${boot_disk_size}" \
            --image="${os_image}" \
            --machine-type="${machine_type}" \
            --zone="${zone}"

        # give the VM a bit of time to start up
        echo_color "> Giving the VM time to start up..."
        sleep 10
        echo_color "> Continuing"
    fi

    if ! configure_ssh "${vm_name}"
    then
        echo_color "> Failed to configure SSH credentials for the VM!\n" "${YELLOW}"
        exit 1
    fi

    # install system packages that we need (retry 4x at 10s intervals, this seems to
    # fail fairly frequently if the VM is newly launched)
    run_ssh_command "${vm_name}" "${zone}" \
        "sudo apt update && sudo apt install -y --no-install-recommends apt-transport-https ca-certificates curl gnupg2 lsb-release software-properties-common unzip" \
        "> Installing system packages for OAT..." \
        4 \
        10

    # install Docker using the repo method: https://docs.docker.com/engine/install/ubuntu/#install-using-the-repository
    gcloud compute scp --zone "${zone}" docker_install.sh "${vm_name}:."
    run_ssh_command "${vm_name}" "${zone}" "/bin/bash docker_install.sh" "> Installing Docker..."
    
    # create a local temporary folder, clone a fresh copy of the repo into it, and
    # check out the selected branch at the same time. then copy the files to the VM,
    # and delete the temp files
    tmp=$(mktemp -d /tmp/oat.XXXXXXXX)
    pushd "${tmp}" > /dev/null
    git clone -b "${branch}" --single-branch git@github.com:grill-lab/OAT.git
    rm -fr OAT/.git
    gcloud compute scp --zone "${zone}" --recurse --compress OAT/* "${vm_name}:."
    popd > /dev/null
    rm -fr "${tmp}"
 
    # run the OAT setup script on the VM *without* using the auto-install
    # dependencies option, that seems to confuse Ubuntu with Debian
    # TODO remove the "echo" after TY2-53 merged
    run_ssh_command "${vm_name}" "${zone}" "echo n | ./setup.sh -s" "> Running OAT setup script..."
    # finally build the images and start the deployment
    run_ssh_command "${vm_name}" "${zone}" "sudo docker compose up -d --build" "> Running docker compose up..."

    # for exit_handler, see above
    deployment_ok=true
elif [[ "${1}" == "tests" ]]
then
    echo_color "> Running the tester container on VM ${vm_name}..."
    run_ssh_command "${vm_name}" "${zone}" "sudo docker compose run tester" ""
elif [[ "${1}" == "logs" ]]
then
    echo_color "> Running 'docker compose logs' on VM ${vm_name}..."
    run_ssh_command "${vm_name}" "${zone}" "sudo docker compose logs" ""
elif [[ "${1}" == "cmd" ]]
then
    declare -ar cmd=("${@:2}")
    echo_color "> Running command '${cmd[*]}' on VM ${vm_name}..."
    run_ssh_command "${vm_name}" "${zone}" "${cmd[*]}" ""
else
    echo_color "Unrecognised parameter \"${1}\"\n"
    exit 1
fi

popd > /dev/null
exit 0
