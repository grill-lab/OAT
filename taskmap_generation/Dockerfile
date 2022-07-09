FROM ubuntu:18.04

MAINTAINER Iain Mackie

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    build-essential \
    git \
    wget vim \
    software-properties-common \
    locales \
    unzip

RUN locale-gen en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en

RUN add-apt-repository -y ppa:deadsnakes/ppa

RUN apt-get install -y python3 \
    python3-pip \
    python-setuptools

RUN pip3 install --upgrade pip
RUN pip3 install --upgrade flask requests

RUN apt-get install -y openjdk-11-jdk

# Install Rust for M1 Compatibility
RUN apt-get install -y curl
RUN curl https://sh.rustup.rs -sSf | bash -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

RUN pip3 install spacy===2.3.5

RUN curl "https://s3.amazonaws.com/aws-cli/awscli-bundle-1.18.187.zip" -o "awscli-bundle.zip"
RUN unzip awscli-bundle.zip
RUN ./awscli-bundle/install -i /usr/local/aws -b /usr/local/bin/aws
RUN aws --version

#COPY taskmap_generation/alexa_prize_cobot_sdk-4.0.3-py2.py3-none-any.whl /
#RUN pip3 install /alexa_prize_cobot_sdk-4.0.3-py2.py3-none-any.whl --force-reinstall

#RUN mkdir ~/.aws
#COPY taskmap_generation/credentials.csv credentials.csv
#RUN echo [default] > ~/.aws/credentials
#RUN echo aws_access_key_id=$(awk -F',' 'FNR==2{print $1}' credentials.csv) >> ~/.aws/credentials
#RUN echo aws_secret_access_key=$(awk -F',' 'FNR==2{print $2}' credentials.csv) >> ~/.aws/credentials
#RUN export COBOT_API_KEY=$(awk -F',' 'FNR==2{print $3}' credentials.csv); echo "export COBOT_API_KEY=$COBOT_API_KEY" >> ~/.bashrc

RUN aws configure set region us-east-1

COPY taskmap_generation/requirements.txt /source/requirements.txt
RUN pip3 install -r /source/requirements.txt
RUN pip3 install jupyter jupyterlab

COPY /shared/ /shared
COPY /taskmap_generation /source/

WORKDIR /source
SHELL ["/bin/bash", "-ic"]
CMD source ~/.bashrc && sleep 60000 && python3 -u main.py
