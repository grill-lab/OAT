# syntax=docker/dockerfile:1.3
FROM oat_common:latest

MAINTAINER Ekaterina Terzieva & Philip Zubel

ARG ROUTER_URL
ENV ROUTER_URL ${ROUTER_URL}

ARG SESSION_MANAGER_URL
ENV SESSION_MANAGER_URL ${SESSION_MANAGER_URL}

COPY tester/requirements.txt /source/requirements.txt
# uses a buildkit cache mount to try and share pip's cache between containers
# during the build process
RUN --mount=type=cache,mode=0755,target=/root/.cache/pip \
    pip3 install -r /source/requirements.txt \
    && aws configure set region us-east-1

COPY tester/ /source
COPY credentials.csv* credentials.csv

WORKDIR /source

ENV PYTHONPATH=/shared:/shared/compiled_protobufs
# the combination of ENTRYPOINT and CMD means that the default behaviour for
# "docker compose run tester" will be equivalent to doing "pytest tests/unit_tests".
# To use a different set of arguments, pass them on the command line:
# "docker compose run tester tests --runslow" would run both unit and integration
# tests, including ones marked as "slow"
ENTRYPOINT ["pytest"]
CMD ["tests/unit_tests"]
