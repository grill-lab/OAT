# syntax=docker/dockerfile:1.3
FROM oat_common:latest

MAINTAINER Sophie Fischer

COPY dashboard/requirements.txt /source/requirements.txt
RUN pip3 install -r /source/requirements.txt

# Dummy credentials, not really needed to run locally DynamoDB but requested by the botocore API
RUN aws configure set region us-east-1 \
    && aws configure set aws_access_key_id abc \
    && aws configure set aws_secret_access_key abc

COPY dashboard/ /source
WORKDIR /source
CMD PYTHONPATH=/shared:/shared/compiled_protobufs python3 -u main.py
