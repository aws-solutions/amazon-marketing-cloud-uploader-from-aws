#!/usr/bin/python
# -*- coding: utf-8 -*-
##############################################################################
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.   #
#                                                                            #
#  Licensed under the Apache License Version 2.0 (the "License").            #
#  You may not use this file except in compliance with the License.          #
#  A copy of the License is located at                                       #
#                                                                            #
#      http://www.apache.org/licenses/                                       #
#                                                                            #
#  or in the "license" file accompanying this file. This file is distributed #
#  on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,        #
#  express or implied. See the License for the specific language governing   #
#  permissions and limitations under the License.                            #
##############################################################################
#
# PURPOSE:
# This function sends anonymous performance data to the AWS
# Solutions metrics API. This information is anonymous and helps improve the
# quality of the solution.
#
##############################################################################

import uuid
import lib.cfnresponse as cfn
import lib.metrics as Metrics
import logging

# format log messages like this:
formatter = logging.Formatter('{%(pathname)s:%(lineno)d} %(levelname)s - %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)

# Remove the default logger in order to avoid duplicate log messages
# after we attach our custom logging handler.
logging.getLogger().handlers.clear()
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(handler)


def handler(event, context):
    logger.info("We got this event:\n", event)
    # Each resource returns a promise with a json object to return cloudformation.
    try:
        request_type = event['RequestType']
        if request_type == 'Create' or request_type == 'Update':
            # Here we handle the CloudFormation CREATE and UPDATE events
            # sent by the AnonymousMetric custom resource.
            resource = event['ResourceProperties']['Resource']
            config = event['ResourceProperties']
            # Remove ServiceToken (lambda arn) to avoid sending AccountId
            config.pop("ServiceToken", None)
            config.pop("Resource", None)
            # Add some useful fields related to stack change
            config["CFTemplate"] = (
                    request_type + "d"
            )  # Created, Updated, or Deleted
            response_data = {}
            logger.info('Request::{} Resource::{}'.format(request_type, resource))
            if resource == 'UUID':
                response_data = {'UUID':str(uuid.uuid4())}
                response_uuid = response_data['UUID']
                cfn.send(event, context, 'SUCCESS', response_data, response_uuid)
            elif resource == 'AnonymousMetric':
                Metrics.send_metrics(config)
                response_uuid = 'Metrics Sent'
                cfn.send(event, context, 'SUCCESS', response_data, response_uuid)
            else:
                logger.error('Create failed, {} not defined in the Custom Resource'.format(resource))
                cfn.send(event, context, 'FAILED', {}, context.log_stream_name)
        elif request_type == 'Delete':
            # Here we handle the CloudFormation DELETE event
            # sent by the AnonymousMetric custom resource.
            resource = event['ResourceProperties']['Resource']
            logger.info('RESPONSE:: {}: Not required to report data for delete request.'.format(resource))
            cfn.send(event, context, 'SUCCESS', {})
        elif request_type == 'Workload':
            # Here we handle the performance metrics reported by the Glue ETL job.
            metrics = event['Metrics']
            logger.info('Workload metrics:')
            logger.info(metrics)
            Metrics.send_metrics(metrics)
        else:
            # If we get any other type of event, we handle that here.
            logger.error('RESPONSE:: {} Not supported'.format(request_type))
    except Exception as e:
        cfn.send(event, context, 'FAILED', {}, context.log_stream_name)
        logger.error(e)
