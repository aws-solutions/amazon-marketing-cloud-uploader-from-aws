<!--
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
-->

<template>
  <div>
    <div class="headerTextBackground">
      <Header />
      <b-container fluid>
        <b-alert
          v-model="showServerError"
          variant="danger"
          dismissible
        >
          Failed to get dataset list from AMC. See Cloudwatch logs for API resource /list_datasets.
        </b-alert>
        <b-alert
          v-model="showFormError"
          variant="danger"
          dismissible
        >
          Invalid dataset definition. {{ formErrorMessage }}
        </b-alert>
        <b-modal id="modal-dataset-type" title="Dataset Types" ok-only>
          <p><strong>Fact</strong> datasets represent time-series data and must include a timestamp column.</p>
          <p><strong>Dimension</strong> datasets represent any information which is not time-bound, such as CRM audience lists, campaign metadata, mapping tables, and product metadata (e.g. a table mapping ASINs to external product names).</p>
        </b-modal>
        <b-modal id="modal-encryption-mode" title="Encryption Mode" ok-only>
          This value is derived from an AWS CloudFormation parameter and can only be changed by updating the deployed stack. Possible values:
          <br><br>
          <p><strong>default:</strong> AWS Glue and AMC will perform default encryption on your behalf.</p>
          <p><strong>aws-kms:</strong> AWS Glue and AMC will encrypt data using the key specified in the `CustomerManagedKey` parameter of the base AWS CloudFormation template. The benefit to using a customer generated encryption key is the ability to revoke AMC’s access to uploaded data at any point. In addition, customers can monitor encryption key access via AWS CloudTrail event logs. See the AMC data upload documentation for more information.</p>
        </b-modal>
        <b-modal id="modal-dataset-period" title="File Partitioning" ok-only>
          <p>When uploading time series data, each file must be partitioned according to a specific unit of time. This unit of time is referred to as the <b>dataset period</b>. The available periods are:</p>
          <ul>
            <li>PT1H (hour)</li>
            <li>P1D (day)</li>
            <li>P7D (7 days)</li>
          </ul>
          <p>PT1M and Autodetect have been temporarily disabled.</p>
          <p>Autodetect will detect the shortest possible period which is appropriate for your data and partition input files accordingly.</p>
        </b-modal>
        <b-modal id="modal-file-format" title="File Format" ok-only>
          <p>The file format for input data, CSV or JSON.</p>
        </b-modal>
        <b-modal id="modal-country" title="Country" ok-only>
          <p><strong>One country per file:</strong> Identities will be resolved and addresses normalized according to the rules of this country. If uploaded data contains hashed identifiers, then separate upload data by country. For example, if you have data with both CA and US records, these records should be split into different files as the tool will apply country-specific identity resolution rules for fields such as phone number and address.</p>
        </b-modal>
        <b-row style="text-align: left">
          <b-col cols="2">
            <Sidebar :is-step3-active="true" />
          </b-col>
          <b-col cols="10">
            <h3>Define Dataset</h3>
            Specify the following details for the dataset.
            <br>
            <br>
            <div>
              <div
                class="bv-no-focus-ring mb-3"
                role="radiogroup"
                tabindex="-1"
              >
                <div class="custom-control custom-control-inline custom-radio">
                  <input
                    class="custom-control-input"
                    type="radio"
                    value="CREATE"
                    id="step3_create_new_dataset_radio"
                    name="step3_dataset_mode"
                    @change="updateDatasetMode"
                    v-model="dataset_mode"
                  /><label class="custom-control-label" for="step3_create_new_dataset_radio"
                    ><span>Create new dataset</span></label
                  >
                </div>
                <div class="custom-control custom-control-inline custom-radio">
                  <input
                    class="custom-control-input"
                    type="radio"
                    value="JOIN"
                    id="step3_append_dataset_radio"
                    name="step3_dataset_mode"
                    @change="updateDatasetMode"
                    v-model="dataset_mode"
                  /><label class="custom-control-label" for="step3_append_dataset_radio"
                    ><span>Add to existing dataset</span></label
                  >
                </div>
              </div>
              <div v-if="dataset_mode === 'JOIN'">
                Select a dataset:&nbsp;
                <b-spinner
                  v-if="datasets.length === 0 && isBusy === true"
                  type="border"
                  small
                >
                </b-spinner>
                <div v-else class="w-50">
                  <select class="custom-select" v-model="new_selected_dataset">
                    <option disabled :value="null">&#45;&#45; Choose one &#45;&#45;</option>
                    <option v-for="item in datasets" :key="item.dataSetId">
                      {{ item }}</option>
                  </select>
                </div>
                <br>
              </div>
              <div v-if="dataset_mode === 'CREATE'">
                <b-form-group
                  id="dataset-id-field"
                  label-cols-lg="1"
                  label-align-lg="left"
                  content-cols-lg="5"
                  description="Unique identifier of the dataset - shown in the AMC UI."
                  label="Name:"
                  label-for="dataset-id-input"
                >
                  <b-form-input
                    id="dataset-id-input"
                    v-model="dataset_id"
                    :state="datasetIsValid"
                  >
                  </b-form-input>
                  <b-form-invalid-feedback id="input-live-feedback">
                    A dataset with that name already exists.
                  </b-form-invalid-feedback>
                </b-form-group>
                <b-form-group
                  id="dataset-description-field"
                  label-cols-lg="1"
                  label-align-lg="left"
                  content-cols-lg="7"
                  description="Human-readable description - shown in the AMC UI."
                  label="Description:"
                  label-for="dataset-description-input"
                >
                  <b-form-input id="dataset-description-input" v-model="description" placeholder="(optional)"></b-form-input>
                </b-form-group>
                <b-row>
                  <b-col sm="2">
                    <b-form-group>
                      <slot name="label">
                        Dataset Type:
                        <b-link v-b-modal.modal-dataset-type>
                          <b-icon-question-circle-fill variant="secondary"></b-icon-question-circle-fill>
                        </b-link>
                      </slot>
                      <div class="bv-no-focus-ring" role="radiogroup" tabindex="-1">
                        <div class="custom-control custom-radio">
                          <input
                            class="custom-control-input"
                            type="radio"
                            name="dataset-type-radios"
                            value="FACT"
                            id="step_3_dataset_type_radio_fact"
                            v-model="dataset_type"
                          /><label class="custom-control-label" for="step_3_dataset_type_radio_fact"
                            ><span>FACT</span></label
                          >
                        </div>
                        <div class="custom-control custom-radio">
                          <input
                            class="custom-control-input"
                            type="radio"
                            name="dataset-type-radios"
                            value="DIMENSION"
                            id="step_3_dataset_type_radio_dimension"
                            v-model="dataset_type"
                          /><label class="custom-control-label" for="step_3_dataset_type_radio_dimension"
                            ><span>DIMENSION</span></label
                          >
                        </div>
                      </div>

                    </b-form-group>
                  </b-col>
                  <b-col v-if="dataset_type==='FACT'" sm="2">
                    <b-form-group>
                      <slot name="label">
                        Dataset Period:
                        <b-link v-b-modal.modal-dataset-period>
                          <b-icon-question-circle-fill variant="secondary"></b-icon-question-circle-fill>
                        </b-link>
                      </slot>
                      <div
                        class="bv-no-focus-ring"
                        id="time_period_options"
                        role="radiogroup"
                        tabindex="-1"
                      >
                        <div class="custom-control custom-radio">
                          <input
                            v-model="time_period"
                            class="custom-control-input"
                            id="time_period_options_BV_option_0"
                            type="radio"
                            name="time-period-radios"
                            disabled=""
                            value="autodetect"
                          /><label class="custom-control-label" for="time_period_options_BV_option_0"
                            ><span>Autodetect</span></label
                          >
                        </div>
                        <div class="custom-control custom-radio">
                          <input
                            v-model="time_period"
                            class="custom-control-input"
                            id="time_period_options_BV_option_1"
                            type="radio"
                            name="time-period-radios"
                            disabled=""
                            value="PT1M"
                          /><label class="custom-control-label" for="time_period_options_BV_option_1"
                            ><span>PT1M (minutely)</span></label
                          >
                        </div>
                        <div class="custom-control custom-radio">
                          <input
                            v-model="time_period"
                            class="custom-control-input"
                            id="time_period_options_BV_option_2"
                            type="radio"
                            name="time-period-radios"
                            value="PT1H"
                          /><label class="custom-control-label" for="time_period_options_BV_option_2"
                            ><span>PT1H (hourly)</span></label
                          >
                        </div>
                        <div class="custom-control custom-radio">
                          <input
                            v-model="time_period"
                            class="custom-control-input"
                            id="time_period_options_BV_option_3"
                            type="radio"
                            name="time-period-radios"
                            value="P1D"
                          /><label class="custom-control-label" for="time_period_options_BV_option_3"
                            ><span>P1D (daily)</span></label
                          >
                        </div>
                        <div class="custom-control custom-radio">
                          <input
                            v-model="time_period"
                            class="custom-control-input"
                            id="time_period_options_BV_option_4"
                            type="radio"
                            name="time-period-radios"
                            value="P7D"
                          /><label class="custom-control-label" for="time_period_options_BV_option_4"
                            ><span>P7D (weekly)</span></label
                          >
                        </div>
                      </div>

                    </b-form-group>
                  </b-col>
                  <b-col sm="2">
                    <b-form-group>
                      <slot name="label">
                        File Format:
                        <b-link v-b-modal.modal-file-format>
                          <b-icon-question-circle-fill variant="secondary"></b-icon-question-circle-fill>
                        </b-link>
                      </slot>
                      <div class="bv-no-focus-ring" role="radiogroup" tabindex="-1">
                        <div class="custom-control custom-radio">
                          <input
                            v-model="file_format"
                            class="custom-control-input"
                            type="radio"
                            name="file-format-radios"
                            value="CSV"
                            id="file_format_radios_option_1"
                          />
                          <label class="custom-control-label" for="file_format_radios_option_1">
                            <span>CSV</span>
                          </label>
                        </div>
                        <div class="custom-control custom-radio">
                          <input
                            v-model="file_format"
                            class="custom-control-input"
                            type="radio"
                            name="file-format-radios"
                            value="JSON"
                            id="file_format_radios_option_2"
                          />
                          <label class="custom-control-label" for="file_format_radios_option_2">
                            <span>JSON</span>
                          </label>
                        </div>
                      </div>
                    </b-form-group>
                  </b-col>
                  <b-col sm="2">
                    Encryption Mode:
                    <b-link v-b-modal.modal-encryption-mode>
                      <b-icon-question-circle-fill variant="secondary"></b-icon-question-circle-fill>
                    </b-link>
                    <div class="text-muted">
                      {{ ENCRYPTION_MODE }}
                    </div>
                    <br />
                  </b-col>
                </b-row>
              </div>
              <div>
                <b-row v-if="dataset_mode === 'JOIN'">
                  <b-col sm="2">
                    <slot name="label">
                      File Format:
                      <b-link v-b-modal.modal-file-format>
                        <b-icon-question-circle-fill variant="secondary"></b-icon-question-circle-fill>
                      </b-link>
                    </slot>
                      <div class="bv-no-focus-ring" role="radiogroup" tabindex="-1">
                        <div class="custom-control custom-radio">
                          <input
                              v-model="file_format"
                              class="custom-control-input"
                              type="radio"
                              name="file-format-radios"
                              value="CSV"
                              id="file_format_radios_option_1"
                          />
                          <label class="custom-control-label" for="file_format_radios_option_1">
                            <span>CSV</span>
                          </label>
                        </div>
                        <div class="custom-control custom-radio">
                          <input
                              v-model="file_format"
                              class="custom-control-input"
                              type="radio"
                              name="file-format-radios"
                              value="JSON"
                              id="file_format_radios_option_2"
                          />
                          <label class="custom-control-label" for="file_format_radios_option_2">
                            <span>JSON</span>
                          </label>
                        </div>
                      </div>
                  </b-col>
                  <b-col sm="2">
                    Encryption Mode:
                    <b-link v-b-modal.modal-encryption-mode>
                      <b-icon-question-circle-fill variant="secondary"></b-icon-question-circle-fill>
                    </b-link>
                    <div class="text-muted">
                      {{ ENCRYPTION_MODE }}
                    </div>
                    <br />
                  </b-col>
                </b-row>
              </div>
              <b-row>
                <b-col sm="1">
                  <slot name="label">
                    Country:
                    <b-link v-b-modal.modal-country>
                      <b-icon-question-circle-fill variant="secondary"></b-icon-question-circle-fill>
                    </b-link>
                  </slot>
                </b-col>
                <b-col sm="5">
                  <b-form-group
                    description="The country indicating where the data for this audience was collected."
                  >
                  <div>
                    <select class="custom-select" id="country-code-dropdown" v-model="country_code">
                      <option value="CA">Canada</option>
                      <option value="FR">France</option>
                      <option value="DE">Germany</option>
                      <option value="IN">India</option>
                      <option value="IT">Italy</option>
                      <option value="JP">Japan</option>
                      <option value="ES">Spain</option>
                      <option value="GB">United Kingdom</option>
                      <option value="US">United States</option></select>
                  </div>
                  </b-form-group>
                </b-col>
              </b-row>
            </div>
            <b-row>
              <b-col sm="9" align="right">
                <button type="submit" class="btn btn-outline-primary mb-2" @click="$router.push({path: '/step2'})">
                  Previous
                </button> &nbsp;
                <button type="submit" class="btn btn-primary mb-2" @click="onSubmit">
                  Next
                </button>
              </b-col>
            </b-row>
          </b-col>
        </b-row>
      </b-container>
    </div>
  </div>
