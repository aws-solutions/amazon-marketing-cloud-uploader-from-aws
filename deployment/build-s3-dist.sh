#!/bin/bash
###############################################################################
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
#
# PURPOSE:
#   Build cloud formation templates and stack resources for the solution.
#
# USAGE:
#  ./build-s3-dist.sh [-h] [-v] --template-bucket {TEMPLATE_BUCKET} --code-bucket {CODE_BUCKET} --solution-name {SOLUTION_NAME} --version {VERSION} --region {REGION} [--profile {PROFILE}]
#    TEMPLATE_BUCKET should be the name for the S3 bucket location where
#      cloud formation templates should be saved.
#    CODE_BUCKET should be the name for the S3 bucket location where cloud
#      formation templates should find Lambda source code packages.
#    SOLUTION_NAME can be any string in kebab case.
#    VERSION can be anything but should be in a format like v1.0.0 just to be consistent
#      with the official solution release labels.
#    REGION needs to be in a format like us-east-1
#    PROFILE is optional. It's the profile that you have setup in ~/.aws/credentials
#      that you want to use for AWS CLI commands.
#
#    The following options are available:
#
#     -h | --help       Print usage
#     -v | --verbose    Print script debug info
#
###############################################################################

trap cleanup_and_die SIGINT SIGTERM ERR

usage() {
  msg "$msg"
  cat <<EOF
Usage: $(basename "${BASH_SOURCE[0]}") [-h] [-v] [--profile PROFILE] --template-bucket TEMPLATE_BUCKET --code-bucket CODE_BUCKET --solution-name SOLUTION_NAME --version VERSION --region REGION

Available options:

-h, --help        Print this help and exit (optional)
-v, --verbose     Print script debug info (optional)
--template-bucket S3 bucket to put cloud formation templates
--code-bucket     S3 bucket to put Lambda code packages
--solution-name   Arbitrary string indicating the solution name
--version         Arbitrary string indicating build version
--region          AWS Region, formatted like us-west-2
--profile         AWS profile for CLI commands (optional)
EOF
  exit 1
}

cleanup_and_die() {
  trap - SIGINT SIGTERM ERR
  echo "Trapped signal."
  cleanup
  die 1
}

cleanup() {
  # Deactivate and remove the temporary python virtualenv used to run this script
  if [[ "$VIRTUAL_ENV" != "" ]];
  then
    deactivate
    rm -rf $VENV
    echo "------------------------------------------------------------------------------"
    echo "Cleaning up complete"
    echo "------------------------------------------------------------------------------"
  fi
}

msg() {
  echo >&2 -e "${1-}"
}

die() {
  local msg=$1
  local code=${2-1} # default exit status 1
  msg "$msg"
  exit "$code"
}

parse_params() {
  # default values of variables set from params
  flag=0
  param=''
  use_solution_builder_pipeline=false

  while :; do
    case "${1-}" in
    -h | --help) usage ;;
    -v | --verbose) set -x ;;
    --template-bucket)
      global_bucket="${2}"
      shift
      ;;
    --code-bucket)
      regional_bucket="${2}"
      shift
      ;;
    --solution-name)
      solution_name="${2}"
      shift
      ;;
    --version)
      version="${2}"
      shift
      ;;
    --region)
      region="${2}"
      shift
      ;;
    --profile)
      profile="${2}"
      shift
      ;;
    --use_solution_builder_pipeline)
      use_solution_builder_pipeline=true
      shift
      ;;
    -?*) die "Unknown option: $1" ;;
    *) break ;;
    esac
    shift
  done

  args=("$@")

  # check required params and arguments
  [[ -z "${global_bucket}" ]] && usage "Missing required parameter: template-bucket"
  [[ -z "${regional_bucket}" ]] && usage "Missing required parameter: code-bucket"
  [[ -z "${solution_name}" ]] && usage "Missing required parameter: solution-name"
  [[ -z "${version}" ]] && usage "Missing required parameter: version"
  [[ -z "${region}" ]] && usage "Missing required parameter: region"

  return 0
}

