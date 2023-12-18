# syntax=docker/dockerfile:1.3
FROM oat_common:latest

MAINTAINER Ekaterina Terzieva 

ARG ROUTER_URL
ENV ROUTER_URL ${ROUTER_URL}

ARG SESSION_MANAGER_URL
ENV SESSION_MANAGER_URL ${SESSION_MANAGER_URL}

COPY training/requirements.txt /source/requirements.txt
# uses a buildkit cache mount to try and share pip's cache between containers
# during the build process
RUN --mount=type=cache,mode=0755,target=/root/.cache/pip \
    pip3 install -r /source/requirements.txt \
    && aws configure set region us-east-1

COPY training/ /source

WORKDIR /source

ENV PYTHONPATH=/shared:/shared/compiled_protobufs
ENTRYPOINT ["python3", "-u", "main.py"]

