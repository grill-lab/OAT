FROM python:slim

MAINTAINER Federico Rossetto


RUN pip3 install --upgrade pip
RUN pip3 install grpcio grpcio_tools

COPY builder/ /source

CMD bash /source/init.sh