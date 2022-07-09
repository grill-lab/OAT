# GRILLbot installation

To get the GRILLbot up and running, follow the following steps:

1. Install Docker (https://docs.docker.com/engine/install/)
2. Install Docker Compose V2 (https://docs.docker.com/compose/cli-command)
3. Download the InternalGRILL source code from AWS

   ```bash
   wget https://grillbot-public-data.s3.amazonaws.com/InternalGRILL-master.zip
   unzip InternalGRILL-master.zip
   cd InternalGRILL-master
   ```
4. Build the Docker images and start the containers using Docker Compose

   ```bash
   docker compose up --build
   ```

   Note: this might take a while!
5. Once everything is up and running, you can access the local client at http://localhost:9000