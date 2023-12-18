# syntax=docker/dockerfile:1.3
FROM sphinxdoc/sphinx:latest

COPY sphinx_docs/requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt

WORKDIR /source/sphinx_docs

#ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/shared:/shared/compiled_protobufs

# the build_docs script runs sphinx-apidoc and then uses the
# Makefile to run the documentation building process
ENTRYPOINT ["/bin/bash", "/source/sphinx_docs/build_docs.sh"]
# these arguments are passed to "make", so the script will
# end up running "make html". you can override this to e.g.
# do "make clean html" to force a full rebuild of the docs.
CMD ["html"]
