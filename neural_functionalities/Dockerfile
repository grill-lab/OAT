# syntax=docker/dockerfile:1.3
FROM nvidia/cuda:11.4.1-runtime-ubuntu18.04

MAINTAINER Paul Owoicho

RUN apt-get update \
    && apt-get install -y --no-install-recommends software-properties-common \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && apt-get install -y --no-install-recommends \
    ca-certificates \
    build-essential \
    git \
    wget \
    locales \
    unzip \
    curl \
    python3 \
    python3-pip \
    python3-setuptools \
    python3-dev \
    && locale-gen en_US.UTF-8 \
    && pip3 install --upgrade pip \
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

COPY neural_functionalities/requirements.txt /source/requirements.txt
# uses a buildkit cache mount to try and share pip's cache between containers
# during the build process
RUN --mount=type=cache,mode=0755,target=/root/.cache/pip \
    pip3 install -r /source/requirements.txt \
    && aws configure set region us-east-1

COPY neural_functionalities/ /source
COPY shared/ /shared

WORKDIR /source
CMD PYTHONPATH=/shared:/shared/compiled_protobufs python3 -u main.py
