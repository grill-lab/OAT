# syntax=docker/dockerfile:1.3
FROM oat_common:latest

MAINTAINER Sophie Fischer

COPY dashboard/requirements.txt /source/requirements.txt
RUN pip3 install -r /source/requirements.txt

# TODO remove
RUN mkdir ~/.aws
COPY credentials.csv credentials.csv
RUN echo [default] > ~/.aws/credentials
RUN echo aws_access_key_id=$(awk -F',' 'FNR==2{print $1}' credentials.csv) >> ~/.aws/credentials
RUN echo aws_secret_access_key=$(awk -F',' 'FNR==2{print $2}' credentials.csv) >> ~/.aws/credentials
RUN aws configure set region us-east-1

COPY dashboard/ /source
WORKDIR /source
CMD PYTHONPATH=/shared:/shared/compiled_protobufs python3 -u main.py
