# README

The `Dockerfile` in this folder builds an image called `oat_common` which is used as a base image for most of the other OAT services. 

The image contains a set of Python packages that the services all have in common. Defining and installing them here helps to avoid having multiple `requirements.txt` files listing the same packages that have to be kept updated. 

The image also installs a set of system packages, saving time installing these into each of the individual OAT service images.

## Image details

`oat_common` is based on the official [ubuntu:22.04](https://hub.docker.com/layers/library/ubuntu/22.04/images/sha256-817cfe4672284dcbfee885b1a66094fd907630d610cab329114d036716be49ba?context=explore) LTS image.

The [Dockerfile](Dockerfile) performs the following steps:

* install some required system packages, including `build-essential`, `git`, `wget`, `curl`, `unzip`, `python3`, `python3-pip` (the Python version used is **3.9**)
* upgrade `pip` to the latest version
* install the set of common Python packages from [requirements.txt](requirements.txt)
* install Rust and add to `$PATH`
* do basic locale configuration 
* defines a location for the `TRANSFORMERS_CACHE` environment variable in the `shared` volume used by all OAT services (this helps prevent repeated downloading of HuggingFace models and other files, see [here](https://huggingface.co/transformers/v4.0.1/installation.html?highlight=transformers_cache#caching-model))

## Building the image

Despite being listed as a dependency of the services in `docker-compose.yaml` the `oat_common` image is **not** (re)built automatically by `docker compose`. 

To build it manually, run `docker compose build oat_common`.
