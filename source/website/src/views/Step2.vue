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
            <li>PT1M (minute)</li>
            <li>PT1H (hour)</li>
            <li>P1D (day)</li>
            <li>P7D (7 days)</li>
          </ul>
          <p>By default, this tool will automatically use the shortest possible period which is appropriate for your data and partition input files accordingly. However, you can override the auto-detected period by explicitly setting it in the dataset definition.</p>
        </b-modal>
        <b-modal id="modal-country" title="Country" ok-only>
          <p><strong>One country per file:</strong> If uploaded data contains hashed identifiers, it is recommended to separate upload data by country. For example, if you have data with both CA and US records, these records should be split into different files as the included File Preparation tool for hashing and normalization will apply country-specific normalization rules for fields such as phone number and address.</p>
        </b-modal>
        <b-row style="text-align: left">
          <b-col cols="2">
            <Sidebar :is-step2-active="true" />
          </b-col>
          <b-col cols="10">
            <h3>Define Dataset</h3>
            Specify the following details for the dataset.
            <br>
            <br>
            <div>
              <b-form-group
                id="bucket"
                label-cols-lg="1"
                label-align-lg="left"
                content-cols-lg="9"
                label="S3 Bucket:"
                label-for="bucket"
              >
                <b-form-input id="bucket" plaintext :placeholder="bucket"></b-form-input>
              </b-form-group>
              <b-form-group
                id="selected-file-field"
                label-cols-lg="1"
                label-align-lg="left"
                content-cols-lg="5"
                label="S3 Keys:"
                label-for="s3key"
              >
                <b-form-input id="s3key" v-model="new_s3key" @change="updateS3key"></b-form-input>
              </b-form-group>
              <b-form-group
                id="dataset-id-field"
                label-cols-lg="1"
                label-align-lg="left"
                content-cols-lg="5"
                description="The unique identifier of the dataset – shown in the AMC UI"
                label="Name:"
                label-for="dataset-id-input"
              >
                <b-form-input id="dataset-id-input" v-model="dataset_id"></b-form-input>
              </b-form-group>
              <b-form-group
                id="dataset-description-field"
                label-cols-lg="1"
                label-align-lg="left"
                content-cols-lg="7"
                description="Human-readable description - shown in AMC UI"
                label="Description:"
                label-for="dataset-description-input"
              >
                <b-form-input id="dataset-description-input" v-model="description" placeholder="(optional)"></b-form-input>
              </b-form-group>
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
                description="Select country - this tool applies country-specific normalization to all rows in the input file">
                <b-form-select id="country-code-dropdown" v-model="country_code">
                  <b-form-select-option value="US">US</b-form-select-option>
                  <b-form-select-option value="UK">UK</b-form-select-option>
                </b-form-select>
              </b-form-group>
            </b-col>
            </b-row>
            </div>
            <b-row>
              <b-col sm="3">
                <b-form-group v-slot="{ ariaDescribedby }">
                  <slot name="label">
                    Dataset Type:
                    <b-link v-b-modal.modal-dataset-type>
                      <b-icon-question-circle-fill variant="secondary"></b-icon-question-circle-fill>
                    </b-link>
                  </slot>
                  <b-form-radio-group
                    id="dataset_type_options"
                    v-model="dataset_type"
                    :options="dataset_type_options"
                    :aria-describedby="ariaDescribedby"
                    name="dataset-type-radios"
                    stacked
                  ></b-form-radio-group>
                </b-form-group>
              </b-col>
              <b-col v-if="dataset_type==='FACT'" sm="3">
                <b-form-group v-slot="{ ariaDescribedby }">
                  <slot name="label">
                    Dataset Period:
                    <b-link v-b-modal.modal-dataset-period>
                      <b-icon-question-circle-fill variant="secondary"></b-icon-question-circle-fill>
                    </b-link>
                  </slot>
                  <b-form-radio-group
                    id="time_period_options"
                    v-model="time_period"
                    :options="time_period_options"
                    :aria-describedby="ariaDescribedby"
                    name="time-period-radios"
                    stacked
                  ></b-form-radio-group>
                </b-form-group>
              </b-col>
            </b-row>
            <b-row>
              <b-col sm="2">
                Encryption Mode:
                <b-link v-b-modal.modal-encryption-mode>
                  <b-icon-question-circle-fill variant="secondary"></b-icon-question-circle-fill>
                </b-link>
                <div class="text-muted">
                  {{ ENCRYPTION_MODE }}
                </div>
              </b-col>
            </b-row>
            <b-row>
              <b-col sm="9" align="right">
                <button type="submit" class="btn btn-outline-primary mb-2" @click="$router.push('Step1')">
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
    name: "Step2",
    components: {
      Header, Sidebar
    },
    data() {
      return {
        new_s3key: '',
        new_dataset_definition: {},
        dataset_id: '',
        description: '',
        country_code: "US",
        dataset_type: '',
        // time_period is autodetected in Glue ETL and updated in amc_uploader.py 
        time_period: 'autodetect',
        time_period_options: [
          { value: "autodetect", text: "Autodetect" },
          { value: "PT1M", text: "PT1M" },
          { value: "PT1H", text: "PT1H" },
          { value: "P1D", text: "P1D" },
          { value: "P7D", text: "P7D" }
        ],
        isStep2Active: true,
        dataset_type_options: ["FACT","DIMENSION"],
        showFormError: false,
        formErrorMessage: ''
      }
    },
    computed: {
      ...mapState(['dataset_definition', 's3key']),
      bucket() {
        return "s3://"+this.DATA_BUCKET_NAME;
      }
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
      this.new_s3key = this.s3key
      this.new_dataset_definition = this.dataset_definition
      this.dataset_id = this.new_dataset_definition['dataSetId']
      this.description = this.new_dataset_definition['description']
      this.country_code = this.new_dataset_definition['countryCode']
      this.file_format = Object.keys(this.new_dataset_definition).includes('fileFormat')?this.new_dataset_definition['fileFormat']:this.file_format
      // set default value for file format
      if (this.file_format === '') {
        if (this.s3key.split('.').pop().toLowerCase() === "csv") {
          this.file_format = "CSV" 
        }
        else if (this.s3key.split('.').pop().toLowerCase() === "json") {
          this.file_format = "JSON" 
        }
      }
      this.time_period = Object.keys(this.new_dataset_definition).includes('period')?this.new_dataset_definition['period']:this.time_period
      this.dataset_type = this.new_dataset_definition['dataSetType']
    },
    methods: {
      updateS3key() {
        console.log("changing s3key to " + this.new_s3key)
        this.$store.commit('updateS3key', this.new_s3key)
        this.$store.commit('saveStep3FormInput', [])
      },
      onSubmit() {
        this.showFormError = false;
        this.new_dataset_definition['dataSetId'] = this.dataset_id
        this.new_dataset_definition['description'] = this.description
        this.new_dataset_definition['countryCode'] = this.country_code
        this.new_dataset_definition['period'] = this.time_period
        this.new_dataset_definition['dataSetType'] = this.dataset_type
        this.new_dataset_definition['compressionFormat'] = 'GZIP'
        if (!this.validForm()) {
          this.showFormError = true;
        } else {
          this.$store.commit('updateDatasetDefinition', this.new_dataset_definition)
          this.$router.push('Step3')
        }
      },
      validForm() {
        if (!this.s3key && !this.new_s3key) {
          this.formErrorMessage = "Missing s3key."
          return false
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
