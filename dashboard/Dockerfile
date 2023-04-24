# syntax=docker/dockerfile:1.3
FROM grill_common:latest

MAINTAINER Carlos Gemmell

RUN #apt-get update && apt-get install -y --no-install-recommends openjdk-18-jdk-headless

COPY dashboard/requirements.txt /source/requirements.txt
RUN pip3 install -r /source/requirements.txt
RUN aws configure set region us-east-1 \
    && aws configure set aws_access_key_id abc \
    && aws configure set aws_secret_access_key abc

WORKDIR /source
CMD PYTHONPATH=/shared:/shared/compiled_protobufs python3 -u main.py
