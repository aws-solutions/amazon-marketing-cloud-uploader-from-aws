// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

const { SubresourceIntegrityPlugin } = require('webpack-subresource-integrity');

module.exports = {
  // Do not show a full-screen overlay in the browser
  // when there are compiler errors or warnings:
  devServer: {
    client: {
      overlay: false,
    },
  },
  configureWebpack: {
    optimization: {
      realContentHash: true
    },
    output: {
      crossOriginLoading: 'anonymous',
    },
    plugins: [
      new SubresourceIntegrityPlugin()
    ],
    performance: {
      hints: false
    }
  }
};
