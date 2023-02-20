# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
#
# ###############################################################################
# PURPOSE:
#   * Regression test for anonymous-data-logger/.
# USAGE:
#   ./run_test.sh --run_unit_test
###############################################################################

from unittest.mock import MagicMock, patch

import pytest




@pytest.fixture
def fake_event():
    return {
        "ResponseURL": "https://test.com/test",
        "StackId": 12345,
        "RequestId": 67890,
        "LogicalResourceId": 1112131415,
        "ResourceProperties": {
            "Resource": None,
        },
    }


@pytest.fixture
def fake_context():
    return MagicMock(log_stream_name="fake_log_stream")


@patch("requests.put")
@patch("urllib.request.urlopen")
def test_handler(mock_response_open, mock_response_put, fake_event, fake_context):

    from anonymous_data_logger.anonymous_data_logger import handler
    
    fake_event["RequestType"] = "Create"
    fake_event["ResourceProperties"]["Resource"] = "UUID"
    fake_event["ResourceProperties"]["ServiceToken"] = "some arn"

    mock_response_open.return_value.getcode().return_value = 200
    mock_response_put.return_value = MagicMock(reason="200")

    handler(
        event=fake_event,
        context=fake_context,
    )

    fake_event["RequestType"] = "Update"
    handler(
        event=fake_event,
        context=fake_context,
    )

    fake_event["ResourceProperties"]["Resource"] = "AnonymousMetric"
    fake_event["RequestType"] = "Create"
    handler(
        event=fake_event,
        context=fake_context,
    )

    fake_event["RequestType"] = "Update"
    handler(
        event=fake_event,
        context=fake_context,
    )


    with patch('logging.Logger.info') as log_mock:
        fake_resource = "AnonymousMetric"
        fake_event["RequestType"] = "Delete"
        fake_event["ResourceProperties"]["Resource"] = fake_resource
        handler(
            event=fake_event,
            context=fake_context,
        )
        log_mock.assert_called_with("RESPONSE:: {}: Not required to report data for delete request.".format(
                        fake_resource
        ))

        fake_event["RequestType"] = "Workload"
        fake_event["Metrics"] = "some metrics"
        handler(
            event=fake_event,
            context=fake_context,
        )
        log_mock.assert_called_with("some metrics")

    with patch('logging.Logger.error') as log_mock:
        fake_resource = "FakeAnonymousMetric"
        fake_event["ResourceProperties"]["Resource"] = fake_resource
        fake_event["RequestType"] = "Create"
        handler(
            event=fake_event,
            context=fake_context,
        )
        log_mock.assert_called_with("Create failed, {} not defined in the Custom Resource".format(
                        fake_resource
        ))

        fake_event["ResourceProperties"]["Resource"] = fake_resource
        fake_event["RequestType"] = "Update"
        handler(
            event=fake_event,
            context=fake_context,
        )
        log_mock.assert_called_with("Create failed, {} not defined in the Custom Resource".format(
                        fake_resource
        ))

        fake_event["ResourceProperties"]["Resource"] = fake_resource
        fake_event["RequestType"] = "DOES NOT EXIST"
        handler(
            event=fake_event,
            context=fake_context,
        )
        log_mock.assert_called_with("RESPONSE:: {} Not supported".format(fake_event["RequestType"]))
      