parse_params "$@"
msg "Build parameters:"
msg "- Template bucket: ${global_bucket}"
msg "- Code bucket: ${regional_bucket}-${region}"
msg "- Solution name: ${solution_name}"
msg "- Version: ${version}"
msg "- Region: ${region}"
msg "- Profile: ${profile}"
msg "- use_solution_builder_pipeline: ${use_solution_builder_pipeline}"

echo ""
sleep 3
s3domain="s3.$region.amazonaws.com"

# Make sure aws cli is installed
if [[ ! -x "$(command -v aws)" ]]; then
echo "ERROR: This script requires the AWS CLI to be installed. Please install it then run again."
exit 1
fi

# Get reference for all important folders
build_dir="$PWD"
source_dir="$build_dir/../source"
consumer_dir="$build_dir/../source/consumer"
global_dist_dir="$build_dir/global-s3-assets"
regional_dist_dir="$build_dir/regional-s3-assets"

# Create and activate a temporary Python environment for this script.
echo "------------------------------------------------------------------------------"
echo "Creating a temporary Python virtualenv for this script"
echo "------------------------------------------------------------------------------"
python3.10 -c "import os; print (os.getenv('VIRTUAL_ENV'))" | grep -q None
if [ $? -ne 0 ]; then
    echo "ERROR: Do not run this script inside Virtualenv. Type \`deactivate\` and run again.";
    exit 1;
fi
command -v python3.10
if [ $? -ne 0 ]; then
    echo "ERROR: install python3.10 before running this script"
    exit 1
fi
echo "Using virtual python environment:"
VENV=$(mktemp -d) && echo "$VENV"
command -v python3.10 > /dev/null
if [ $? -ne 0 ]; then
    echo "ERROR: install python3.10 before running this script"
    exit 1
fi
python3.10 -m venv "$VENV"
source "$VENV"/bin/activate
pip3 install wheel
pip3 install --quiet boto3 chalice requests aws_xray_sdk awswrangler

echo "------------------------------------------------------------------------------"
echo "Create distribution directory"
echo "------------------------------------------------------------------------------"

# Setting up directories
echo "rm -rf $global_dist_dir"
rm -rf "$global_dist_dir"
echo "mkdir -p $global_dist_dir"
mkdir -p "$global_dist_dir"
echo "rm -rf $regional_dist_dir"
rm -rf "$regional_dist_dir"
echo "mkdir -p $regional_dist_dir"
mkdir -p "$regional_dist_dir"
echo "mkdir -p $regional_dist_dir/website/"
mkdir -p "$regional_dist_dir"/website/

echo "------------------------------------------------------------------------------"
echo "Building Lambda Layers"
echo "------------------------------------------------------------------------------"
cd "$build_dir"/lambda_layer_factory/ || exit 1
echo "Running build-lambda-layer.sh"
rm -rf lambda_layer-python-* lambda_layer-python*.zip
./build-lambda-layer.sh requirements.txt
if [ $? -ne 0 ]; then
  echo "ERROR: Lambda layer build script failed."
  exit 1
fi
rm -rf lambda_layer_python-3.9/
echo "Lambda layer build script completed.";
mv lambda_layer_python3.9.zip "$regional_dist_dir"
echo "Lambda layer file:"
ls $regional_dist_dir/lambda_layer_python3.9.zip
cd "$build_dir" || exit 1

