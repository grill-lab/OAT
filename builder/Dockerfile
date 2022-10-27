FROM grill_common:latest

MAINTAINER Federico Rossetto


RUN pip3 install --upgrade pip
RUN pip3 install grpcio==1.47.0 grpcio_tools==1.47.0

COPY builder/ /source

CMD bash /source/init.sh
