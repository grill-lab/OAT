# syntax=docker/dockerfile:1.3
FROM ubuntu:18.04

# install basic set of packages common to all dependent images, generate locales,
# upgrade pip

RUN sed -i -e 's/http:\/\/archive/mirror:\/\/mirrors/' -e 's/\/ubuntu\//\/mirrors.txt/' /etc/apt/sources.list \
    && sed -i -e 's/http:\/\/security/mirror:\/\/mirrors/' -e 's/\/ubuntu\//\/mirrors.txt/' /etc/apt/sources.list \
    && apt-get update \
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
    && update-alternatives --install /usr/bin/python python /usr/bin/python3 1 \
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
