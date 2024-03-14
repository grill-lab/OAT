FROM oat_common:latest

MAINTAINER Sophie Fischer

ARG ROUTER_URL
ENV ROUTER_URL ${ROUTER_URL}

ARG SESSION_MANAGER_URL
ENV SESSION_MANAGER_URL ${SESSION_MANAGER_URL}

RUN apt-get update \
    && apt-get install -y --no-install-recommends openjdk-18-jdk-headless \
    && python3 -m pip install --upgrade pip \
    # Dummy credentials, not really needed to run locally DynamoDB but requested by the botocore API
    && aws configure set region us-east-1 \
    && aws configure set aws_access_key_id abc \
    && aws configure set aws_secret_access_key abc

WORKDIR /source

COPY offline/requirements.txt /source/requirements.txt

# uses a buildkit cache mount to try and share pip's cache between containers
# during the build process
RUN --mount=type=cache,mode=0755,target=/root/.cache/pip \
    pip3 install -r /source/requirements.txt

CMD PYTHONPATH=/shared:/shared/compiled_protobufs python3 -u main.py
