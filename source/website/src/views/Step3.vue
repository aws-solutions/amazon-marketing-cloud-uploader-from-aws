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
          v-if="showServerError"
          v-model="showServerError"
          variant="danger"
          dismissible
        >
          <div v-if="serverErrorMessage">ERROR. {{ serverErrorMessage }}</div>
          <div v-else>ERROR. See Cloudwatch logs for API Handler.</div>
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
            <li>P1M (month)</li>
          </ul>
          <p>Select "DIMENSION" if no specific partition scheme is required for the dataset creation.</p>
        </b-modal>
        <b-modal id="modal-file-format" title="File Format" ok-only>
          <p>The file format for input data, CSV or JSON.</p>
        </b-modal>
        <b-modal id="modal-country" title="Country" ok-only>
          <p><strong>One country per file:</strong> Identities will be resolved and addresses normalized according to the rules of this country. If uploaded data contains hashed identifiers, then separate upload data by country. For example, if you have data with both CA and US records, these records should be split into different files as the tool will apply country-specific identity resolution rules for fields such as phone number and address.</p>
        </b-modal>
        <b-modal id="modal-update-strategy" title="Update Strategy" ok-only>
          <p><strong>ADDITIVE:</strong></p>
            <ul>
              <li><strong>For fact datasets:</strong> This strategy adds new records to records that may already be present in each time-based partition of the table. If the table already contains records, then the (new) record set being uploaded may overlap with the existing records. These overlaps are partition overlaps.</li>
              <li><strong>For dimension datasets:</strong> Dimension datasets are a single partition of records. This strategy, when used with a dimension dataset, will add the uploaded records to the existing records.</li>
            </ul>
          <p><strong>FULL_REPLACE:</strong></p>
            <ul>
              <li><strong>For fact datasets:</strong> The uploaded data replaces all records previously saved in the tables.</li>
              <li><strong>For dimension datasets:</strong> Dimension datasets have a single partition of records. This strategy will replace all existing records in that partition with the records to be uploaded.</li>
            </ul>
          <p><strong>OVERLAP_REPLACE:</strong></p>
            <ul>
              <li><strong>This strategy applies for uploads to fact datasets only:</strong> When a data upload is performed with OVERLAP_REPLACE as the strategy, then new data will be added to table partitions. Any overlapping partitions will be removed and replaced with new content.</li>
            </ul>
          <p><strong>OVERLAP_KEEP:</strong></p>
            <ul>
              <li><strong>This strategy applies for uploads to fact datasets only:</strong> All new data for non-overlapping partitions will be added to the table. Any overlapping partitions will retain their original data. When the upload overlaps with any partitions that already have data, the original data of the overlapping partition(s) is RETAINED, and those in the upload are ignored.</li>
            </ul>
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
                <div>
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
                </div>
                <br>
                <b-row>
                  <b-col sm="3">
                    <slot name="label">
                      Update Strategy:
                      <b-link v-b-modal.modal-update-strategy>
                        <b-icon-question-circle-fill variant="secondary"></b-icon-question-circle-fill>
                      </b-link>
                    </slot>
                      <div class="bv-no-focus-ring" role="radiogroup" tabindex="-1">
                        <div class="custom-control custom-radio">
                          <input
                              v-model="update_strategy"
                              class="custom-control-input"
                              type="radio"
                              name="update-strategy-radios"
                              value="ADDITIVE"
                              id="update-strategy-radios_option_1"
                          />
                          <label class="custom-control-label" for="update-strategy-radios_option_1">
                            <span>ADDITIVE</span>
                          </label>
                        </div>
                        <div class="custom-control custom-radio">
                          <input
                              v-model="update_strategy"
                              class="custom-control-input"
                              type="radio"
                              name="update-strategy-radios"
                              value="FULL_REPLACE"
                              id="update-strategy-radios_option_2"
                          />
                          <label class="custom-control-label" for="update-strategy-radios_option_2">
                            <span>FULL_REPLACE</span>
                          </label>
                        </div>
                        <div class="custom-control custom-radio">
                          <input
                              v-model="update_strategy"
                              class="custom-control-input"
                              type="radio"
                              name="update-strategy-radios"
                              value="OVERLAP_REPLACE"
                              id="update-strategy-radios_option_3"
                          />
                          <label class="custom-control-label" for="update-strategy-radios_option_3">
                            <span>OVERLAP_REPLACE</span>
                          </label>
                        </div>
                        <div class="custom-control custom-radio">
                          <input
                              v-model="update_strategy"
                              class="custom-control-input"
                              type="radio"
                              name="update-strategy-radios"
                              value="OVERLAP_KEEP"
                              id="update-strategy-radios_option_4"
                          />
                          <label class="custom-control-label" for="update-strategy-radios_option_4">
                            <span>OVERLAP_KEEP</span>
                          </label>
                        </div>
                      </div>
                  </b-col>
                  <b-col sm="3">
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
                </b-row>
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
                  <b-form-valid-feedback v-if="isBusy" id="input-live-feedback">
                    Validating name... <b-spinner small></b-spinner>
                  </b-form-valid-feedback>
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
                  <b-col sm="3">
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
                            id="time_period_options_BV_option_1"
                            type="radio"
                            name="time-period-radios"
                            value="DIMENSION"
                          /><label class="custom-control-label" for="time_period_options_BV_option_1"
                            ><span>DIMENSION</span></label
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
                            value="P1M"
                          /><label class="custom-control-label" for="time_period_options_BV_option_4"
                            ><span>P1M (monthly)</span></label
                          >
                        </div>
                      </div>
                    </b-form-group>
                  </b-col>
                  <b-col sm="3">
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
                  <b-col sm="3">
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
              <br>
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
                      <option value="Not Applicable">Not Applicable</option>
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
                <button type="submit" class="btn btn-primary mb-2" :disabled="showServerError || isBusy" @click="onSubmit">
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
import Header from '@/components/Header.vue';
import Sidebar from '@/components/Sidebar.vue';
import { API } from 'aws-amplify';
import { mapState } from 'vuex';

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
      dataset_id: null,
      description: '',
      country_code: '',
      // time_period is autodetected in Glue ETL and updated in amc_uploader.py
      time_period: '',
      time_period_options: [
        { value: "DIMENSION", text: "DIMENSION" },
        { value: "PT1H", text: "PT1H (hourly)" },
        { value: "P1D", text: "P1D (daily)" },
        { value: "P1M", text: "P1M (monthly)" }
      ],
      isStep3Active: true,
      file_format: "",
      file_format_options: ["CSV", "JSON"],
      update_strategy: "",
      isBusy: false,
      showFormError: false,
      showServerError: false,
      serverErrorMessage: '',
      formErrorMessage: '',
      userId: null,
      new_s3key: null,
    }
  },
  computed: {
    ...mapState(['dataset_definition', 's3key', 'selected_dataset', 'amc_instances_selected']),
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
    this.userId = this.USER_POOL_ID
    this.list_datasets(this.amc_instances_selected)
    this.new_s3key = this.s3key
    // Avoid running list_datasets() if the user skipped Step 1
    if (this.s3key) {
      // Run list_datasets() so we can warn users when they enter
      // a dataset name which already exists.
      this.list_datasets()
    }
    // pre-populate the form with previously selected values:
    if (this.dataset_definition) {
      this.new_dataset_definition = this.dataset_definition
    }
    this.dataset_id = this.new_dataset_definition['dataSetId']
    this.description = this.new_dataset_definition['description']
    this.country_code = this.new_dataset_definition['countryCode']
    this.file_format = Object.keys(this.new_dataset_definition).includes('fileFormat')?this.new_dataset_definition['fileFormat']:this.file_format
    this.time_period = Object.keys(this.new_dataset_definition).includes('period')?this.new_dataset_definition['period']:this.time_period
    this.update_strategy = this.new_dataset_definition['updateStrategy']
  },
  methods: {
    async list_datasets(amc_instances_selected) {
      if (!amc_instances_selected) return
      // Close any visible server error alert.
      this.showServerError = false
      // Reset the dataset list which is shown in the dropdown for JOIN.
      this.datasets = []
      // Reset the user's previous selection in the dataset dropdown for JOIN.
      this.new_selected_dataset = null
      this.$store.commit('updateSelectedDataset', this.new_selected_dataset)
      const apiName = 'amcufa-api'
      const method = 'POST'
      const data = {
        'instance_id': amc_instances_selected[0].instance_id,
        "marketplace_id": amc_instances_selected[0].marketplace_id,
        "advertiser_id": amc_instances_selected[0].advertiser_id,
        "user_id": this.userId
      }
      const resource = 'list_datasets'
      this.isBusy = true;
      try {
        console.log("sending " + method + " " + resource + " " + JSON.stringify(data))
        let requestOpts = {
          headers: {'Content-Type': 'application/json'},
          body: data
        };
        const response = await API.post(apiName, resource, requestOpts);
        if (response === null || response.Status === "Error") {
          this.showServerError = true
          this.isBusy = false;
        } else if (response.authorize_url){
          const current_page = "step3"
          const state_key = current_page + this.userId + Date.now()
          const b64_state_key = btoa(current_page + this.userId + Date.now())
          let state_vars = {
            "amc_instances_selected": amc_instances_selected,
            "s3key": this.new_s3key,
            "dataset_definition": this.new_dataset_definition,
            "selected_dataset": this.new_selected_dataset,
            "current_page": current_page
          }
          localStorage.setItem(state_key, JSON.stringify(state_vars))
          window.location.href = response.authorize_url + "&state=" + b64_state_key
        }
        else {
          this.datasets = response.dataSets.map(x => x.dataSetId).sort()
          this.isBusy = false;
        }
      } catch (e) {
        console.log("ERROR: " + e.response.data.message)
        this.response = e.response.data.message
        this.showServerError = true
        this.serverErrorMessage = e.response.data.message
        this.isBusy = false
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
        this.list_datasets(this.amc_instances_selected)
        // reset form fields for CREATE
        this.dataset_id = ''
        this.dataset_type = ''
      }
    },
    onSubmit() {
      this.showFormError = false;
      this.new_dataset_definition['dataSetId'] = this.dataset_id
      this.new_dataset_definition['description'] = this.description
      this.new_dataset_definition['period'] = this.time_period
      this.new_dataset_definition['countryCode'] = this.country_code
      this.new_dataset_definition['fileFormat'] = this.file_format
      // the Glue script will always output a GZIP compressed file for upload to AMC
      this.new_dataset_definition['compressionFormat'] = 'GZIP'
      // when creating a new dataset, default update strategy to ADDITIVE since there is no previous data being updated
      this.new_dataset_definition['updateStrategy'] = (this.dataset_mode === 'CREATE') ? 'ADDITIVE' : this.update_strategy;
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
      if (this.dataset_mode === 'CREATE' && !this.datasetIsValid) {
        this.formErrorMessage = "Check dataset name."
        return false
      }
      if (this.dataset_mode === 'JOIN' && this.new_selected_dataset == null) {
        this.formErrorMessage = "Missing dataset selection."
        return false
      }
      if (this.dataset_mode === 'JOIN' && !this.new_dataset_definition['updateStrategy']) {
        this.formErrorMessage = "Missing update strategy."
        return false
      }
      if (!this.file_format) {
        this.formErrorMessage = "Missing file format."
        return false
      }
      if (!this.new_dataset_definition['countryCode']) {
        this.formErrorMessage = "Missing country."
        return false
      }
      if (this.dataset_mode === 'JOIN') {
        // No more checks needed if user is appending to existing dataset.
        return true
      }
      if (!this.new_dataset_definition['dataSetId']) {
        this.formErrorMessage = "Missing dataset name."
        return false
      }
      if (/^[a-z]([_a-z0-9]+$)/.test(this.dataset_id) === false) {
        this.formErrorMessage = "Dataset name must match regex ^[a-z]([_a-z0-9]+$)"
        return false
      }
      if (!this.new_dataset_definition['period']) {
        this.formErrorMessage = "Missing dataset period."
        return false
      }
      return true
    }
  }
}
</script>
