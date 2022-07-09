cd ..
echo Going to base of repo at $PWD

echo Setting docer environemt to host
minikube docker-env --unset

echo Building bob the builder
docker build -t builder -f builder/Dockerfile .
docker run -v $PWD/shared:/shared -v $PWD/builder:/source builder

echo Setting docker environemt to minikube
eval $(minikube docker-env)

#echo Builing offline image
#docker build -t offline -f offline/Dockerfile .

echo Building orchestrator image
docker build -t orchestrator -f orchestrator/Dockerfile .

echo Building local_client image
docker build -t local_client -f local_client/Dockerfile .

echo Builing functionalities image
docker build -t functionalities -f functionalities/Dockerfile .

echo Builing neural_functionalities image
docker build -t neural_functionalities -f neural_functionalities/Dockerfile .

echo Builing external_functionalities image
docker build -t external_functionalities -f external_functionalities/Dockerfile .

echo Builing taskmap_generation image
docker build -t taskmap_generation -f taskmap_generation/Dockerfile .
