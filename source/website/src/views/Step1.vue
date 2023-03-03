<!--
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
-->

<template>
  <div>
    <div class="headerTextBackground">
      <Header />
      <b-container fluid>
        <b-modal id="modal-file-format" title="File Format Requirements">
          <p><strong>CSV</strong> files must include a header, be UTF-8 encoded, and comma delimited.</p>
          <p><strong>JSON</strong> files must contain one object per row of data. Each row must be a top-level object. No parent object or array may be present in the JSON file. An example of the accepted JSON format is shown below:</p>
          <pre>
{"name": "Product A", "sku": 11352987, "quantity": 2, "pur_time": "2021-06-23T19:53:58Z"}
{"name": "Product B", "sku": 18467234, "quantity": 2, "pur_time": "2021-06-24T19:53:58Z"}
{"name": "Product C", "sku": 27264393, "quantity": 2, "pur_time": "2021-06-25T19:53:58Z"}
{"name": "Product A", "sku": 48572094, "quantity": 2, "pur_time": "2021-06-25T19:53:58Z"}
{"name": "Product B", "sku": 18278476, "quantity": 1, "pur_time": "2021-06-26T13:33:58Z"}
            </pre>
        </b-modal>
        <b-row style="text-align: left">
          <b-col cols="2">
            <Sidebar :is-step1-active="true" />
          </b-col>
          <b-col cols="10">
            <h3>Select files</h3>
            Select one or more files to ingest. Files must be formatted as CSV or JSON with identical schemas.
            <b-link v-b-modal.modal-file-format>
              <b-icon-question-circle-fill variant="secondary"></b-icon-question-circle-fill>
            </b-link>
            <br>
            <br>
            <div>
              <b-row align-v="end">
                <b-col sm="9" align="left">
                  <b-form-group
                    id="bucket-label"
                    label-cols-lg="2"
                    label-align-lg="left"
                    label="Bucket: "
                    label-for="bucket"
                  >
                    <b-form-input id="bucket-input" plaintext :placeholder="DATA_BUCKET_NAME"></b-form-input>
                  </b-form-group>
                  <b-form-group
                    id="s3key-label"
                    label-cols-lg="2"
                    label-align-lg="left"
                    label="Keys:"
                    label-for="s3key-input"
                  >
                    <b-form-input id="s3key-input" v-model="new_s3key"></b-form-input>
                  </b-form-group>
                </b-col>
                <b-col sm="2" align="right">
                  <button type="submit" class="btn btn-primary mb-2" :disabled="!new_s3key" @click="onSubmit">
                    Next
                  </button>
                  <br>
                  <br>
                </b-col>
              </b-row>
            </div>

            <div>
              <b-table
                ref="selectableTable"
                :items="results"
                :fields="fields"
                :busy="isBusy"
                select-mode="multi"
                responsive="sm"
                selectable
                small
                @row-selected="onRowSelected"
              >
                <template #table-busy>
                  <div class="text-center my-2">
                    <b-spinner class="align-middle"></b-spinner>
                    <strong>&nbsp;&nbsp;Loading...</strong>
                  </div>
                </template>
                <template #cell(selected)="{ rowSelected }">
                  <template v-if="rowSelected">
                    <span aria-hidden="true">&check;</span>
                    <span class="sr-only">Selected</span>
                  </template>
                  <template v-else>
                    <span aria-hidden="true">&nbsp;</span>
                    <span class="sr-only">Not selected</span>
                  </template>
                </template>
              </b-table>
            </div>
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
    name: "Step1",
    components: {
      Header, Sidebar
    },
    data() {
      return {
        isBusy: false,
        fields: [
          {key: 'selected'},
          {key: 'key', sortable: true},
          {key: 'last_modified', sortable: true},
          {key: 'size', sortable: true}],
        new_s3key: '',
        isStep1Active: true,
        results: [],
      }
    },
    computed: {
      ...mapState(['s3key']),
    },
    deactivated: function () {
      console.log('deactivated');
    },
    activated: function () {
      console.log('activated')
    },
    created: function () {
      console.log('created')
      this.send_request('POST', 'list_bucket', {'s3bucket': this.DATA_BUCKET_NAME})
    },
    mounted: function() {
      this.new_s3key = this.s3key
    },
    methods: {
      onSubmit() {
        this.$store.commit('updateS3key', this.new_s3key)
        this.$store.commit('saveStep3FormInput', [])
        this.$router.push({path: '/step2'})
      },
      onRowSelected(items) {
        let newKeys = [];
        for(let item of items) newKeys.push(item.key)
        this.new_s3key = newKeys.join(", ");
      },
      async send_request(method, resource, data) {
        this.results = []
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
          this.results = response
        }
        catch (e) {
          console.log("ERROR: " + e.response.data.message)
          this.isBusy = false;
          this.results = e.response.data.message
        }
        this.isBusy = false;
      }
    }
  }
</script>
