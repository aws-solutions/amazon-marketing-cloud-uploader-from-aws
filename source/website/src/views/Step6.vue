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
            <b-row>
              <b-col>
                <h3>Phase 1: Datasets defined</h3>
              </b-col>
              <b-col align="right">
                <b-button @click="list_datasets()">
                  Refresh
                </b-button>
              </b-col>
            </b-row>
            <b-table
              ref="datasetTable"
              select-mode="single"
              selectable
              responsive="sm"
              small
              :fields="dataset_fields"
              :items="datasets"
              :busy="isBusy"
              :per-page="perPagePhase1"
              :current-page="currentPagePhase1"
              sort-by="updatedTime"
              :sort-desc="true"
              show-empty
              @row-selected="onRowSelected"
            >
              <template #empty="scope">
                {{ scope.emptyText }}
              </template>
              <template #cell(createdtime)="data">
                {{ new Date(data.item.createdTime).toLocaleString() }}
              </template>
              <template #cell(updatedtime)="data">
                {{ new Date(data.item.updatedTime).toLocaleString() }}
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
              v-if="datasets.length > perPagePhase1"
              v-model="currentPagePhase1"
              align="center"
              :per-page="perPagePhase1"
              :total-rows="rowsPhase1"
              aria-controls="shotTable"
            ></b-pagination>
            <br>
            <b-row>
              <b-col>
                <h3>Phase 2: Datasets transformed</h3>
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
              :per-page="perPagePhase2"
              :current-page="currentPagePhase2"
              sort-by="StartedOn"
              :sort-desc="true"
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
              v-if="etl_jobs.length > perPagePhase2"
              v-model="currentPagePhase2"
              align="center"
              :per-page="perPagePhase2"
              :total-rows="rowsPhase2"
              aria-controls="shotTable"
            ></b-pagination>
            <br>
            <b-row>
              <b-col>
                <h3>Phase 3: Datasets uploaded</h3>
                <div v-if="selected_dataset">
                  Showing uploads for {{ selected_dataset }}
                </div>
                <div v-else>
                  Please select a dataset from the table in Phase 1.
                </div>
              </b-col>
              <b-col v-if="selected_dataset" align="right">
                <br>
                <b-button @click="listDatasetUploads(`${selected_dataset}`)">
                  Refresh
                </b-button>
              </b-col>
            </b-row>
            <div v-if="selected_dataset">
              <b-table
                :items="uploads"
                :fields="upload_fields"
                :busy="isBusy3"
                :per-page="perPagePhase3"
                :current-page="currentPagePhase3"
                sort-by="dateCreated"
                :sort-desc="true"
                show-empty
                small
                responsive="sm"
              >
                <template #empty>
                  The dataset {{ selected_dataset }} has not been uploaded.
                </template>
                <template #table-busy>
                  <div class="text-center my-2">
                    <b-spinner class="align-middle"></b-spinner>
                    <strong>&nbsp;&nbsp;Loading...</strong>
                  </div>
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
                v-if="uploads.length > perPagePhase3"
                v-model="currentPagePhase3"
                align="center"
                :per-page="perPagePhase3"
                :total-rows="rowsPhase3"
                aria-controls="shotTable"
              ></b-pagination>
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

  export default {
    name: "Step5",
    components: {
      Header, Sidebar
    },
    data() {
      return {
        currentPagePhase3: 1,
        perPagePhase3: 10,
        currentPagePhase2: 1,
        perPagePhase2: 5,
        currentPagePhase1: 1,
        perPagePhase1: 10,
        datasets: [],
        selected_dataset: '',
        dataset_fields: [
          {key: 'selected'},
          {key: 'dataSetId', sortable:true},
          {key: 'description'},
          {key: 'dataSetType', sortable:true},
          {key: 'fileFormat', sortable:true},
          {key: 'createdTime', sortable:true},
          {key: 'updatedTime', sortable:true},
          {key: 'Actions'}
        ],
        etl_jobs: [],
        etl_fields: ['DatasetId', 'Id', 'StartedOn', 'CompletedOn', 'ExecutionTime', 'JobRunState', 'show_details'],
        uploads: [],
        upload_fields: [
          {key: "dateCreated", label: "Date Created", sortable: true},
          {key: "totalFileCount", label: "Total Files"},
          {key: "errorFileCount", label: "Bad Files"},
          {key: "rowsAcceptedTotal", label: "Rows Accepted"},
          {key: "rowsDroppedTotal", label: "Rows Dropped"},
          {key: "rowsWithResolvedIdentity", label: "Identities Resolved"},
          {key: "sourceFileS3Key", label: "Source File", sortable: true},
          {key: "uploadId", label: "Upload Id"},
          {key: "status", label: "Status"},
          {key: "show_details", label: "Show Details"}
        ],
        isBusy: false,
        isBusy2: false,
        isBusy3: false,
        isStep5Active: true,
        response: ''
      }
    },
    computed: {
      rowsPhase1() {
        return this.datasets.length
      },
      rowsPhase2() {
        return this.etl_jobs.length
      },
      rowsPhase3() {
        return this.uploads.length
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
      this.list_datasets()
      this.get_etl_jobs()
    },
    methods: {
      onRowSelected(items) {
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
        await this.delete_dataset({'dataSetId': dataSetId})
      },
      async delete_dataset(data) {
        const apiName = 'amcufa-api'
        let response = ""
        const method = 'POST'
        const resource = 'delete_dataset'
        try {
          console.log("sending " + method + " " + resource + " " + JSON.stringify(data))
          let requestOpts = {
            headers: {'Content-Type': 'application/json'},
            body: data
          };
          response = await this.$Amplify.API.post(apiName, resource, requestOpts);
          console.log(response)
        }
        catch (e) {
          console.log("ERROR: " + e.response.data.message)
          this.response = e.response.data.message
        }
      },
      async listDatasetUploads(dataSetId) {
        this.selected_dataset = dataSetId
        await this.list_uploads({'dataSetId': dataSetId})
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
            const response = await this.$Amplify.API.post(apiName, resource, requestOpts);
            this.uploads.push(...response.uploads);
            console.log(this.uploads)
            data.nextToken = response.nextToken;
            requestOpts.body = data;
          } while (data.nextToken);
        }
        catch (e) {
          console.log("ERROR: " + e.response.data.message)
          this.isBusy3 = false;
          this.response = e.response.data.message
        }
        this.isBusy3 = false;
      },
      async list_datasets() {
        const apiName = 'amcufa-api'
        let response = ""
        const method = 'GET'
        const resource = 'list_datasets'
        this.isBusy = true;
        try {
          if (method === "GET") {
            console.log("sending " + method + " " + resource)
            response = await this.$Amplify.API.get(apiName, resource);
            console.log(response)
            this.datasets = response.dataSets
          }
        }
        catch (e) {
          console.log("ERROR: " + e.response.data.message)
          this.isBusy = false;
          this.response = e.response.data.message
        }
        this.isBusy = false;
      },
      async get_etl_jobs() {
        this.isBusy2 = true;
        this.etl_jobs = []
        const apiName = 'amcufa-api'
        let response = ""
        const method = 'GET'
        const resource = 'get_etl_jobs'
        try {
          if (method === "GET") {
            console.log("sending " + method + " " + resource)
            response = await this.$Amplify.API.get(apiName, resource);
            console.log(response)
            this.etl_jobs = response.JobRuns
          }
        }
        catch (e) {
          console.log("ERROR: " + e.response.data.message)
          this.isBusy2 = false;
          this.response = e.response.data.message
        }
        this.isBusy2 = false;
      }
    }
  }
</script>