</template>

<script>
import Header from '@/components/Header.vue'
import Sidebar from '@/components/Sidebar.vue'
import { mapState } from 'vuex'

export default {
  name: "Step3",
  components: {
    Header, Sidebar
  },
  data() {
    return {
      datasets: [],
      dataset_mode: 'CREATE',
      dataset_mode_options: [
        { value: 'CREATE', text: 'Create new dataset'},
        { value: 'JOIN', text: 'Add to existing dataset'}
      ],
      new_selected_dataset: null,
      new_dataset_definition: {},
      dataset_id: '',
      description: '',
      country_code: '',
      dataset_type: '',
      // time_period is autodetected in Glue ETL and updated in amc_uploader.py
      time_period: 'PT1H',
      time_period_options: [
        { value: "autodetect", text: "Autodetect", disabled: true},
        { value: "PT1M", text: "PT1M (minutely)", disabled: true },
        { value: "PT1H", text: "PT1H (hourly)" },
        { value: "P1D", text: "P1D (daily)" },
        { value: "P7D", text: "P7D (weekly)" }
      ],
      isStep3Active: true,
      dataset_type_options: ["FACT","DIMENSION"],
      file_format: "",
      file_format_options: ["CSV", "JSON"],
      isBusy: false,
      showFormError: false,
      showServerError: false,
      formErrorMessage: ''
    }
  },
  computed: {
    ...mapState(['dataset_definition', 's3key', 'selected_dataset', 'destination_endpoints']),
    datasetIsValid() {
      if (this.dataset_id === '' || this.dataset_id === undefined) return null
      else return !this.datasets.includes(this.dataset_id)
    },
  },
  deactivated: function () {
    console.log('deactivated');
  },
  activated: function () {
    console.log('activated')
  },
  created: function () {
    console.log('created')
  },
  mounted: function() {
    // Avoid running list_datasets() if the user skipped Step 1
    if (this.s3key) {
      // Run list_datasets() so we can warn users when they enter
      // a dataset name which already exists.
      this.list_datasets()
    }
    // pre-populate the form with previously selected values:
    if (this.selected_dataset !== null) {
      this.dataset_mode = 'JOIN'
      this.new_selected_dataset = this.selected_dataset
    }
    this.new_dataset_definition = this.dataset_definition
    this.dataset_id = this.new_dataset_definition['dataSetId']
    this.description = this.new_dataset_definition['description']
    this.country_code = this.new_dataset_definition['countryCode']
    this.file_format = Object.keys(this.new_dataset_definition).includes('fileFormat')?this.new_dataset_definition['fileFormat']:this.file_format
    this.time_period = Object.keys(this.new_dataset_definition).includes('period')?this.new_dataset_definition['period']:this.time_period
    this.dataset_type = this.new_dataset_definition['dataSetType']
  },
  methods: {
    async list_datasets() {
      this.showServerError = false
      this.datasets = []
      const apiName = 'amcufa-api'
      const method = 'POST'
      const data = {'destination_endpoint': this.destination_endpoints[0]}
      const resource = 'list_datasets'
      this.isBusy = true;
      try {
        console.log("sending " + method + " " + resource + " " + JSON.stringify(data))
        let requestOpts = {
          headers: {'Content-Type': 'application/json'},
          body: data
        };
        const response = await this.$Amplify.API.post(apiName, resource, requestOpts);
        if (response === null || response.Status === "Error") {
          this.showServerError = true
          this.isBusy = false;
        } else {
          this.datasets = response.dataSets.map(x => x.dataSetId).sort()
          this.isBusy = false;
        }
      } catch (e) {
        console.log("ERROR: " + e.response.data.message)
        this.response = e.response.data.message
      }
    },
    updateDatasetMode() {
      console.log("Changing dataset mode to: " + this.dataset_mode)
      if (this.dataset_mode === 'CREATE') {
        // reset form fields for JOIN
        this.new_selected_dataset = null
        this.$store.commit('updateSelectedDataset', this.new_selected_dataset)
      }
      if (this.dataset_mode === 'JOIN') {
        this.list_datasets()
        // reset form fields for CREATE
        this.dataset_id = ''
        this.dataset_type = ''
        this.$store.commit('updateSelectedDataset', this.new_selected_dataset)
      }
    },
    onSubmit() {
      this.showFormError = false;
      this.new_dataset_definition['dataSetId'] = this.dataset_id
      this.new_dataset_definition['description'] = this.description
      this.new_dataset_definition['period'] = this.time_period
      this.new_dataset_definition['dataSetType'] = this.dataset_type
      this.new_dataset_definition['countryCode'] = this.country_code
      this.new_dataset_definition['fileFormat'] = this.file_format
      // The compressionFormat must be GZIP because GZIP is the only supported
      // value. See AMC Data Upload documentation.
      this.new_dataset_definition['compressionFormat'] = 'GZIP'
      if (!this.validForm()) {
        this.showFormError = true;
      } else {
        if (this.dataset_mode === 'CREATE') {
          this.$store.commit('updateDatasetDefinition', this.new_dataset_definition)
          this.$router.push({path: '/step4'})
        } else if (this.dataset_mode === 'JOIN') {
          this.$store.commit('updateSelectedDataset', this.new_selected_dataset)
          this.$router.push({path: '/step4'})
        } else {
          this.formErrorMessage = "Invalid dataset mode."
          this.showFormError = true;
        }
      }
    },
    validForm() {
      if (!this.s3key) {
        this.formErrorMessage = "Missing s3key."
        return false
      }
      if (this.dataset_mode === 'JOIN' && this.new_selected_dataset == null) {
        this.formErrorMessage = "Missing dataset selection."
        return false
      }
      if (!this.file_format) {
        this.formErrorMessage = "Missing file format."
        return false
      }
      if (!this.new_dataset_definition['countryCode']  || this.new_dataset_definition['countryCode'].length === 0) {
        this.formErrorMessage = "Missing country."
        return false
      }
      if (this.dataset_mode === 'JOIN') {
        // No more checks needed if user is appending to existing dataset.
        return true
      }
      if (!this.new_dataset_definition['dataSetId'] || this.new_dataset_definition['dataSetId'].length === 0) {
        this.formErrorMessage = "Missing dataset name."
        return false
      }
      if (this.dataset_id.indexOf(' ') >= 0) {
        this.formErrorMessage = "Dataset name must not contain spaces."
        return false
      }
      if (/^[a-zA-Z0-9_-]+$/.test(this.dataset_id) === false) {
        this.formErrorMessage = "Dataset name must match regex ^[a-zA-Z0-9_-]+$"
        return false
      }
      if (!this.new_dataset_definition['dataSetType']  || this.new_dataset_definition['dataSetType'].length === 0) {
        this.formErrorMessage = "Missing dataset type."
        return false
      }
      return true
    }
  }
}
</script>
