// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

const SriPlugin = require('webpack-subresource-integrity');

module.exports = {
  configureWebpack: {
    output: {
      crossOriginLoading: 'anonymous',
    },
    plugins: [
      new SriPlugin({
        hashFuncNames: ['sha256', 'sha384'],
        enabled: false
      }),
    ],
    performance: {
      hints: false
    }
  }
};
