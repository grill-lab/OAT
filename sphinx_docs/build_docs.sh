#!/bin/bash

DOCS_PREFIX="./docs_"
PACKAGES=(external_functionalities functionalities neural_functionalities orchestrator shared offline)

# Run sphinx-apidoc to generate Sphinx source files for the autodoc extension
# https://www.sphinx-doc.org/en/master/man/sphinx-apidoc.html
for pkg in "${PACKAGES[@]}"
do
    # parameters:
    #  -o : output path
    #  --implicit-namespaces : this is used to partly workaround the lack of a single top-level OAT package
    #  /source/${pkg} : input files
    #  remaining parameters are excludes
    sphinx-apidoc --implicit-namespaces -o "${DOCS_PREFIX}${pkg}" /source/"${pkg}" "/source/shared/compiled_protobufs/*" "/shared/compiled_protobufs/"
done

# run make with the arguments passed in from the Dockerfile (default is "html" 
# which will generate HTML documentation)
make "$@"
