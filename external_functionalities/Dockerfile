# syntax=docker/dockerfile:1.3
FROM grill_common:latest

MAINTAINER Iain & Sophie :)

COPY external_functionalities/requirements.txt /source/requirements.txt

# uses a buildkit cache mount to try and share pip's cache between containers
# during the build process
RUN --mount=type=cache,mode=0755,target=/root/.cache/pip \
    pip3 install -r /source/requirements.txt \
    # Dummy credentials, not really needed to run locally DynamoDB but requested by the botocore API
    && aws configure set region us-east-1 \
    && aws configure set aws_access_key_id abc \
    && aws configure set aws_secret_access_key abc


COPY external_functionalities/ /source
COPY shared/ /shared

WORKDIR /source
CMD PYTHONPATH=/shared:/shared/compiled_protobufs python3 -u main.py
