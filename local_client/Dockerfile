FROM python:slim

MAINTAINER Carlos Gemmell

ARG DISTRIBUTOR_URL
ENV DISTRIBUTOR_URL ${DISTRIBUTOR_URL}

COPY local_client/ /source
RUN pip install -r /source/requirements.txt

RUN aws configure set region us-east-1

COPY shared/ /shared

WORKDIR source

CMD PYTHONPATH=/shared python local_client.py