echo "------------------------------------------------------------------------------"
echo "CloudFormation Templates"
echo "------------------------------------------------------------------------------"
echo ""
echo "Preparing template files:"
cp "$build_dir/amazon-marketing-cloud-uploader-from-aws.yaml" "$global_dist_dir/amazon-marketing-cloud-uploader-from-aws.template"
cp "$build_dir/glue.yaml" "$global_dist_dir/glue.template"
cp "$build_dir/auth.yaml" "$global_dist_dir/auth.template"
cp "$build_dir/web.yaml" "$global_dist_dir/web.template"
find "$global_dist_dir"
echo "Updating template source bucket in template files with '$global_bucket'"
echo "Updating code source bucket in template files with '$regional_bucket'"
echo "Updating solution version in template files with '$version'"
new_global_bucket="s/%%GLOBAL_BUCKET_NAME%%/$global_bucket/g"
new_regional_bucket="s/%%REGIONAL_BUCKET_NAME%%/$regional_bucket/g"
new_version="s/%%VERSION%%/$version/g"
new_solution="s/%%SOLUTION_NAME%%/$solution_name/g"
# Update templates in place. Copy originals to [filename].orig
sed -i.orig -e "$new_global_bucket" "$global_dist_dir/amazon-marketing-cloud-uploader-from-aws.template"
sed -i.orig -e "$new_regional_bucket" "$global_dist_dir/amazon-marketing-cloud-uploader-from-aws.template"
sed -i.orig -e "$new_version" "$global_dist_dir/amazon-marketing-cloud-uploader-from-aws.template"
sed -i.orig -e "$new_solution" "$global_dist_dir/amazon-marketing-cloud-uploader-from-aws.template"
sed -i.orig -e "$new_global_bucket" "$global_dist_dir/glue.template"
sed -i.orig -e "$new_regional_bucket" "$global_dist_dir/glue.template"
sed -i.orig -e "$new_version" "$global_dist_dir/glue.template"
sed -i.orig -e "$new_solution" "$global_dist_dir/glue.template"
sed -i.orig -e "$new_global_bucket" "$global_dist_dir/web.template"
sed -i.orig -e "$new_regional_bucket" "$global_dist_dir/web.template"
sed -i.orig -e "$new_version" "$global_dist_dir/web.template"
sed -i.orig -e "$new_solution" "$global_dist_dir/web.template"

echo "------------------------------------------------------------------------------"
echo "API Stack"
echo "------------------------------------------------------------------------------"

echo "Building API Lambda handler"
cd "$source_dir/api" || exit 1
[ -e dist ] && rm -rf dist
mkdir -p dist
if ! [ -x "$(command -v chalice)" ]; then
  echo 'Chalice is not installed. It is required for this solution. Exiting.'
  exit 1
fi

# Remove chalice deployments to force redeploy when there are changes to configuration only
# Otherwise, chalice will use the existing deployment package
[ -e .chalice/deployments ] && rm -rf .chalice/deployments

echo "cp -R $source_dir/share ./dist"
cp -R "$source_dir/share" "./dist"

echo "Running chalice..."
chalice package --merge-template external_resources.json dist
echo "Finished running chalice."
echo "cp ./dist/sam.json $global_dist_dir/api.template"
cp dist/sam.json "$global_dist_dir"/api.template
if [ $? -ne 0 ]; then
  echo "ERROR: Failed to build api template"
  exit 1
