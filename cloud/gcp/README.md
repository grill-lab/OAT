# OAT GCP deployment script

**NOTE**: this script currently creates a basic VM without a GPU, so some OAT functionality will not be available with the default configuration.

The `oat_gcp.sh` script in this folder can be used to set up a basic GCP VM instance, install necessary dependencies, clone a selected branch of the OAT repository, then build and run the services using `docker compose`. 

Before you can run the script, you will need to install the [Google Cloud SDK](https://cloud.google.com/sdk/docs/install-sdk) and run the [initialization process](https://cloud.google.com/sdk/docs/install-sdk#initializing_the) to authenticate and select the cloud project you wish to use. 

## Using the script

The script is configured by a set of parameters defined in the [oat_gcp_config](oat_gcp_config) file. These have sensible defaults but you can edit them to e.g. change the GCP compute region or use a more powerful machine type.

You can also temporarily override any of the parameters in `oat_gcp_config` by setting the appropriate environment variable, e.g.:

```bash
# check out my-branch instead of main
BRANCH=my-branch ./oat_gcp.sh create
```

Each of the subcommands the script supports is described below.

### create

This will create a new VM, install dependencies, build the Docker images, and then run the deployment. 


```bash
./oat_gcp.sh create
```

It uses `docker compose up -d --build` as the final command, so the containers will be detached from the terminal and continue running in the background. 

If something goes wrong partway through the process, you can run the same command again to make another attempt. The script will detect if a VM with the selected name already exists and avoid attempting to create another.

The script will perform the following actions assuming the default parameters are set:
 * Create a GCP VM using an `e2-standard-4` instance (4 cores, 16GB RAM) with a 200GB disk, using Ubuntu 22.04 LTS as the OS
 * Install required OAT packages using `apt-get`
 * Install Docker and Docker Compose
 * Copy over a clone of the OAT repo with a selected branch checked out
 * Run the OAT `setup.sh` script
 * Run `docker compose up --build -d` to start the OAT services in the background

### destroy

This will delete the selected VM immediately. 

```bash
./oat_gcp.sh destroy
```

### cmd

This is a just a wrapper around `gcloud compute ssh vm_name --command "cmd arg1 arg"`:
```
# equivalent to:
#    gcloud compute ssh vm_name --command "sudo docker compose ps"
./oat_gcp.sh cmd sudo docker compose ps
```

Alternatively once the `create` command has finished setting up the VM, you can simply use `gcloud compute ssh` and `gcloud compute scp` as usual.

### tests

Runs the tester container:

```bash
# executes the command `sudo docker compose run tester`
./oat_gcp.sh tests
```

### logs

Runs `sudo docker compose logs`

```bash
./oat_gcp.sh logs
```
