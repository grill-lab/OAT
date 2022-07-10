#!/bin/bash

sudo apt-get update

sudo apt install --yes apt-transport-https ca-certificates curl gnupg2 software-properties-common unzip
curl -fsSL https://download.docker.com/linux/debian/gpg | sudo apt-key add -
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/debian $(lsb_release -cs) stable"
sudo apt update
sudo apt install --yes docker-ce docker-compose-plugin
# Build the basic image for all containers
sudo docker compose build grill_common