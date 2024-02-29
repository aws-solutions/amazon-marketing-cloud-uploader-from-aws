// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import { createStore as _createStore } from 'vuex'
import state from './state'
import mutations from './mutations'
import actions from './actions'

export default new _createStore({
  state,
  mutations,
  actions
})
