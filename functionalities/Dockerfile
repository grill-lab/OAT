# syntax=docker/dockerfile:1.3
FROM oat_common:latest

MAINTAINER Carlos Gemmell

COPY functionalities/requirements.txt /source/requirements.txt
# uses a buildkit cache mount to try and share pip's cache between containers
# during the build process
RUN --mount=type=cache,mode=0755,target=/root/.cache/pip \
    apt-get update \
    && apt-get install -y --no-install-recommends openjdk-18-jdk-headless \
    && pip3 install -r /source/requirements.txt \
    && aws configure set region us-east-1

COPY functionalities/ /source
COPY shared/ /shared

WORKDIR /source
CMD PYTHONPATH=/shared:/shared/compiled_protobufs python3 -u main.py
