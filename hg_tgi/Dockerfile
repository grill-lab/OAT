FROM ghcr.io/huggingface/text-generation-inference:latest
RUN apt-get update && apt-get install -y curl

# wrapper script for the TGI launcher which just unpacks
# parameters passed in using the TGI_PARAMS env var via 
# docker-compose.yml
COPY hg_tgi/tgi-wrapper.sh /tmp
ENTRYPOINT ["bash", "/tmp/tgi-wrapper.sh"]
