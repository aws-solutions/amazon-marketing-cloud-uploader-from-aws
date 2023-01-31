<!--
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
-->

<template>
  <div>
    <div class="headerTextBackground">
      <Header />
      <b-modal
        v-model="showModal"
        :title="modal_title"
        ok-only
        @ok="hideModal"
      >
        {{ response }}
      </b-modal>
      <b-container fluid>
        <b-row style="text-align: left">
          <b-col cols="2">
            <Sidebar :is-step5-active="true" />
          </b-col>
          <b-col cols="10">
            <h3>Confirm Details</h3>
            <b-row>
              <b-col sm="7">
                Click Submit to record this dataset in AMC.
              </b-col>
              <b-col sm="3" align="right">
                <button type="submit" class="btn btn-outline-primary mb-2" @click="$router.push({path: '/step4'})">
                  Previous
                </button> &nbsp;
                <button type="submit" class="btn btn-primary mb-2" @click="onSubmit">
                  Submit
                  <b-spinner v-if="isBusy" style="vertical-align: sub" small label="Spinning"></b-spinner>
                </button>
              </b-col>
            </b-row>
            <b-row>
              <b-col cols="7">
                <h5>Input files:</h5>
                <ul>
                  <li v-for="item in s3key.split(',')">
                    {{ "s3://" + DATA_BUCKET_NAME + "/" + item }}
                  </li>
                </ul>
                <h5>Destinations:</h5>
                <ul>
                <li v-for="amc_instance in destinations">
                  {{ amc_instance }}
                </li>
                </ul>
                <br>
                <h5>Dataset Attributes:</h5>
                <b-table
                  small
                  outlined
                  :items="dataset.other_attributes"
                  thead-class="hidden_header"
                  show-empty
                >
                </b-table>
                <template #empty="scope">
                  {{ scope.emptyText }}
                </template>
              </b-col>
            </b-row>
            <b-row>
              <b-col cols="10">
                <h5>Columns:</h5>
                <b-table 
                  v-if="dataset.columns && dataset.columns.length > 0"
                  small
                  outlined
                  :fields="column_fields"
                  :items="dataset.columns"
                >
                </b-table>
                <b-table
                  v-else
                  small
                  outlined
                  :items="dataset.columns"
                  show-empty
                ></b-table>
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
  import {mapState} from "vuex";

  export default {
    name: "Step5",
    components: {
      Header, Sidebar
    },
    data() {
      return {
        column_fields: ['name', 'description', 'dataType', 'columnType', 'nullable', 'isMainUserId', 'isMainUserIdType', 'isMainUserId', 'externalUserIdType.identifierType','isMainEventTime'],
        dataset_fields: [{key: '0', label: 'Name'}, {key: '1', label: 'Value'}],
        isBusy: false,
        showModal: false,
        modal_title: '',
        isStep5Active: true,
        response: ''
      }
    },
    computed: {
      ...mapState(['deleted_columns', 'dataset_definition', 's3key', 'destinations']),
      encryption_key() {
        if (this.CUSTOMER_MANAGED_KEY === "") {
          return "default"
        } else {
          return this.CUSTOMER_MANAGED_KEY
        }
      },
      pii_fields() {
         return (this.dataset.columns.filter(x => x.externalUserIdType).map(x => (new Object( {'column_name':x.name, 'pii_type': x.externalUserIdType.identifierType}))))
      },
      timestamp_column_name() {
        const timestamp_column = this.dataset.columns.filter(x => x.isMainEventTime).map(x => x.name)
        // The Glue ETL job requires timestamp_column_name to be an empty string 
        // for all DIMENSION datasets.
        const dataset_type = this.dataset_definition['dataSetType']
        if (dataset_type == 'FACT' && timestamp_column && timestamp_column.length > 0)
          return timestamp_column[0]
        else
          return ''
      },
      dataset() {
        let {columns, ...other_attributes} = this.dataset_definition
        other_attributes['encryption_mode'] = this.ENCRYPTION_MODE
        return {"columns": columns, "other_attributes": Object.entries(other_attributes)}
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
    methods: {
      hideModal() {
        this.showModal = false
      },
      onSubmit() {
        this.send_request('POST', 'create_dataset', {'body': this.dataset_definition})
      },
      async send_request(method, resource, data) {
        console.log("sending " + method + " " + resource + " " + JSON.stringify(data))
        const apiName = 'amcufa-api'
        let response = ""
        this.isBusy = true;
        try {
          if (method === "GET") {
            response = await this.$Amplify.API.get(apiName, resource);
          } else if (method === "POST") {
            let requestOpts = {
              headers: {'Content-Type': 'application/json'},
              body: data
            };
            response = await this.$Amplify.API.post(apiName, resource, requestOpts);
          }
          console.log(JSON.stringify(response))
          console.log("Dataset defined successfully")
          
          // Start Glue ETL job now that the dataset has been accepted by AMC
          let s3keysList = this.s3key.split(',').map((item) => item.trim())

          for (let key of s3keysList) {
            console.log("Starting Glue ETL job for s3://" + this.DATA_BUCKET_NAME + "/" + key)
            resource = 'start_amc_transformation'
            data = {'sourceBucket': this.DATA_BUCKET_NAME, 'sourceKey': key, 'outputBucket': this.ARTIFACT_BUCKET_NAME, 'piiFields': JSON.stringify(this.pii_fields),'deletedFields': JSON.stringify(this.deleted_columns), 'timestampColumn': this.timestamp_column_name, 'datasetId': this.dataset_definition.dataSetId, 'period': this.dataset_definition.period}
            let requestOpts = {
              headers: {'Content-Type': 'application/json'},
              body: data
            };
            console.log("POST " + resource + " " + JSON.stringify(requestOpts))
            response = await this.$Amplify.API.post(apiName, resource, requestOpts);
            console.log(response)
            console.log(JSON.stringify(response))
            console.log("Started Glue ETL job")
          }
          
          // Navigate to next step
          this.$router.push({path: '/step5'})
        }
        catch (e) {
          this.modal_title = e.response.status + " " + e.response.statusText
          console.log("ERROR: " + this.modal_title)
          this.isBusy = false;
          this.response = JSON.stringify(e.response.data)  
          this.showModal = true
        }
        this.isBusy = false;
      }
    }
  }
</script>

<style>
.hidden_header {
  display: none;
}
</style>
