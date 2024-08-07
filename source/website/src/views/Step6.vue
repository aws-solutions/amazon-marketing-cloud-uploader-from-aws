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
            <Sidebar :is-step6-active="true" />
          </b-col>
          <b-col cols="10">
            <b-alert
              v-model="showServerError"
              variant="danger"
              dismissible
            >
              Server error. Failed to get AMC instance list. See Cloudwatch logs for API resource, /system/configuration.
            </b-alert>
            <b-modal id="modal-upload-error" title="Upload Error" ok-only>
              AMC returned the following error when attempting to upload <b>{{ selected_dataset }}</b>:
              <br>
              <br>
              <code>{{ upload_failure }}</code>
            </b-modal>
            <!-- User Interface controls -->
            <b-card no-body class="mb-1" border-variant="secondary" bg-variant="light">
              <b-card-header header-tag="header" class="p-2" role="tab">
                <b-row>
                  <b-col>
                    <h5 class="mb-0">
                      AMC Endpoint Selector
                    </h5>
                  </b-col>
                  <b-col align="right">
                    <b-button v-b-toggle:amc-selector @click="changeAmcSelectorVisibility">
                      <span class="when-open">Hide</span><span class="when-closed">Show</span>
                    </b-button>
                  </b-col>
                </b-row>
              </b-card-header>
              <b-collapse id="amc-selector" v-model="amc_selector_visible">
                <b-card-body>
                  <p class="text-secondary">
                    Click a row in the table to select an AMC endpoint.
                  </p>

                  <b-row>
                    <b-col lg="6" class="my-1">
                      <b-form-group
                        label="Filter"
                        label-for="filter-input"
                        label-cols-sm="3"
                        label-align-sm="right"
                        label-size="sm"
                        class="mb-0"
                      >
                        <b-input-group size="sm">
                          <b-form-input
                            id="filter-input"
                            v-model="filter"
                            type="search"
                            placeholder="Type to Search"
                          ></b-form-input>
                          <b-input-group-append>
                            <b-button :disabled="!filter" @click="filter = ''">
                              Clear
                            </b-button>
                          </b-input-group-append>
                        </b-input-group>
                      </b-form-group>
                    </b-col>
                    <b-col lg="6" class="my-1">
                      <b-form-group
                        v-slot="{ ariaDescribedby }"
                        label="Filter On"
                        description="Leave all unchecked to filter on all data"
                        label-cols-sm="3"
                        label-align-sm="right"
                        label-size="sm"
                        class="mb-0"
                      >
                        <b-form-checkbox-group
                          v-model="filterOn"
                          :aria-describedby="ariaDescribedby"
                          class="mt-1"
                        >
                          <b-form-checkbox value="instance_id">
                            Instance ID
                          </b-form-checkbox>
                          <b-form-checkbox value="tag_list">
                            Tags
                          </b-form-checkbox>
                        </b-form-checkbox-group>
                      </b-form-group>
                    </b-col>
                  </b-row>
                  <b-table
                    :items="formattedItems"
                    :fields="available_amc_instances_fields"
                    :current-page="currentPageAmcInstances"
                    :per-page="perPageAmcInstances"
                    :filter="filter"
                    :filter-included-fields="filterOn"
                    :busy="isBusy4"
                    show-empty
                    small
                    @filtered="onFiltered"
                  >
                    <template #table-busy>
                      <div class="text-center my-2">
                        <b-spinner class="align-middle"></b-spinner>
                        <strong>&nbsp;&nbsp;Loading...</strong>
                      </div>
                    </template>
                    <template #cell(actions)="row">
                      <b-button v-if="selected_instance_id !== row.item.instance_id" size="sm" class="mr-1" @click="selectEndpoint(row.item)">
                        Select
                      </b-button>
                      <b-button v-if="selected_instance_id === row.item.instance_id" size="sm" class="mr-1" @click="unselectEndpoint()">
                        Unselect
                      </b-button>
                    </template>
                  </b-table>
                  <b-pagination
                    v-if="available_amc_instances.length > perPageAmcInstances"
                    v-model="currentPageAmcInstances"
                    align="center"
                    :per-page="perPageAmcInstances"
                    :total-rows="available_amc_instances.length"
                    aria-controls="shotTable"
                  ></b-pagination>
                </b-card-body>
              </b-collapse>
            </b-card>
            <div v-if="selected_instance_id === '' && isBusy4 === false">
              <p class="text-danger">
                Choose an AMC endpoint from the table shown above.
              </p>
            </div>
            <div v-else>
              <hr>
              <b-row>
                <b-col cols="10">
                  <h3>Datasets</h3>
                  <p v-if="!showAmcApiError" class="text-secondary">
                    Showing datasets from AMC Instance ID <em>{{ selected_instance_id === '' ? "none" : selected_instance_id }}</em>
                  </p>
                </b-col>
                <b-col align="right">
                  <b-button @click="list_datasets()">
                    Refresh
                  </b-button>
                </b-col>
              </b-row>
              <div v-if="showAmcApiError">
                <p class="text-danger" v-if="amcErrorMessage">
                    ERROR. {{ amcErrorMessage }}
                </p>
                <p class="text-danger" v-else>
                    Error listing datasets from AMC Instance ID <em>{{ selected_instance_id }}</em>
                </p>
              </div>
              <div v-else>
                <b-table
                  ref="datasetTable"
                  select-mode="single"
                  selectable
                  responsive="sm"
                  small
                  :fields="dataset_fields"
                  :items="datasets"
                  :busy="isBusy1"
                  :per-page="perPage1"
                  :current-page="currentPage1"
                  show-empty
                  @row-selected="onDatasetSelected"
                >
                  <template #empty="scope">
                    {{ scope.emptyText }}
                  </template>
                  <template #cell(Actions)="data">
                    <b-link
                      class="text-danger"
                      @click="deleteDataset(`${data.item.dataSetId}`)"
                    >
                      Delete
                    </b-link>
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
                  <template #table-busy>
                    <div class="text-center my-2">
                      <b-spinner class="align-middle"></b-spinner>
                      <strong>&nbsp;&nbsp;Loading...</strong>
                    </div>
                  </template>
                </b-table>
                <b-pagination
                  v-if="datasets.length > perPage1"
                  v-model="currentPage1"
                  align="center"
                  :per-page="perPage1"
                  :total-rows="rows1"
                  aria-controls="shotTable"
                ></b-pagination>
                <br>
              </div>
              <b-row v-if="!showAmcApiError">
                <b-col>
                  <h3>Uploads</h3>
                  <div v-if="selected_dataset">
                    <p class="text-secondary">
                      Showing uploads for <em>{{ selected_dataset }}</em>&nbsp;
                      <b-link v-if="upload_failure!==''" v-b-modal.modal-upload-error class="text-danger">
                        <b-icon-exclamation-triangle-fill variant="danger"></b-icon-exclamation-triangle-fill>
                      </b-link>
                    </p>
                  </div>
                  <div v-else>
                    <p class="text-danger">
                      Please select a dataset from the table above.
                    </p>
                  </div>
                </b-col>
                <b-col v-if="selected_dataset" align="right">
                  <b-button @click="listDatasetUploads(`${selected_dataset}`)">
                    Refresh
                  </b-button>
                </b-col>
              </b-row>
              <div v-if="selected_dataset">
                <b-table
                  :items="uploads"
                  :fields="upload_fields"
                  :busy="isBusy3 || isBusy5"
                  :per-page="perPage2"
                  :current-page="currentPage2"
                  show-empty
                  small
                  responsive="sm"
                >
                  <template #empty>
                    This dataset has not been uploaded.
                    <b-link v-if="upload_failure!==''" v-b-modal.modal-upload-error class="text-danger">
                      (Show upload error)
                    </b-link>
                  </template>
                  <template #table-busy>
                    <div class="text-center my-2">
                      <b-spinner class="align-middle"></b-spinner>
                      <strong>&nbsp;&nbsp;Loading...</strong>
                    </div>
                  </template>
                  <template #cell(sourceFileS3Key)="row">
                    <!-- This returns values from any of the supported dataSource types -->
                    {{ (row.item.dataSource.sourceFileS3Key || row.item.dataSource.sourceS3Prefix || row.item.dataSource.sourceManifestS3Key || row.item.dataSource.sourceS3Bucket).split('/').slice(-1)[0] }}
                  </template>
                  <template #cell(show_details)="row">
                    <b-form-checkbox @change="row.toggleDetails">
                    </b-form-checkbox>
                  </template>
                  <template #row-details="data">
                    <b-card>
                      <b-row v-for="(item, key) in data.item" :key="key" class="mb-2">
                        <b-col sm="3" class="text-sm-right">
                          <strong>{{ key }}:</strong>
                        </b-col>
                        <b-col>
                          {{ item }}
                        </b-col>
                      </b-row>
                    </b-card>
                  </template>
                </b-table>
                <b-pagination
                  v-if="uploads.length > perPage2"
                  v-model="currentPage2"
                  align="center"
                  :per-page="perPage2"
                  :total-rows="rows2"
                  aria-controls="shotTable"
                ></b-pagination>
              </div>
              <br>
              <b-row>
                <b-col>
                  <h3>AWS Glue Jobs</h3>
                  <p class="text-secondary">
                    Data transformation history.
                  </p>
                </b-col>
                <b-col align="right">
                  <b-button @click="get_etl_jobs()">
                    Refresh
                  </b-button>
                </b-col>
              </b-row>
              <b-table
                small
                responsive="sm"
                :fields="etl_fields"
                :items="etl_jobs"
                :busy="isBusy2"
                :per-page="perPage3"
                :current-page="currentPage3"
                sort-by="StartedOn"
                :sort-desc="false"
                :sort-compare="datetimeSortCompare"
                show-empty
              >
                <template #cell(id)="data">
                  ...{{ data.item.Id.substr(-8) }}
                </template>
                <template #cell(JobRunState)="data">
                  {{ data.item.JobRunState }}
                </template>
                <template #cell(show_details)="row">
                  <b-form-checkbox @change="row.toggleDetails">
                  </b-form-checkbox>
                </template>
                <template #row-details="data">
                  <b-card>
                    <b-row v-for="(item, key) in data.item" :key="key" class="mb-2">
                      <b-col sm="3" class="text-sm-right">
                        <strong>{{ key }}:</strong>
                      </b-col>
                      <b-col>
                        {{ item }}
                      </b-col>
                    </b-row>
                  </b-card>
                </template>
                <template #empty>
                  No ETL jobs have started yet.
                </template>
                <template #table-busy>
                  <div class="text-center my-2">
                    <b-spinner class="align-middle"></b-spinner>
                    <strong>&nbsp;&nbsp;Loading...</strong>
                  </div>
                </template>
              </b-table>
              <b-pagination
                v-if="etl_jobs.length > perPage3"
                v-model="currentPage3"
                align="center"
                :per-page="perPage3"
                :total-rows="rows3"
                aria-controls="shotTable"
              ></b-pagination>
              <br>
            </div>
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
import { mapState } from "vuex";

  export default {
    name: "Step6",
    components: {
      Header, Sidebar
    },
    data() {
      return {
        amc_selector_visible: true,
        available_amc_instances: [{"tags": [], "instance_id": "", "advertiser_id": "", "marketplace_id": "", "data_upload_account_id": ""}],
        filtered_amc_instances: [],
        available_amc_instances_fields: [
          {key: 'actions', label: 'Actions' },
          {key: 'instance_id', label: 'Instance ID'},
          {key: 'advertiser_id', label: 'Advertiser ID'},
          {key: 'marketplace_id', label: 'MarketPlace ID'},
          {key: 'tag_list', label: 'Tags', sortable: false}
        ],
        totalRows: 1,
        currentPage: 1,
        perPage: 5,
        pageOptions: [5, 10, 15, { value: 100, text: "Show a lot" }],
        filter: null,
        filterOn: [],
        currentPage2: 1,
        perPage2: 5,
        currentPage3: 1,
        perPage3: 5,
        currentPage1: 1,
        perPage1: 5,
        currentPageAmcInstances: 1,
        perPageAmcInstances: 5,
        selected_instance_id: '',
        selected_instance: '',
        datasets: [],
        selected_dataset: '',
        dataset_fields: [
          {key: 'selected'},
          {key: 'dataSetId', sortable:true},
          {key: 'description'},
          {key: 'period', sortable:true},
          {key: 'countryCode', sortable:true},
          {key: 'Actions'}
        ],
        etl_jobs: [],
        etl_fields: [
          {key: 'DatasetId', label: 'Dataset Id', sortable: true},
          {key: 'filename', label: 'File Name', sortable: true},
          {key: 'StartedOn', label: 'Started On', sortable: true},
          {key: 'ExecutionTime', label: 'Duration', sortable: true},
          {key: 'JobRunState', label: 'JobRunState', sortable: true},
          {key: 'show_details', label: 'Show Details', sortable: true}
        ],
        uploads: [],
        upload_failure: "",
        upload_fields: [
          {key: "createdAt", label: "Created At", sortable: true},
          {key: "sourceFileS3Key", label: "Source File", sortable: true},
          {key: "countryCode", label: "Country Code", sortable: true},
          {key: "status", label: "Status", sortable: true},
          {key: "show_details", label: "Show Details"}
        ],
        isBusy1: false,
        isBusy2: false,
        isBusy3: false,
        isBusy4: false,
        isBusy5: false,
        showAmcApiError: false,
        showServerError: false,
        amcErrorMessage: '',
        isStep6Active: true,
        userId: null
      }
    },
    computed: {
      ...mapState(['amc_monitor', 'amc_selector_visible_state']),
      formattedItems () {
        if (!this.available_amc_instances) return []
        return this.available_amc_instances.map(item => {
          if (item.instance_id === this.selected_instance_id) {
            item._rowVariant = "info"
          }
          else {
            item._rowVariant = ""
          }
          return item
        })
      },
      rows1() {
        return this.datasets.length
      },
      rows3() {
        return this.etl_jobs.length
      },
      rows2() {
        return this.uploads.length
      },
    },
    watch: {
      //  whenever the endpoint selection changes this function will run
      selected_instance_id() {
        this.datasets = []
        if (this.selected_instance_id !== '') this.list_datasets()
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
      this.get_etl_jobs()
    },
    mounted: function() {
      this.userId = this.USER_POOL_ID
      this.read_system_configuration('GET', 'system/configuration')
      // Set the initial number of items
      this.totalRows = this.available_amc_instances.length
      this.selected_instance = this.amc_monitor
      this.selected_instance_id = this.selected_instance.instance_id || ''
      this.amc_selector_visible = this.amc_selector_visible_state
    },
    methods: {
      datetimeSortCompare(a, b, key) { //NOSONAR
        // this function is used to sort the StartedOn column
        if (key === 'StartedOn') {
          return new Date(b["StartedOn"]) - new Date(a["StartedOn"]);
        } else {
          // Let b-table handle sorting other fields (other than `StartedOn` field)
          return false
        }
      },
      changeAmcSelectorVisibility() {
        this.$store.commit('updateAmcSelectorVisibility', !this.amc_selector_visible)
      },
      onFiltered(filteredItems) {
        // Trigger pagination to update the number of buttons/pages due to filtering
        this.totalRows = filteredItems.length
        this.currentPage = 1
      },
      selectEndpoint(item) {
        this.selected_instance_id = item.instance_id
        this.selected_instance = item
        this.selected_dataset = ''
        // Reset dataset list pagination when user selects a new AMC instance.
        this.currentPage1 = 1
        this.$store.commit('updateAmcMonitor', this.selected_instance)
      },
      unselectEndpoint() {
        this.selected_instance_id = ''
        this.selected_dataset = ''
        this.selected_instance = ''
      },
      onDatasetSelected(items) {
        if (items.length > 0) {
          this.selected_dataset = items[0].dataSetId
          this.listDatasetUploads(this.selected_dataset)
        } else {
          this.uploads = []
          this.selected_dataset=''
        }
      },
      async deleteDataset(dataSetId) {
        this.datasets = this.datasets.filter(x => x.dataSetId !== dataSetId)
        await this.delete_dataset(
          {
            'dataSetId': dataSetId,
            'instance_id': this.selected_instance_id,
            "marketplace_id": this.selected_instance.marketplace_id,
            "advertiser_id": this.selected_instance.advertiser_id,
            "user_id":  this.userId
          })
      },
      async delete_dataset(data) {
        const apiName = 'amcufa-api'
        const method = 'POST'
        const resource = 'delete_dataset'
        try {
          console.log("sending " + method + " " + resource + " " + JSON.stringify(data))
          let requestOpts = {
            headers: {'Content-Type': 'application/json'},
            body: data
          };
          await API.post(apiName, resource, requestOpts);
        }
        catch (e) {
          console.log("ERROR: " + e)
          if (e.response) console.log(e.response.data.message)
        }
      },
      async listDatasetUploads(dataSetId) {
        this.selected_dataset = dataSetId
        this.upload_failure = ''
        await this.list_uploads(
          {
            'dataSetId': dataSetId,
            'instance_id': this.selected_instance_id,
            "marketplace_id": this.selected_instance.marketplace_id,
            "advertiser_id": this.selected_instance.advertiser_id,
            "user_id":  this.userId
        })
        await this.list_upload_failures({
            'dataSetId': dataSetId,
            'instance_id': this.selected_instance_id,
            "marketplace_id": this.selected_instance.marketplace_id,
            "advertiser_id": this.selected_instance.advertiser_id,
            "user_id":  this.userId
          })
      },
      async list_uploads(data) {
        this.uploads = []
        const apiName = 'amcufa-api'
        const method = 'POST'
        const resource = 'list_uploads'
        this.isBusy3 = true;
        try {
          console.log("sending " + method + " " + resource + " " + JSON.stringify(data))
          let requestOpts = {
            headers: {'Content-Type': 'application/json'},
            body: data
          };
          do {
            const response = await API.post(apiName, resource, requestOpts);
            if (response.authorize_url){
              this.process_redirect(response)
            }
            this.uploads.push(...response.uploads);
            data.nextToken = response.nextToken;
            requestOpts.body = data;
          } while (data.nextToken);
        }
        catch (e) {
          console.log("ERROR: " + e)
          if (e.response) console.log(e.response.data.message)
        } finally {
          this.isBusy3 = false;
        }
      },
      async list_upload_failures(data) {
        this.upload_failure = ""
        const apiName = 'amcufa-api'
        const method = 'POST'
        const resource = 'list_upload_failures'
        this.isBusy5 = true;
        try {
          console.log("sending " + method + " " + resource + " " + JSON.stringify(data))
          let requestOpts = {
            headers: {'Content-Type': 'application/json'},
            body: data
          };
          const response = await API.post(apiName, resource, requestOpts);
          this.upload_failure = response
        }
        catch (e) {
          console.log("ERROR: " + e)
          if (e.response) console.log(e.response.data.message)
        } finally {
          this.isBusy5 = false;
        }
      },
      async list_datasets() {
        this.showAmcApiError = false
        const apiName = 'amcufa-api'
        const method = 'POST'
        const data = {
          'instance_id': this.selected_instance_id,
          "marketplace_id": this.selected_instance.marketplace_id,
          "advertiser_id": this.selected_instance.advertiser_id,
          "user_id":  this.userId
        }
        const resource = 'list_datasets'
        this.isBusy1 = true;
        try {
          console.log("sending " + method + " " + resource + " " + JSON.stringify(data))
          let requestOpts = {
            headers: {'Content-Type': 'application/json'},
            body: data
          };
          const response = await API.post(apiName, resource, requestOpts);
          if (response.Status === "Error") {
            this.showAmcApiError = true
          }else if (response.authorize_url){
            this.process_redirect(response)
          }
           else {
            this.datasets = response.dataSets
          }
        }
        catch (e) {
          console.log("ERROR: " + e)
          if (e.response) {
            console.log(e.response.data.message)
            this.amcErrorMessage = e.response.data.message
            this.showAmcApiError = true
          }
        } finally {
          this.isBusy1 = false;
        }
      },
      async get_etl_jobs() {
        this.isBusy2 = true;
        this.etl_jobs = []
        const apiName = 'amcufa-api'
        let response = ""
        const method = 'GET'
        const resource = 'get_etl_jobs'
        try {
          console.log("sending " + method + " " + resource)
          response = await API.get(apiName, resource);
          if ('JobRuns' in response) { //NOSONAR
            this.etl_jobs = response.JobRuns.map(x => { //NOSONAR
              x["filename"] = x.Arguments["--source_key"];
              if ("StartedOn" in x) x["StartedOn"] = new Date(x["StartedOn"]).toLocaleString()
              return x
            })
          }else if (response.authorize_url){
            this.process_redirect(response)
          }
        }
        catch (e) {
          console.log("ERROR: " + e)
          if (e.response) console.log(e.response.data.message)
        } finally {
          this.isBusy2 = false;
        }
      },
      async read_system_configuration(method, resource) {
        this.showServerError = false
        console.log("sending " + method + " " + resource)
        const apiName = 'amcufa-api'
        let response = ""
        this.isBusy4 = true;
        try {
          response = await API.get(apiName, resource);
          if (Array.isArray(response) && response.length > 0 &&
            typeof response[0] == "object" && "Value" in response[0]) {
              this.available_amc_instances = response[0]["Value"]
              // If there is only one registered AMC Instance, then select that one by default:
              if (this.available_amc_instances.length === 1) {
                this.selected_instance_id = this.available_amc_instances[0].instance_id
                this.selected_instance = this.available_amc_instances[0]
              }
          } else {
            this.$router.push({path: '/settings'})
          }
        }
        catch (e) {
          console.log(e)
          this.showServerError = true
        } finally {
          this.isBusy4 = false;
        }
      },
      process_redirect(response){
        const current_page = "step6"
        const state_key = current_page + this.userId + Date.now()
        const b64_state_key = btoa(current_page + this.userId + Date.now())
        let state_vars = {
          "amc_monitor": this.selected_instance,
          "amc_selector_visible_state": this.amc_selector_visible,
          "current_page": current_page
        }
        localStorage.setItem(state_key, JSON.stringify(state_vars))
        window.location.href = response.authorize_url + "&state=" + b64_state_key
      }
    }
  }
</script>

<style>
.collapsed > .when-open,
.not-collapsed > .when-closed {
  display: none;
}
</style>
