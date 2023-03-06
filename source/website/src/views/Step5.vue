<!--
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
-->

<template>
  <div>
    <div class="headerTextBackground">
      <Header />
      <b-container fluid>
        <b-row style="text-align: left">
          <b-col cols="2">
            <Sidebar :is-step5-active="true" />
          </b-col>
          <b-col cols="10">
            <h3>Confirm Details</h3>
            <b-row>
              <b-col sm="7">
                <p v-if="isValid">
                  Click Submit to record this dataset in AMC.
                </p>
                <p v-else class="text-danger">
                  Invalid dataset. Verify that your dataset definition is complete.
                </p>
              </b-col>
              <b-col sm="3" align="right">
                <button type="submit" class="btn btn-outline-primary mb-2" @click="$router.push({path: '/step4'})">
                  Previous
                </button> &nbsp;
                <button type="submit" class="btn btn-primary mb-2" :disabled="!isValid || isBusy || disable_submit" @click="onSubmit">
                  Submit
                  <b-spinner v-if="isBusy" style="vertical-align: sub" small label="Spinning"></b-spinner>
                </button>
              </b-col>
            </b-row>
            <b-row>
              <b-col cols="11">
                <h5>Input files:</h5>
                <div v-if="s3key !== ''">
                  <ul>
                    <li v-for="item in s3key.split(',')" :key="item">
                      {{ "s3://" + DATA_BUCKET_NAME + "/" + item }}
                    </li>
                  </ul>
                </div>
                <div v-else>
                  <br>
                </div>
                <h5>Destinations:</h5>
                <ul>
                  <li v-for="endpoint in destination_endpoints" :key="endpoint">
                    <div v-if="endpoint_request(endpoint).is_busy">
                      {{ endpoint }} <b-spinner small></b-spinner>
                    </div>
                    <div v-else>
                      <div v-if="!endpoint_request(endpoint).status">
                        {{ endpoint }} {{ endpoint_request(endpoint).status }}
                      </div>
                      <div v-else-if="endpoint_request(endpoint).status.toLowerCase().includes('error')">
                        {{ endpoint }} <p class="text-danger" style="display:inline">
                          <br>{{ endpoint_request(endpoint).status }}
                        </p>
                      </div>
                      <div v-else-if="JSON.stringify(endpoint_request(endpoint).status).length > 0">
                        {{ endpoint }} (<b-link variant="link" @click="onClickMonitor(endpoint)">
                          monitor
                        </b-link>)
                      </div>
                    </div>
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
                <div v-if="deleted_columns.length > 0">
                  Excluding columns {{ deleted_columns }} in {{ s3key }} from upload.
                </div>
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
        disable_submit: false,
        destination_fields: [
          {key: 'endpoint', label: 'AMC Endpoint', sortable: true},
          {key: 'actions', label: 'Actions'},
        ],
        column_fields: ['name', 'description', 'dataType', 'columnType', 'nullable', 'isMainUserId', 'isMainUserIdType', 'isMainUserId', 'externalUserIdType.identifierType','isMainEventTime'],
        dataset_fields: [{key: '0', label: 'Name'}, {key: '1', label: 'Value'}],
        endpoint_request_state: [],
        isStep5Active: true,
        response: '',
        apiName: 'amcufa-api'
      }
    },
    computed: {
      ...mapState(['deleted_columns', 'dataset_definition', 's3key', 'selected_dataset', 'destination_endpoints']),
      isBusy() {
        // if any endpoint is busy then return true
        return this.endpoint_request_state.filter(x => x.is_busy === true).length > 0
      },
      isValid() {
        return !(this.s3key === '' || this.destination_endpoints.length === 0 || !this.dataset.columns || this.dataset.columns.length === 0)
      },
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
      this.endpoint_request_state = this.destination_endpoints.map(x => ({
        "endpoint": x,
        "status": null,
        "is_busy": false
      }))
    },
    methods: {
      onClickMonitor(endpoint) {
        this.$store.commit('updateAmcMonitor', endpoint)
        this.$router.push({path: '/step6'})
      },
      endpoint_request(endpoint) {
        const i =  this.endpoint_request_state.findIndex(x => x.endpoint === endpoint)
        if (i !== null) {
          return this.endpoint_request_state[i]
        }
      },
      onSubmit() {
        this.disable_submit = true
        // Send a request to create datasets to each endpoint in parallel.
        if (this.selected_dataset === null) {
          this.create_datasets(this.destination_endpoints)
        } else {
          this.check_dataset_exists(this.destination_endpoints, this.selected_dataset)
        }
        console.log("Finished defining datasets.")
        // Wait for all those requests to complete, then start the glue job.
        this.start_amc_transformation('POST', 'start_amc_transformation', {
          'sourceBucket': this.DATA_BUCKET_NAME,
          // 'sourceKey' is added in start_amc_transformation().
          'outputBucket': this.ARTIFACT_BUCKET_NAME,
          'piiFields': JSON.stringify(this.pii_fields),
          'deletedFields': JSON.stringify(this.deleted_columns),
          'timestampColumn': this.timestamp_column_name,
          'datasetId': this.dataset_definition.dataSetId,
          'period': this.dataset_definition.period,
          'countryCode': this.dataset_definition.countryCode,
          'destination_endpoints': JSON.stringify(this.destination_endpoints)
        })
      },
      check_dataset_exists(destination_endpoints, dataset_id) {
        // set busy status to show spinner for each endpoint
        this.endpoint_request_state = this.destination_endpoints.map(x => ({
          "endpoint": x,
          "status": "",
          "is_busy": true
        }))
        destination_endpoints.forEach(endpoint => {
          this.send_request('POST', 'describe_dataset', {
            'body': this.dataset_definition,
            'dataSetId': dataset_id,
            'destination_endpoint': endpoint
          }).then(result => {
            console.log("describe_dataset() result for " + endpoint + ":")
            console.log(JSON.stringify(result))
            const j = this.endpoint_request_state.findIndex(x => x.endpoint === endpoint)
            if (j != null) {
              this.endpoint_request_state[j].is_busy = false
              this.endpoint_request_state[j].status = JSON.stringify(result)
            }
          })
        })
      },
      create_datasets(destination_endpoints) {
        // set busy status to show spinner for each endpoint
        this.endpoint_request_state = this.destination_endpoints.map(x => ({
          "endpoint": x,
          "status": "",
          "is_busy": true
        }))
        destination_endpoints.forEach(endpoint => {
          this.send_request('POST', 'create_dataset', {
            'body': this.dataset_definition,
            'destination_endpoint': endpoint
          }).then(result => {
            console.log("create_dataset() result for " + endpoint + ":")
            console.log(JSON.stringify(result))
            const j = this.endpoint_request_state.findIndex(x => x.endpoint === endpoint)
            if (j != null) {
              this.endpoint_request_state[j].is_busy = false
              this.endpoint_request_state[j].status = JSON.stringify(result)
            }
          })
        })
      },
      async send_request(method, resource, data) {
        this.modal_title = ''
        this.response = ''
        console.log("sending " + method + " " + resource + " " + JSON.stringify(data))
        let requestOpts = {
          headers: {'Content-Type': 'application/json'},
          body: data
        };
        try {
          const result = await this.$Amplify.API.post(this.apiName, resource, requestOpts)
          return result
        } catch (e) {
          console.log(e.toString())
          return e.toString()
        }
      },
      async start_amc_transformation(method, resource, data) {
        try {
          // Start Glue ETL job now that the dataset has been accepted by AMC
          let s3keysList = this.s3key.split(',').map((item) => item.trim())
          for (let key of s3keysList) {
            data["sourceKey"] = key
            console.log("Starting Glue ETL job for s3://" + this.DATA_BUCKET_NAME + "/" + key)
            let requestOpts = {
              headers: {'Content-Type': 'application/json'},
              body: data
            };
            console.log("POST " + resource + " " + JSON.stringify(requestOpts))
            this.response = await this.$Amplify.API.post(this.apiName, resource, requestOpts);
            console.log("Started Glue ETL job")
            console.log(JSON.stringify(this.response))
          }
        } catch (e) {
          console.log(e.toString())
          return
        }
      }
    }
  }
</script>

<style>
.hidden_header {
  display: none;
}
</style>
