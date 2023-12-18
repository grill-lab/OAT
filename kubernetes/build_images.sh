#!/bin/bash

# for the pip cache mounting feature in most Dockerfiles
export DOCKER_BUILDKIT=1

echo "Setting Docker environment to host"
minikube docker-env --unset

echo "Setting docker environment to minikube"
eval "$(minikube docker-env)"

echo "Going to base of repo at ${PWD}"
cd ..

echo "Loading oat_common image into minikube environment (may take a couple of minutes)"
minikube image load --overwrite=false oat_common

echo "Building bob the builder"
docker build -t builder -f builder/Dockerfile .
# assumes "minikube mount" has already been used to attach the shared
# folder from the repo path on the host to "/shared" inside minkube
docker run -v "/shared:/shared" builder

echo "Building orchestrator image"
docker build -t orchestrator -f orchestrator/Dockerfile .

echo "Building local_client image"
docker build -t local_client -f local_client/Dockerfile .

echo "Building functionalities image"
docker build -t functionalities -f functionalities/Dockerfile .

echo "Building neural_functionalities image"
docker build -t neural_functionalities -f neural_functionalities/Dockerfile .

echo "Building external_functionalities image"
docker build -t external_functionalities -f external_functionalities/Dockerfile .

echo "Building llm_functionalities image"
docker build -t llm_functionalities -f llm_functionalities/Dockerfile .
