# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
#
# ###############################################################################
# PURPOSE:
#   * Unit test for project api endpoints and workflow.
#
# USAGE:
#   ./run_test.sh --run_unit_test --test-file-name test_tasks.py
###############################################################################

import json
import os

import pytest
from moto import mock_aws


def test_safe_json():
    from share.tasks import safe_json_loads

    assert safe_json_loads("test") == "test"
    assert safe_json_loads(json.dumps({"test": "123"})) == {"test": "123"}


@mock_aws
def test_create_update_secret_exception():
    from share.tasks import create_update_secret

    with pytest.raises(Exception):
        create_update_secret(secret_id=123, secret_string="test_string")


def test_get_client_id_secret_env():
    from share.tasks import get_client_id_secret_env

    client_id = os.environ["CLIENT_ID"]
    client_secret = os.environ["CLIENT_SECRET"]

    assert get_client_id_secret_env() == (client_id, client_secret)

    os.environ["CLIENT_ID"] = ""
    os.environ["CLIENT_SECRET"] = ""

    assert get_client_id_secret_env() == ('', '')

    # Reapply env client_id and secrets.
    os.environ["CLIENT_ID"] = client_id
    os.environ["CLIENT_SECRET"] = client_secret
