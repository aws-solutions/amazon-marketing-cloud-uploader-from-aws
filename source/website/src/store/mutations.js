// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

export default {
  updateDeletedColumns (state, value) {
    state.deleted_columns = value
  },
  updateDatasetDefinition (state, value) {
    state.dataset_definition = value
  },
  saveStep3FormInput (state, value) {
    state.step3_form_input = value
  },
  updateS3key (state, value) {
    state.s3key = value
  },
  updateSelectedDataset (state, value) {
    state.selected_dataset = value
  },
  updateSelectedAmcInstances (state, value) {
    state.amc_instances_selected = value
  },
  updateAmcMonitor (state, value) {
    state.amc_monitor = value
  },
  updateAmcSelectorVisibility (state, value) {
    state.amc_selector_visible_state = value
  }
}