fi
cd dist
echo "deployment.zip /share/* -x **/__pycache__/*"
zip -r deployment.zip share/* -x "**/__pycache__/*"
cd ..
echo "cp ./dist/deployment.zip $regional_dist_dir-api.zip"
cp ./dist/deployment.zip "$regional_dist_dir"/api.zip
if [ $? -ne 0 ]; then
  echo "ERROR: Failed to build api template"
  exit 1
fi
rm -rf ./dist

echo "------------------------------------------------------------------------------"
echo "Glue ETL"
echo "------------------------------------------------------------------------------"
echo "Building Glue ETL script"
cd "$source_dir/glue" || exit 1
echo "cp amc_transformations.py $regional_dist_dir/"
cp amc_transformations.py "$regional_dist_dir"
zip -q library.zip library/*
cp library.zip "$regional_dist_dir"
rm -f library.zip

echo "------------------------------------------------------------------------------"
echo "Build vue website"
echo "------------------------------------------------------------------------------"

echo "Building Vue.js website"
cd "$source_dir/website/" || exit 1
echo "Installing node dependencies"
npm install
echo "Compiling the vue app"
npm run build
echo "Finished building website"
cp -r ./dist/* "$regional_dist_dir"/website/
rm -rf ./dist

echo "------------------------------------------------------------------------------"
echo "Generate webapp manifest file"
echo "------------------------------------------------------------------------------"
# This manifest file contains a list of all the webapp files. It is necessary in
# order to use the least privileges for deploying the webapp.
#
# Details: The website_helper.py Lambda function needs this list in order to copy
# files from $regional_dist_dir/website to the WebsiteBucket (see web.yaml).  Since the manifest file is computed during build
# time, the website_helper.py Lambda can use that to figure out what files to copy
# instead of doing a list bucket operation, which would require ListBucket permission.
# Furthermore, the S3 bucket used to host AWS solutions disallows ListBucket
# access, so the only way to copy the website files from that bucket from
# to WebsiteBucket is to use said manifest file.
#
cd $regional_dist_dir"/website/" || exit 1
manifest=(`find . -type f | sed 's|^./||'`)
manifest_json=$(IFS=,;printf "%s" "${manifest[*]}")
echo "[\"$manifest_json\"]" | sed 's/,/","/g' > "$source_dir/helper/webapp-manifest.json"
cat "$source_dir/helper/webapp-manifest.json"

echo "------------------------------------------------------------------------------"
echo "Build website helper function"
echo "------------------------------------------------------------------------------"

echo "Building website helper function"
cd "$source_dir/helper" || exit 1
[ -e dist ] && rm -r dist
mkdir -p dist
zip -q -g ./dist/websitehelper.zip ./website_helper.py webapp-manifest.json
cp "./dist/websitehelper.zip" "$regional_dist_dir/websitehelper.zip"

echo "------------------------------------------------------------------------------"
echo "Build AMC uploader function"
echo "------------------------------------------------------------------------------"

echo "Building AMC uploader function"
cd "$source_dir/amc_uploader" || exit 1
[ -e dist ] && rm -r dist
mkdir -p dist
echo "cp -R $source_dir/share ./dist"
cp -R "$source_dir/share" "./dist"
[ -e package ] && rm -r package
mkdir -p package
echo "preparing packages from requirements.txt"
# Package dependencies listed in requirements.txt
pushd package || exit 1
# Handle distutils install errors with setup.cfg
touch ./setup.cfg
echo "[install]" > ./setup.cfg
echo "prefix= " >> ./setup.cfg
pip3 install --quiet -r ../requirements.txt --target .
zip -q -r9 ../dist/amc_uploader.zip .
popd || exit 1
zip -q -g ./dist/amc_uploader.zip ./amc_uploader.py
zip -q -g ./dist/amc_uploader.zip ./lib/sigv4.py
cd dist
echo "amc_uploader.zip share/* -x **/__pycache__/*"
zip -r amc_uploader.zip share/* -x "**/__pycache__/*"
cd ..
cp "./dist/amc_uploader.zip" "$regional_dist_dir/amc_uploader.zip"
rm -rf ./dist

echo "------------------------------------------------------------------------------"
echo "Creating deployment package for anonymous data logger"
echo "------------------------------------------------------------------------------"

echo "Building anonymous data logger"
cd "$source_dir/anonymous_data_logger" || exit 1
[ -e dist ] && rm -rf dist
mkdir -p dist
[ -e package ] && rm -rf package
mkdir -p package
echo "create requirements for lambda"
# Make lambda package
pushd package || exit 1
echo "create lambda package"
# Handle distutils install errors
touch ./setup.cfg
echo "[install]" > ./setup.cfg
echo "prefix= " >> ./setup.cfg
pip3 install --quiet -r ../requirements.txt --target .
cp -R ../anonymous_lib .
if ! [ -d ../dist/anonymous_data_logger.zip ]; then
  zip -q -r9 ../dist/anonymous_data_logger.zip .
elif [ -d ../dist/anonymous_data_logger.zip ]; then
  echo "Package already present"
fi
popd || exit 1
zip -q -g ./dist/anonymous_data_logger.zip ./anonymous_data_logger.py
cp "./dist/anonymous_data_logger.zip" "$regional_dist_dir/anonymous_data_logger.zip"
# Finished building anonymous data logger
rm -rf ./dist ./package

# Skip copy dist to S3 if building for solution builder because
# that pipeline takes care of copying the dist in another script.
if [ $use_solution_builder_pipeline = false ]; then

  echo "------------------------------------------------------------------------------"
  echo "Copy dist to S3"
  echo "------------------------------------------------------------------------------"
  echo "Validating ownership of s3://$global_bucket"
  # Get account id
  account_id=$(aws sts get-caller-identity --query Account --output text $(if [ ! -z $profile ]; then echo "--profile $profile"; fi))
  if [ $? -ne 0 ]; then
    msg "ERROR: Failed to get AWS account ID"
    die 1
  fi
  # Validate ownership of $global_bucket
  aws s3api head-bucket --bucket $global_bucket --expected-bucket-owner $account_id $(if [ ! -z $profile ]; then echo "--profile $profile"; fi)
  if [ $? -ne 0 ]; then
    msg "ERROR: Your AWS account does not own s3://$global_bucket/"
    die 1
  fi
  echo "Validating ownership of s3://${regional_bucket}-${region}"
  # Validate ownership of ${regional_bucket}-${region}
  aws s3api head-bucket --bucket ${regional_bucket}-${region} --expected-bucket-owner $account_id $(if [ ! -z $profile ]; then echo "--profile $profile"; fi)
  if [ $? -ne 0 ]; then
    msg "ERROR: Your AWS account does not own s3://${regional_bucket}-${region} "
    die 1
  fi
  # Copy deployment assets to distribution buckets
  cd "$build_dir"/ || exit 1

  echo "*******************************************************************************"
  echo "*******************************************************************************"
  echo "**********                    I M P O R T A N T                      **********"
  echo "*******************************************************************************"
  echo "** You are about to upload templates and code to S3. Please confirm that     **"
  echo "** buckets ${global_bucket} and ${regional_bucket}-${region} are appropriately     **"
  echo "** secured (not world-writeable, public access blocked) before continuing.   **"
  echo "*******************************************************************************"
  echo "*******************************************************************************"
  echo "PROCEED WITH UPLOAD? (y/n) [n]: "
  read input
  if [ "$input" != "y" ] ; then
      echo "Upload aborted."
      exit
  fi

  echo "=========================================================================="
  echo "Uploading CloudFormation templates and Lambda code to S3"
  echo "=========================================================================="
  echo "Templates: ${global_bucket}-reference/$solution_name/$version/"
  echo "Lambda code: ${regional_bucket}-${region}/$solution_name/$version/"
  echo "---"

  set -x
  aws s3 sync $global_dist_dir s3://$global_bucket/$solution_name/$version/ $(if [ ! -z $profile ]; then echo "--profile $profile"; fi)
  aws s3 sync $regional_dist_dir s3://${regional_bucket}-${region}/$solution_name/$version/ $(if [ ! -z $profile ]; then echo "--profile $profile"; fi)
  set +x

  echo "------------------------------------------------------------------------------"
  echo "S3 packaging complete"
  echo "------------------------------------------------------------------------------"

  echo ""
  echo "Template to deploy:"
  echo ""
  echo "TEMPLATE='"https://"$global_bucket"."$s3domain"/$solution_name/"$version"/amazon-marketing-cloud-uploader-from-aws.template"'"
fi

cleanup
echo "Done"
exit 0
