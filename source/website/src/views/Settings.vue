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
              Server error. See Cloudwatch logs for API Handler.
            </b-alert>
            <b-alert
              :show="showSuccessCountDown"
              dismissible
              fade
              variant="success"
              @dismissed="showSuccessCountDown=0"
              @dismiss-count-down="countDownChanged"
            >
              AMC Instances have been updated successfully.
            </b-alert>
            <b-alert
              :show="showLwACountDown"
              dismissible
              fade
              variant="success"
              @dismissed="showLwACountDown=0"
              @dismiss-count-down="countDownChangedLwA"
            >
              OAuth secret saved. Initiating LwA authorization in {{ showLwACountDown }} seconds.
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
            <b-alert
              :show="showOauthValidationError"
              variant="danger"
            >
              Invalid credentials. Try again.
            </b-alert>
            <b-row>
              <b-col>
              <h3>Authentication</h3>
              </b-col>
              </b-row>
            <b-row>
              <b-col cols="10">
                Setup your Login with Amazon OAuth credentials. Need help? <b-link href="https://advertising.amazon.com/API/docs/en-us/guides/onboarding/overview">Learn more</b-link>.
              </b-col>
              <b-col v-if="!isBusyOauth && !showOauthValidationError">
                <b-badge variant="success" v-if="isOauthSaved">Credentials Saved</b-badge>
                <b-badge variant="danger" v-else>Credentials Unsaved</b-badge>
              </b-col>
            </b-row>
            <br>
            <b-row>
              <b-col sm="9">
                <b-table-simple
                    ref="oAuthTable"
                    responsive="sm"
                    small
                    borderless
                    style="margin-bottom: 0"
                >
                  <b-tbody>
                    <div class="text-center text-secondary my-2" v-if="isBusyOauth">
                      <b-spinner class="align-middle"></b-spinner>
                      <strong>&nbsp;&nbsp;Loading...</strong>
                    </div>
                    <b-tr v-else>
                      <b-td>
                        <b-form-group
                            id="clientId-label"
                            label-cols-lg="2"
                            label-align-lg="left"
                            label="Client ID:"
                            label-for="clientId-input"
                        >
                          <b-form-input
                              id="clientId-input"
                              v-model="client_id"
                              :state="showOauthValidationError ? isValidClientId : null"
                          >
                          </b-form-input>
                        </b-form-group>
                        <b-form-group
                            id="clientSecret-label"
                            label-cols-lg="2"
                            label-align-lg="left"
                            label="Client Secret:"
                            label-for="clientSecret-input"
                        >
                          <b-form-input
                              id="clientSecret-input"
                              v-model="client_secret"
                              type="password"
                              :state="showOauthValidationError ? isValidClientSecret : null"
                          >
                          </b-form-input>
                        </b-form-group>
                      </b-td>
                    </b-tr>
                  </b-tbody>
                </b-table-simple>
              </b-col>
            </b-row>

            <b-row>
              <b-col align="left">
                <b-button id="import_client_button" type="button" variant="outline-secondary" class="mb-2" @click="onImportOauthCredentialsFile">
                  Import
                </b-button> &nbsp;
                <input type="file" class="form-control" id="importOauthCredentialsFile" @input="importOauthCredentialsFile" style="display:none;">
                <b-button id="export_client_button" type="button" variant="outline-secondary" :disabled="!client_id || !client_secret" class="mb-2" @click="onExportOauthCredentials">
                  Export
                </b-button>
              </b-col>
              <b-col align="right">
                <b-button id="reset_oauth_button" type="reset" variant="outline-secondary" class="mb-2" @click="onResetOauth">
                  Reset
                </b-button> &nbsp;
                <b-button id="save_oauth_button" type="submit" variant="primary" class="mb-2" :disabled="!client_id || !client_secret" @click="onSubmitOauthCredentials">
                  {{ oAuthSaveButtonLabel }}
                </b-button>
              </b-col>
            </b-row>
            <br>
            <b-row>
              <b-col cols="10">
                <h3>AMC Instances</h3>
                Specify the connection properties for each AMC instance that needs to interface with this solution.
              </b-col>
            </b-row>
            <br>
              <b-table
                ref="settingsTable"
                :items="amcInstances"
                :fields="amcInstanceAttributes"
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
                <template #cell(data_upload_account_id)="row">
                  <b-form-input v-model="row.item.data_upload_account_id" placeholder="(Click to edit)" :state="isValidAccountId(row.item.data_upload_account_id)" class="custom-text-field " />
                </template>
                <template #cell(instance_id)="row">
                  <b-form-input v-model="row.item.instance_id" placeholder="(Click to edit)" :state="!isEmpty(row.item.instance_id)" class="custom-text-field " />
                </template>
                <template #cell(advertiser_id)="row">
                  <b-form-input v-model="row.item.advertiser_id" placeholder="(Click to edit)" :state="!isEmpty(row.item.advertiser_id)" class="custom-text-field " />
                </template>
                <template #cell(marketplace_id)="row">
                  <b-form-input v-model="row.item.marketplace_id" placeholder="(Click to edit)" :state="!isEmpty(row.item.marketplace_id)" class="custom-text-field " />
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
                <template #head(instance_id)>
                  AMC Instance Id
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
          </b-col>
        </b-row>
      </b-container>
    </div>
  </div>
