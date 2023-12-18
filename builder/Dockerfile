FROM oat_common:latest

MAINTAINER Federico Rossetto

COPY builder/ /source

RUN pip3 install --upgrade pip
RUN pip3 install -r /source/requirements.txt

COPY shared/ /shared

CMD bash /source/init.sh
