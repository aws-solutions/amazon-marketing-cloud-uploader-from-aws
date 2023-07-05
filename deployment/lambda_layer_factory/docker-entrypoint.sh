#!/bin/bash

echo "================================================================================"
echo "Installing the packages listed in requirements.txt:"
echo "================================================================================"
cat /packages/requirements.txt
pip3.10 install -q -r /packages/requirements.txt -t /packages/lambda_layer_python-3.10/python/lib/python3.10/site-packages


echo "================================================================================"
echo "Creating zip files for Lambda layers"
echo "================================================================================"
cd /packages/lambda_layer_python-3.10/
zip -q -r /packages/lambda_layer_python3.10.zip .


# Clean up build environment
cd /packages/
rm -rf /packages/lambda_layer_python-3.10/