</template>

<script>
  import Header from '@/components/Header.vue';
  import Sidebar from '@/components/Sidebar.vue';
  import '@/components/VoerroTagsInput.css';
  import VoerroTagsInput from '@/components/VoerroTagsInput.vue';
  import { API } from 'aws-amplify';

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
        showLwACountDown: 0,
        showSuccessCountDown: 0,
        isBusy: false,
        isBusyOauth: false,
        currentPage: 1,
        perPage: 5,
        amcInstances: [this.defaultAmcInstances()],
        amcInstanceAttributes: [
          {key: 'instance_id', label: 'AMC Instance ID'},
          {key: 'advertiser_id', label: 'Amazon Ads Advertiser Entity ID'},
          {key: 'marketplace_id', label: 'Amazon Ads Marketplace ID'},
          {key: 'data_upload_account_id', label: 'Data Upload Account ID'},
          {key: 'tags', label: 'Tags'},
        ],
        isSettingsActive: true,
        client_id: '',
        client_secret: '',
        isClientIdSaved: false,
        isClientSecretSaved: false,
        oAuthCredentialsFilename: null,
        userId: null,
        isEnv: false,
        showOauthValidationError: false
      }
    },
    computed: {
      oAuthSaveButtonLabel() {
        if (this.isClientIdSaved && this.isClientSecretSaved)
          return "Overwrite"
        else
          return "Save"
      },
      isOauthSaved() {
        return this.isClientIdSaved && this.isClientSecretSaved
      },
      isValidForm() {
        return this.isValidAmcInstances()
      },
      isValidClientId() {
        const regex = /^[a-zA-Z0-9\-\.]+$/;
        return regex.test(this.client_id);
      },
      isValidClientSecret() {
        // This function returns null when client_id is blank so that
        // the text field does not prematurely show a pass/fail icon when it is empty.
        const regex = /^[a-zA-Z0-9\-\.]+$/;
        return regex.test(this.client_secret);
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
      this.userId = this.USER_POOL_ID
      this.read_system_configuration()
      this.describe_secret()
    },
    methods: {
      defaultAmcInstances(){
        return {"instance_id": "", "advertiser_id": "", "marketplace_id": "", "data_upload_account_id": "", "tags": []}
      },
      isValidAccountId(account_id) {
        return (account_id !== undefined && account_id.match('^[0-9]{12}$') != null)
      },
      isValidAmcInstances(){
        let result = true
        for (let i = 0; i < this.amcInstances.length; i++) {
          if (
              this.isValidAccountId(this.amcInstances[i].data_upload_account_id) === false ||
              this.isEmpty(this.amcInstances[i].instance_id) ||
              this.isEmpty(this.amcInstances[i].advertiser_id) ||
              this.isEmpty(this.amcInstances[i].marketplace_id)
          ) {
            result = false;
            break;
          }
        }
        result = result && (this.amcInstances.length > 0 && this.amcInstances.length < 260);
        return result
      },
      isEmpty(obj){
        return (!obj || obj.length === 0)
      },
      countDownChangedLwA(dismissCountDown) {
        this.showLwACountDown = dismissCountDown
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
          this.amcInstances = [this.defaultAmcInstances()]
        }
      },
      onImport() {
        this.importFilename = null
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
            if (
                Array.isArray(contents) && contents.length > 0 &&
                Object.keys(contents[0]).includes("instance_id") &&
                Object.keys(contents[0]).includes("advertiser_id") &&
                Object.keys(contents[0]).includes("marketplace_id")
              ) {
              vm.amcInstances = contents
              vm.dismissCountDown = vm.dismissSecs
            } else {
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
      onImportOauthCredentialsFile() {
        this.oAuthCredentialsFilename = null
        // dismiss error alert
        this.showImportError = false
        document.getElementById('importOauthCredentialsFile').click()
      },
      importOauthCredentialsFile(e) {
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
            if (Object.keys(contents).length > 0 && Object.keys(contents).includes("client_id") && Object.keys(contents).includes("client_secret")) {
              vm.client_id = contents["client_id"]
              vm.client_secret = contents["client_secret"]
              vm.dismissCountDown = vm.dismissSecs
            } else {
              vm.showImportError = true
            }
          } catch (error) {
            console.log(error)
            vm.showImportError = true
          }
        };
        reader.readAsText(this.importFilename);
      },
      onExportOauthCredentials() {
        const table_data = JSON.stringify({"client_id": this.client_id, "client_secret": this.client_secret});
        const blob = new Blob([table_data], {type: 'text/plain'});
        const e = document.createEvent('MouseEvents'),
            a = document.createElement('a');
        a.download = "lwa_oauth_credentials.json";
        a.href = window.URL.createObjectURL(blob);
        a.dataset.downloadurl = ['text/json', a.download, a.href].join(':');
        e.initEvent('click', true, false, window, 0, 0, 0, 0, 0, false, false, false, false, 0, null); //NOSONAR
        a.dispatchEvent(e);
      },
      onResetOauth() {
        this.client_id=''
        this.client_secret=''
        this.describe_secret()
      },
      onReset() {
        this.read_system_configuration()
      },
      onSubmit() {
        // Reset the list of selected instances used on step 4
        this.$store.commit('updateSelectedAmcInstances', [])
        this.save_system_configuration({"Name": "AmcInstances", "Value": this.amcInstances})
      },
      onSubmitOauthCredentials() {
        this.showOauthValidationError = false
        if (this.isValidClientId && this.isValidClientSecret)
          this.send_save_secret_request()
        else {
          this.showOauthValidationError = true
        }
      },
      delay(time) {
        return new Promise(resolve => setTimeout(resolve, time));
      },
      async send_save_secret_request() {
        const method = "POST"
        const resource = "save_secret"
        const data = {"client_id": this.client_id, "client_secret": this.client_secret, "user_id": this.userId}
        this.showLwACountDown = 0
        this.showServerError = false
        console.log("sending " + method + " " + resource)
        const apiName = 'amcufa-api'
        this.isBusyOauth = true;
        try {
          let requestOpts = {
            headers: {'Content-Type': 'application/json'},
            body: data
          };
          await API.post(apiName, resource, requestOpts);
          // Erase OAuth form to protect sensitive information
          this.client_id = ''
          this.client_secret = ''
          // Show the "Credentials Saved" badge
          this.isClientIdSaved = true
          this.isClientSecretSaved = true
          // Stop the spinner
          this.isBusyOauth = false;
          // Pause for 5 seconds before jumping to LwA authorization
          this.showLwACountDown = 5
          const timeout = this.showLwACountDown * 1000
          await this.delay(timeout)
          // Begin LwA authorization
          await this.get_amc_instances()
        }
        catch (e) {
          this.showServerError = true;
          console.log(e)
        } finally {
          this.isBusyOauth = false;
        }
      },
      async save_system_configuration(data) {
        const method = "POST"
        const resource = "system/configuration"
        this.showSuccessCountDown = 0
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
            let requestOpts = {
              headers: {'Content-Type': 'application/json'},
              body: data
            };
            await API.post(apiName, resource, requestOpts);
            this.showSuccessCountDown = 5
        }
        catch (e) {
          this.showServerError = true;
          console.log(e)
        } finally {
          this.isBusy = false;
        }
      },
      async describe_secret() {
        this.isBusyOauth = true;
        const method = 'POST'
        const apiName = 'amcufa-api'
        const data = {
          "user_id": this.userId
        }
        const resource = 'describe_secret'
        try {
          console.log("sending " + method + " " + resource + " " + JSON.stringify(data))
          let requestOpts = {
            headers: {'Content-Type': 'application/json'},
            body: data
          };
          const response = await API.post(apiName, resource, requestOpts);
          if (response === null || response.Status === "Error") {
            this.showServerError = true
          }
          const secret_string_keys = response["secret_string_keys"]
          if (secret_string_keys.includes("client_id"))
            this.isClientIdSaved = true
          if (secret_string_keys.includes("client_secret"))
            this.isClientSecretSaved = true
        } catch (e) {
          console.log("ERROR: " + e.response.data.message)
          this.response = e.response.data.message
          this.showServerError = true
          this.serverErrorMessage = e.response.data.message
        } finally {
          this.isBusyOauth = false;
        }
      },
      async read_system_configuration() {
        this.showServerError = false
        const method = "GET"
        const resource = "system/configuration"
        console.log("sending " + method + " " + resource)
        const apiName = 'amcufa-api'
        let response = ""
        this.isBusy = true;
        try {
          if (method === "GET") {
            response = await API.get(apiName, resource);
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
      },
      async get_amc_instances() {
        const apiName = 'amcufa-api'
        const method = 'POST'
        const data = {
          "user_id": this.userId
        }
        const resource = 'get_amc_instances'
        try {
          console.log("sending " + method + " " + resource + " " + JSON.stringify(data))
          let requestOpts = {
            headers: {'Content-Type': 'application/json'},
            body: data
          };
          const response = await API.post(apiName, resource, requestOpts);
          if (response === null || response.Status === "Error") {
            this.showServerError = true
          } else if (response.authorize_url){
            const current_page = "settings"
            const state_key = current_page + this.userId + Date.now()
            const b64_state_key = btoa(current_page + this.userId + Date.now())
            let state_vars = {
              "current_page": current_page
            }
            localStorage.setItem(state_key, JSON.stringify(state_vars))
            window.location.href = response.authorize_url + "&state=" + b64_state_key
          }
        } catch (e) {
          console.log("ERROR: " + e.response.data.message)
          this.response = e.response.data.message
          this.showServerError = true
          this.serverErrorMessage = e.response.data.message
          this.isBusyOauth = false
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
