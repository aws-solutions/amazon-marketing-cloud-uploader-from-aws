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
            <b-modal id="modal-amc-endpoint" title="AMC Endpoints" ok-only>
              AMC endpoint URLs must reside in <b>{{ AWS_REGION }}</b> and match the following regex pattern:
              <br>
              <br>
              <code>https://.*.execute-api.{{ AWS_REGION }}.amazonaws.com/prod</code>
            </b-modal>
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
            <b-alert
              :show="amcInstances.length > 259"
              variant="danger"
            >
              AMC instance list is too long. Length {{ amcInstances.length }} exceeds maximum allowable limit of 259.
            </b-alert>
            <b-row>
              <b-col cols="10">
                <h3>AMC Instances</h3>
                Specify the connection properties for each AMC instance that needs to interface with this solution.
              </b-col>
            </b-row>
            <br>
            <div>
              <p class="text-secondary">
                Click table cells to edit values.
              </p>
              <b-table
                ref="settingsTable"
                :items="amcInstances"
                :fields="fields"
                :busy="isBusy"
                :current-page="currentPage"
                :per-page="perPage"
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
                  <b-form-input v-model="row.item.endpoint" placeholder="(Click to edit)" :state="isValidEndpoint(row.item.endpoint)" class="custom-text-field " />
                </template>
                <template #cell(data_upload_account_id)="row">
                  <b-form-input v-model="row.item.data_upload_account_id" placeholder="(Click to edit)" :state="isValidAccountId(row.item.data_upload_account_id)" class="custom-text-field " />
                </template>
                <template #cell(tags)="row">
                  <b-row no-gutters>
                    <b-col cols="10">
                      <voerro-tags-input v-model="row.item.tags"
                                         element-id="tags"
                                         :add-tags-on-space="true"
                                         :add-tags-on-comma="true"
                                         :add-tags-on-blur="true"
                                         :typeahead="false"
                                         placeholder="(Click to edit)"
                      >
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
                <template #head(endpoint)>
                  AMC Endpoint
                  <b-link v-b-modal.modal-amc-endpoint>
                    <b-icon-question-circle-fill variant="secondary"></b-icon-question-circle-fill>
                  </b-link>
                </template>
              </b-table>
              <b-pagination
                v-if="amcInstances.length > perPage"
                v-model="currentPage"
                align="center"
                :per-page="perPage"
                :total-rows="amcInstances.length"
                aria-controls="shotTable"
              ></b-pagination>
              <b-row>
                <b-col align="left">
                  <b-button id="import_button" type="button" variant="outline-secondary" class="mb-2" @click="onImport">
                    Import
                  </b-button> &nbsp;
                  <input type="file" class="form-control" id="importFile" @input="importFile" style="display:none;">
                  <b-button id="export_button" type="button" variant="outline-secondary" class="mb-2" :disabled="!isValidForm" @click="onExport">
                    Export
                  </b-button>
                </b-col>
                <b-col align="right">
                  <b-button id="reset_button" type="reset" variant="outline-secondary" class="mb-2" @click="onReset">
                    Reset
                  </b-button> &nbsp;
                  <b-button id="save_button" type="submit" variant="primary" class="mb-2" :disabled="!isValidForm" @click="onSubmit">
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
        showRegionWarning: true,
        showServerError: false,
        showImportError: false,
        dismissSecs: 5,
        showSuccessCountDown: 0,
        isBusy: false,
        currentPage: 1,
        perPage: 5,
        amcInstances: [{"endpoint": "","data_upload_account_id": "", "tags": []}],
        fields: [
          {key: 'endpoint', label: 'AMC Endpoint', thStyle: { width: '50%'}},
          {key: 'data_upload_account_id', label: 'Data Upload Account Id'},
          {key: 'tags', label: 'Tags'}
        ],
        isSettingsActive: true
      }
    },
    computed: {
      isValidForm() {
        return this.amcInstances.length > 0 && this.amcInstances.length < 260 && this.amcInstances.every(x => this.isValidEndpoint(x.endpoint) !== false && this.isValidAccountId(x.data_upload_account_id) !== false)
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
      this.read_system_configuration('GET', 'system/configuration')
    },
    methods: {
      isValidEndpoint(x) {
        // This function is used enable an error icon in a form input field.
        if (!x) return false
        // If the endpoint is valid then we return null instead of true because
        // we don't want to show the green check mark icon.
        if (x.match('https://.+.execute-api.'+this.AWS_REGION+'.amazonaws.com/prod') != null) return null
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
      importFile(e) {
        let files = e.target.files || e.dataTransfer.files
        if (!files.length)
          return;
        this.importFilename = files[0]
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
        a.download = "amc_instances.json";
        a.href = window.URL.createObjectURL(blob);
        a.dataset.downloadurl = ['text/json', a.download, a.href].join(':');
        e.initEvent('click', true, false, window, 0, 0, 0, 0, 0, false, false, false, false, 0, null); //NOSONAR
        a.dispatchEvent(e);
      },
      onReset() {
        this.read_system_configuration('GET', 'system/configuration')
      },
      onSubmit() {
        // Reset the list of selected instances used on step 4
        this.$store.commit('updateDestinations', [])
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
        if (Array.isArray(response) && response.length > 0 && 
          typeof response[0] == "object" && "Value" in response[0]) {
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
    border: 0;
    padding: 0em 0em;
  }
</style>
