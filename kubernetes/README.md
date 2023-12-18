# Running OAT with Minikube

[Minikube](https://minikube.sigs.k8s.io/docs/) creates a local Kubernetes cluster you can use to emulate a production environment. This document gives a brief description of how to deploy OAT in a Minikube environment.

You will need to open 2 terminals, labelled "Terminal 1" and "Terminal 2" below.

### Terminal 1

Run the following commands:
```
cd OAT/
minikube start
minikube tunnel &
minikube dashboard &
minikube mount ./shared:/shared 
```

### Terminal 2
Building the images and running them can be done with the following script. This does the following:
```
cd OAT/kubernetes
bash build_and_run.sh
```
- Runs the `builder` service to generate the Python protobuf bindings (these are stored in `OAT/shared/compiled_protobufs`
- Changes the docker environment to be visible to minikube. This is distinct from the host docker env. This can be done manually by running: `eval $(minikube docker-env)`
- Builds all the images for the online from their Dockerfiles
- Deletes all pods relating to OAT by running: `kubectl delete -k ./`
- Applies the manifests to Minikube by running: `kubectl delete -k ./`

You should then see the local client be available at `localhost:9000`
<img width="1166" alt="image" src="https://user-images.githubusercontent.com/6844601/129228300-9ffe043a-92ed-4208-ba78-767ab7ae7071.png">

## Restarting with modified code
If the OAT pods in Minikube are already running and you only need to reload them to apply new code, you can use the following command. Note that this **does not build the images** again, it only reloads the pods to pull their latest version. 
```
kubectl rollout restart -f ./
```

## Kustomization and kubectl
`kubectl` is  the primary way to interface with kubernetes through the commandline. When using the `-k` option we are telling kubectl to read the `kustomization.yaml` in a specific directory.

We use [Kustomize](https://kubectl.docs.kubernetes.io/guides/introduction/kustomize/) to aggregate all kubernetes manifests into a single output  and  specify what resources need to be spun up. Since `OAT` has certain  components  that are only required when running it standalone, they are specified as extras in `/kubernetes/internal_overlay`. 

The `kubernetes/kustomization.yaml` specifies `internal_overlay` as a resource so by running `kubectl apply -k  ./` we start `OAT` with the resources needed to run it as a standalone instance (`external_functionalities`, a local DynamoDB instance).

To  gain  a more intuitive understanding of what kustomization is doing, see what it does by running `kubectl kustomize ./kubernetes`. This allows you to see the full manifest that is passed to `kubectl`.
