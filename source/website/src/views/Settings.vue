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
                v-model="showServerError"
                variant="danger"
                dismissible
            >
              Server error. See Cloudwatch logs for API resource, /system/configuration.
            </b-alert>
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
                fixed
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
                  <b-form-input placeholder="(Click to edit)" v-model="row.item.endpoint" :state="isValidEndpoint(row.item.endpoint)" class="custom-text-field " />
                </template>
                <template #cell(data_upload_account_id)="row">
                  <b-form-input placeholder="(Click to edit)" v-model="row.item.data_upload_account_id" :state="isValidAccountId(row.item.data_upload_account_id)" class="custom-text-field " />
                </template>
                <template #cell(tags)="row">
                  <b-row no-gutters>
                    <b-col cols="10">
                      <voerro-tags-input element-id="tags"
                        v-model="row.item.tags"
                        :add-tags-on-space="true"
                        :add-tags-on-comma="true"
                        :add-tags-on-blur="true"
                        :typeahead="false"
                        placeholder="(Click to edit)">
                      </voerro-tags-input>
                    </b-col>
                    <b-col cols="1" align="right">
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
                  <b-button id="save_button" type="submit" variant="primary" class="mb-2" @click="onSubmit" :disabled="!isValidForm">
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
  import VoerroTagsInput from '@/components/VoerroTagsInput.vue';
  import '@/components/VoerroTagsInput.css'

  export default {
    name: "Settings",
    components: {
      Header, Sidebar, VoerroTagsInput
    },
    data() {
      return {
        importFilename: null,
        showImportSuccess: false,
        showServerError: false,
        showImportError: false,
        dismissSecs: 5,
        showSuccessCountDown: 0,
        isBusy: false,
        amcInstances: [{"endpoint": "","data_upload_account_id": "", "tags": []}],
        fields: [
          {key: 'endpoint', label: 'AMC Endpoint', sortable: true, thStyle: { width: '50%'}},
          {key: 'data_upload_account_id', label: 'Data Upload Account Id', sortable: true},
          {key: 'tags', label: 'Tags', sortable: false}
        ],
        isSettingsActive: true
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
    computed: {
      isValidForm() {
        return this.amcInstances.length > 0 && this.amcInstances.every(x => this.isValidEndpoint(x.endpoint) !== false && this.isValidAccountId(x.data_upload_account_id) !== false)
      }
    },
    mounted: function() {
      this.read_system_configuration('GET', 'system/configuration')
    },
    methods: {
      isValidEndpoint(x) {
        // This function is used enable an error icon in a form input field.
        // If valid we return null instead of true because we don't want to
        // show the green check mark icon.
        if (!x) return false
        if (x.match('https://.+.execute-api..+.amazonaws.com/prod') != null) return null
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
        this.amcInstances.splice(index, 1)
        // Prevent the table from being empty if a user delete a row when there is only one row.
        if (this.amcInstances.length === 0) {
          this.amcInstances = [{"endpoint": "","data_upload_account_id": "", "tags": []}]
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
            if (Array.isArray(contents) && contents.length > 0 && Object.keys(contents[0]).includes("endpoint") && Object.keys(contents[0]).includes("data_upload_account_id")) {
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
        this.read_system_configuration('GET', 'system/configuration')
      },
      onSubmit() {
        this.save_system_configuration('POST', 'system/configuration', {"Name": "AmcInstances", "Value": this.amcInstances})
      },
      async save_system_configuration(method, resource, data) {
        this.showServerError = false
        const amc_instances = data["Value"]
        for (let amc_instance of amc_instances) {
          if ('tags' in amc_instance && amc_instance.tags.length > 0) {
            amc_instance.tag_list = Object.values(amc_instance.tags).map(x => x.value).toString().replace(',', ', ')
          }
        }
        console.log("sending " + method + " " + resource + " " + JSON.stringify(data))
        const apiName = 'amcufa-api'
        this.isBusy = true;
        try {
          if (method === "POST") {
            let requestOpts = {
              headers: {'Content-Type': 'application/json'},
              body: data
            };
            await this.$Amplify.API.post(apiName, resource, requestOpts);
          }
        }
        catch (e) {
          this.showServerError = true;
          console.log(e)
        } finally {
          this.isBusy = false;
        }
      },
      async read_system_configuration(method, resource) {
        this.showServerError = false
        console.log("sending " + method + " " + resource)
        const apiName = 'amcufa-api'
        let response = ""
        this.isBusy = true;
        try {
          if (method === "GET") {
            response = await this.$Amplify.API.get(apiName, resource);
          }
          if (response.length > 0 && "Value" in response[0]) {
            this.amcInstances = response[0]["Value"]
            console.log(JSON.stringify(this.amcInstances))
          }
        }
        catch (e) {
          console.log(e)
          this.showServerError = true
        } finally {
          this.isBusy = false;
        }
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
  .tags-input-wrapper-default {
    border: 0
  }
  .tags-input-wrapper-default {
    padding: 0em 0em;
  }
</style>
