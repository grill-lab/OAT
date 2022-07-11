#!/bin/bash

out_path="./shared/file_system"

echo "Downloading models..."
#aws s3 cp --recursive s3://grill-bot-data/models $out_path"/models"
curl --create-dirs -o $out_path"/models.zip" \
  https://open-grill.s3.amazonaws.com/data/models.zip
unzip -d $out_path $out_path"/models.zip"

echo "Downloading indexes..."
curl --create-dirs -o $out_path"/indexes.zip" \
  https://open-grill.s3.amazonaws.com/data/indexes.zip
unzip -d $out_path $out_path"/indexes.zip"

echo "Downloading Lookup files..."
curl --create-dirs -o $out_path"/lookup_files.zip" \
  https://open-grill.s3.amazonaws.com/data/lookup_files.zip
unzip -d $out_path $out_path"/lookup_files.zip"
