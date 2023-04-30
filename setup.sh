#!/bin/bash
#
# OAT setup script. Run this before attempting to build any of
# of the Docker images (see README.md for more information).

set -o errexit   # abort on nonzero exitstatus
set -o nounset   # abort on unbound variable
set -o pipefail  # don't hide errors within pipes

declare exit_ok=false

exit_handler() {
    # Handles the bash EXIT signal
    if [[ "${exit_ok}" == false ]]
    then
        echo -e "\n\n*** OAT setup was NOT successfully completed!"
        echo "*** Check the output above for error messages"
    else
        echo -e "\n\nOAT setup successfully completed!"
    fi
}

check_command_exists() {
    # Check if a given command is executable
    #
    # Args:
    #   $1 = name of command, e.g. "apt-get"
    #
    # Returns: 0 if command is available, 1 if it isn't
    command -v "${1}" &> /dev/null
}

install_deps_apt() {
    # If we're on a system with apt-get available, try
    # installing the required dependencies automatically.
    # This basically just runs the recommended steps from
    # https://docs.docker.com/engine/install/ubuntu/#install-using-the-repository
    # and so will only work on Ubuntu systems.
    #
    # Returns: ignored (will exit on error)
    sudo apt-get update
    sudo apt-get install --yes apt-transport-https ca-certificates curl gnupg software-properties-common unzip lsb-release
    sudo mkdir -m 0755 -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    sudo apt update
    sudo apt-get install --yes docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    echo "> OAT dependency installation was successful!"
}

check_deps() {
    # Check for each of the basic binaries required to setup and build
    # OAT, displaying an error and aborting if any are not found
    #
    # Returns: ignored (will exit on error)
    declare -ar commands=(docker unzip curl)
    for c in "${commands[@]}"
    do
        echo -n "> Checking for ${c}..."
        if check_command_exists "${c}"
        then
            echo "OK!"
        else
            echo "not found! Please install it and re-run the script."
            exit 1
        fi
    done

    # check for docker compose (vs docker-compose) a bit differently
    echo -n "> Checking for Docker Compose plugin..."
    if sudo docker compose version &> /dev/null
    then
        echo "OK!"
    else
        echo "not found! Please install it and re-run the script."
        exit 1
    fi
}

download_oat_files() {
    # Download the model/index/lookup files for OAT
    #
    # Will NOT attempt to download again if local files already exist
    #
    # Returns: ignored (will exit on error)

    declare -r out_path="./shared/file_system"
    declare -ra names=(indexes lookup_files)

    for n in "${names[@]}"
    do
        if [[ -d "${out_path}/${n}" ]]
        then
            echo "> Path ${out_path}/${n} already exists, skipping download"
        else
            echo "> Downloading ${n}..."
            curl --create-dirs -o "${out_path}/${n}.zip" \
                "https://open-grill.s3.amazonaws.com/data/${n}.zip"
            # -d = extract files into the given directory,
            unzip -d "${out_path}" "${out_path}/${n}.zip"
        fi
    done

    if [[ -d "${out_path}/models" ]]
    then
    # sync command currently not working so removing the files and fetching everything
    # as a workaround for syncing updates
        echo "> Path ${out_path}/models already exists, syncing updates"
        rm -r "${out_path}/models"
        aws s3 cp "s3://model-classifiers" "${out_path}" --recursive
    else
        echo "> Downloading models..."
        aws s3 cp "s3://model-classifiers" "${out_path}" --recursive
    fi

}

oat_setup() {
    # Run the setup process
    #
    # Args:
    #   $1 = true if auto-install step should be skipped, false otherwise
    #   $2 = true if user confirmation required for auto-install, false otherwise
    #
    # Returns: ignored (will exit on error)

    # set up exit handler before beginning to install things
    trap exit_handler EXIT

    # if apt-get is available, offer to try automatically installing
    # the required dependencies as a first step
    if [[ "${1}" = true ]]
    then
        if check_command_exists "apt-get"
        then
            if [[ "${2}" = true ]]
            then
                # waits for a single character input (no return/enter required)
                read -p "> Attempt to install dependencies automatically? (y/n)? " -n 1 -r
                echo
                if [[ "${REPLY}" =~ ^[Yy]$ ]]
                then
                    echo "> Installing dependencies via apt-get"
                    install_deps_apt
                fi
            else
                echo "> Installing dependencies via apt-get"
                install_deps_apt
            fi
        fi
    else
        echo "> Skipping dependency installation step"
    fi

    # check for docker/curl etc
    echo -e "> Checking for required applications...\n"
    check_deps

    if [[ "${3}" = true ]]
    then
      echo "> Downloading OAT model/data files..."
      download_oat_files
    else
      echo "> Skipping downloads!"
    fi

    echo "> Building grill_common image..."
    sudo docker compose build grill_common

    exit_ok=true
}

# default is to check for dependencies
declare check_deps=true
# default is to ask for confirmation before installing anything
declare confirm_deps=true
# default is to download all files
declare download_files=true

# parse any arguments supplied (getopts is a bash builtin)
while getopts "hys" opt
do
    case "${opt}" in
        h)
            echo "Usage: setup.sh [-y] [-s] [-h] [-d]"
            echo -e "\t-s : don't attempt to auto-install any dependencies"
            echo -e "\t-y : don't ask for confirmation before auto-installing dependencies"
            echo -e "\t-h : display this message"
            echo -e "\t-d : skip downloading all available OAT files"
            exit 0
            ;;
        y)
            confirm_deps=false
            ;;
        s)
            check_deps=false
            ;;
        d)
            download_files=false
            ;;
        *)
            echo "Unknown argument!"
            exit 1
    esac
done

oat_setup "${check_deps}" "${confirm_deps}" "${download_files}"

exit 0

