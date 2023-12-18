# syntax=docker/dockerfile:1.3
FROM oat_common:latest

MAINTAINER Carlos Gemmell

ARG DISTRIBUTOR_URL
ENV DISTRIBUTOR_URL ${DISTRIBUTOR_URL}

COPY local_client/ /source
COPY shared/ /shared
RUN pip install -r /source/requirements.txt

RUN aws configure set region us-east-1

WORKDIR source

CMD PYTHONPATH=/shared:/shared/compiled_protobufs python3 local_client.py
