#!/bin/bash

# read the value of $TGI_PARAMS into an array, splitting on spaces
# TODO: might break if there are parameter values that also contain spaces
IFS=' ' read -ra PARAM_ARRAY <<< "${TGI_PARAMS}"

#echo "Parameters: ${PARAM_ARRAY[@]}"

# Pass the parameters on to the launcher.
# (only default arg in the original Dockerfile is --json-output)
text-generation-launcher "${PARAM_ARRAY[@]}"
