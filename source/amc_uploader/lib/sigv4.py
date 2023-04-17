# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
#
# ###########################################################################
# Below are functions for constructing sigv4 signed HTTP requests
# Reference:
# http://docs.aws.amazon.com/general/latest/gr/signature-v4-examples.html#signature-v4-examples-python
#
# The requests package is not included in the default AWS Lambda env
# be sure that it has been provided in a Lambda layer.
#
##########################################################################

import importlib
import sys

sys.path.insert(0, "./share/sigv4.py")
sigv4 = importlib.import_module("share.sigv4")
