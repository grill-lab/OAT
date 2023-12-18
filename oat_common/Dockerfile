# syntax=docker/dockerfile:1.3
FROM ubuntu:22.04

# Builds an image that is used as a base by most of the OAT services.
#
# The commands below install some common packages for all dependent images, does
# some basic locale generation, upgrades pip, installs some Python packages used
# by almost all the OAT services based on this image, installs Rust, and sets the 
# TRANSFORMERS_CACHE env var for HuggingFace downloads to a location in the
# volume shared by all the services

COPY oat_common/requirements.txt /requirements.txt

ENV TZ="Europe/London"
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
    software-properties-common \
    gnupg \
    ca-certificates \
    build-essential \
    git \
    wget \
    locales \
    unzip \
    curl \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && apt-get install -y --no-install-recommends \
    python3.9 \
    python3-pip \
    python3-setuptools \
    python3.9-distutils \
    python3.9-dev \
    && update-alternatives --install /usr/bin/python3 python /usr/bin/python3.9 5 \
    && locale-gen en_US.UTF-8 \
    && pip3 install --upgrade pip \
    && pip3 install -r /requirements.txt \
    # Install Rust for M1 Compatibility
    && curl https://sh.rustup.rs -sSf | bash -s -- -y \
    # removes about 500MB of docs
    && rm -rf /root/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/share/doc 

ENV PATH="/root/.cargo/bin:${PATH}"
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
# Use a common location in the volume for downloaded models from the
# huggingface.co transformers module
# https://huggingface.co/transformers/v4.0.1/installation.html?highlight=transformers_cache#caching-models
ENV TRANSFORMERS_CACHE /shared/file_system/cache/huggingface
