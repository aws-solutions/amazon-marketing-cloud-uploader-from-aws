#!/usr/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import datetime
import json
import requests


def send_metrics(config):
    metrics = {}
    # move Solution ID and UUID to the root JSON level
    metrics["Solution"] = config.pop("SolutionId", None)
    metrics["UUID"] = config.pop("UUID", None)
    metrics["TimeStamp"] = str(datetime.datetime.utcnow().isoformat())
    metrics["Data"] = config
    url = "https://metrics.awssolutionsbuilder.com/generic"
    data = json.dumps(metrics).encode("utf8")
    headers = {"content-type": "application/json"}
    req = requests.post(url, headers=headers, data=data, timeout=15)
    print("RESPONSE CODE:: {}".format(req.text))
    print("METRICS SENT:: {}".format(metrics))
