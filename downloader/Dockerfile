FROM oat_common:latest

COPY downloader/ /source

# stop watchtower logging errors
RUN  aws configure set region us-east-1

COPY credentials.csv* /root/credentials.csv
WORKDIR /source
ENV PYTHONPATH=/shared:/shared/compiled_protobufs

# expects arguments to be passed to the script, e.g.
# > docker compose run downloader offline functionalities
ENTRYPOINT ["python3", "main.py"]
