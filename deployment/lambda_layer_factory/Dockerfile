# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

FROM public.ecr.aws/docker/library/alpine:3.20

RUN apk add --no-cache --upgrade bash
RUN apk add zip
RUN apk add python3=~3.12
RUN apk add --update py-pip

# Install Python packages and build zip files at runtime
WORKDIR /
RUN mkdir -p /packages/lambda_layer-python-3.12/python/lib/python3.12/site-packages
COPY ./docker-entrypoint.sh /

ENTRYPOINT ["sh", "docker-entrypoint.sh"]
