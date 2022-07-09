# syntax=docker/dockerfile:1.3
FROM grill_common:latest

MAINTAINER Carlos Gemmell

RUN apt-get install -y openjdk-11-jdk \
    && curl "https://s3.amazonaws.com/aws-cli/awscli-bundle-1.18.187.zip" -o "awscli-bundle.zip" \
    && unzip awscli-bundle.zip \
    && awscli-bundle/install -i /usr/local/aws -b /usr/local/bin/aws \
    && rm -f awscli-bundle.zip

COPY dashboard/requirements.txt /source/requirements.txt
#COPY requirements.txt /source/requirements.txt
RUN pip3 install -r /source/requirements.txt
RUN aws configure set region us-east-1 \
    && aws configure set aws_access_key_id abc \
    && aws configure set aws_secret_access_key abc

WORKDIR /source
CMD PYTHONPATH=/shared:/shared/compiled_protobufs python3 -u main.py
