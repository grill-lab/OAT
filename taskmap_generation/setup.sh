#!/bin/bash

if [ $1 == "--local" ]
then
  out_path="./shared/file_system/taskmap_generation"
else
  out_path="/shared/file_system/taskmap_generation"
fi

#echo "Downloading Recipe 1M+ dataset..."
#aws s3 cp --recursive s3://grill-bot-data/recipe1M $out_path"/recipe1M"

echo "Downloading Wikihow dataset..."
curl --create-dirs -o $out_path"/wikihow/wikihow_upen.jsonl" \
  https://open-grill.s3.amazonaws.com/data/sources/wikihow_upen.jsonl
curl --create-dirs -o $out_path"/wikihow/wikihow_upen_req.jsonl" \
  https://open-grill.s3.amazonaws.com/data/sources/wikihow_upen_req.jsonl
#aws s3 cp --recursive s3://grill-bot-data/wikihow $out_path"/wikihow"

echo "Downloading Seriouseats dataset..."
curl --create-dirs -o $out_path"/seriouseats/serious_eats_docs.json" \
  https://open-grill.s3.amazonaws.com/data/sources/serious_eats_docs.json
#aws s3 cp --recursive s3://grill-bot-data/seriouseats $out_path"/seriouseats"

echo "Downloading Step Requirement lookup file..."
#aws s3 cp s3://grill-bot-data/step_requirement_links/step_requirement_links_v4.json $out_path"/"
curl --create-dirs -o $out_path"/step_requirement_links.json" \
https://open-grill.s3.amazonaws.com/data/sources/step_requirement_links.json


