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
            <Sidebar :is-settings-active="true" />
          </b-col>
          <b-col cols="10">
            <b-alert
                :show="showSuccessCountDown"
                dismissible
                fade
                variant="success"
                @dismissed="showSuccessCountDown=0"
                @dismiss-count-down="countDownChanged"
            >
              This alert will dismiss after {{ showSuccessCountDown }} seconds...
            </b-alert>
            <b-alert
                :show="showImportError"
                variant="danger"
                dismissible
            >
              Import failed. Check data format.
            </b-alert>
            <b-row>
              <b-col cols="10">
                <h3>AMC Instances</h3>
                Specify the connection properties for each AMC instance that needs to interface with this solution.
              </b-col>
            </b-row>
            <br>
            <div>
              <p class="text-secondary">Click table cells to edit values.</p>
              <b-table
                ref="settingsTable"
                :items="amcInstances"
                :fields="fields"
                :busy="isBusy"
                responsive="sm"
                small
                selectable
                select-mode="single"
                bordered
              >
                <template #table-busy>
                  <div class="text-center my-2">
                    <b-spinner class="align-middle"></b-spinner>
                    <strong>&nbsp;&nbsp;Loading...</strong>
                  </div>
                </template>
                <template #cell(endpoint)="row">
                  <b-form-input placeholder="click to enter" v-model="row.item.endpoint" :state="isValidEndpoint(row.item.endpoint)" class="custom-text-field " />
                </template>
                <template #cell(data_upload_account_id)="row">
                  <b-row no-gutters>
                    <b-col cols="11">
                      <b-form-input placeholder="click to enter" v-model="row.item.data_upload_account_id" :state="isValidAccountId(row.item.data_upload_account_id)" class="custom-text-field" />
                    </b-col>
                    <b-col align="right">
                        <b-button v-b-tooltip.hover.right size="sm" style="display: flex;" variant="link" title="Remove row" @click="delete_row(row.index)">
                          <b-icon-x-circle variant="secondary"></b-icon-x-circle>
                        </b-button>
                        <b-button v-b-tooltip.hover.right size="sm" style="display: flex;" variant="link" title="Add row" @click="add_row(row.index)">
                          <b-icon-plus-square variant="secondary"></b-icon-plus-square>
                        </b-button>
                    </b-col>
                  </b-row>
                </template>
              </b-table>
              <b-row>
                <b-col align="left">
                  <b-button id="import_button" type="button" variant="outline-secondary" class="mb-2" @click="onImport">
                    Import
                  </b-button> &nbsp;
                  <b-form-file style="display:none;" v-model="importFilename" id="importFile" accept="application/json" @input="importFile"></b-form-file>
                  <b-button id="export_button" type="button" variant="outline-secondary" class="mb-2" @click="onExport">
                    Export
                  </b-button>
                </b-col>
                <b-col align="right">
                  <b-button id="reset_button" type="reset" variant="outline-secondary" class="mb-2" @click="onReset">
                    Reset
                  </b-button> &nbsp;
                  <b-button id="save_button" type="submit" class="mb-2" @click="onSubmit" :disabled="amcInstances.length == 0">
                    Save
                  </b-button>
                </b-col>
              </b-row>
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
    name: "Settings",
    components: {
      Header, Sidebar
    },
    data() {
      return {
        importFilename: null,
        showImportSuccess: false,
        showImportError: false,
        dismissSecs: 5,
        showSuccessCountDown: 0,
        isBusy: false,
        amcInstances: [],
        fields: [
          {key: 'endpoint', label: 'AMC Endpoint', sortable: true},
          {key: 'data_upload_account_id', label: 'Data Upload Account Id', sortable: true}
        ],
        isSettingsActive: true,
        results: [],
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
      // this.send_request('POST', 'save_settings', {'amcInstances': this.amcInstances})
    },
    mounted: function() {
    },
    methods: {
      isValidEndpoint(x) {
        // This function is used enable an error icon in a form input field.
        // If valid we return null instead of true because we don't want to
        // show the green check mark icon.
        if (!x) return false
        if (x.match('https://.+\.execute-api\..+\.amazonaws\.com/prod') != null) return null
        else return false
      },
      isValidAccountId(x) {
        // This function is used enable an error icon in a form input field.
        // If valid we return null instead of true because we don't want to
        // show the green check mark icon.
        if (!x) return false
        if (x.match('^[0-9]{12}$') != null) return null
        else return false
      },
      countDownChanged(dismissCountDown) {
        this.showSuccessCountDown = dismissCountDown
      },
      add_row(index) {
        if (index < this.amcInstances.length) {
          this.amcInstances.splice(index+1, 0, {})
        } else {
          this.amcInstances.splice(index-this.amcInstances.length, 0, {})      
        }
      },
      delete_row(index) {
        if (this.amcInstances.length === 0){
          this.amcInstances = [{"endpoint":"","data_upload_account_id":""}]
        } else {
          this.amcInstances.splice(index, 1)
        }
        
      },
      onImport() {
        this.importFilename = null
        // dismiss success alert
        this.showSuccessCountDown = 0
        // dismiss error alert
        this.showImportError = false
        document.getElementById('importFile').click()
      },
      importFile() {
        if (!this.importFilename) {
          return;
        }
        const reader = new FileReader();
        const vm = this;
        reader.onload = function(e) {
          try {
            const contents = JSON.parse(e.target.result);
            // validate contents
            if (Array.isArray(contents) && contents.length > 0 && Object.keys(contents[0]).toString() === "endpoint,data_upload_account_id") {
              vm.amcInstances = contents
              vm.dismissCountDown = vm.dismissSecs
            } else {
              console.log("Invalid data:")
              console.log(contents);
              vm.showImportError = true
            }
          } catch (error) {
            console.log(error)
            vm.showImportError = true
          }
        };
        reader.readAsText(this.importFilename);
      },
      onExport() {
        const table_data = JSON.stringify(this.amcInstances);
        const blob = new Blob([table_data], {type: 'text/plain'});
        const e = document.createEvent('MouseEvents'),
            a = document.createElement('a');
        a.download = "data.json";
        a.href = window.URL.createObjectURL(blob);
        a.dataset.downloadurl = ['text/json', a.download, a.href].join(':');
        e.initEvent('click', true, false, window, 0, 0, 0, 0, 0, false, false, false, false, 0, null);
        a.dispatchEvent(e);
      },
      onReset() {
        this.amcInstances = []
      },
      onSubmit() {
        this.send_request('POST', '/system/configuration', {"Name": "AmcInstances", "Value": this.amcInstances})
      },
      async send_request(method, resource, data) {
        this.results = []
        console.log("sending " + method + " " + resource + " " + JSON.stringify(data))
        const apiName = 'amcufa-api'
        let response = ""

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

<style>
  .custom-text-field {
    background-color: white !important;
    border: 0;
    padding-left: 0px !important;
    padding-right: 0px !important;
    margin-top: 0px !important;
    margin-bottom: 0px !important;
  }
</style>
