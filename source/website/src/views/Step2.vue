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
            <Sidebar :is-step2-active="true" />
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
              v-model="showFormError"
              variant="danger"
              dismissible
            >
              You must select at least one AMC Instance.
            </b-alert>
            <h3>Select AMC Endpoints</h3>
            <div v-if="isBusy === false">
              <b-row>
                <b-col>
                  <p v-if="selected_amc_instances.length === 0" class="text-secondary">
                    Select one or more AMC endpoints to receive uploads.
                  </p>
                  <p v-else-if="selected_amc_instances.length === 1">
                    {{ selected_amc_instances.length }} AMC instance selected.
                  </p>
                  <p v-else>
                    {{ selected_amc_instances.length }} AMC instances selected.
                  </p>
                </b-col>
                <b-col sm="3" align="right" class="row align-items-end">
                  <button type="submit" class="btn btn-outline-primary mb-2" @click="$router.push({path: '/step1'})">
                    Previous
                  </button> &nbsp;
                  <button type="submit" class="btn btn-primary mb-2" @click="onSubmit">
                    Next
                  </button>
                </b-col>
              </b-row>
              <br>
              <!-- User Interface controls -->
              <b-row>
                <b-col class="my-1">
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

                <b-col class="my-1">
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
                      :aria-describedby="ariaDescribedby"
                      class="mt-1"
                    >

                      <div class="custom-control custom-control-inline custom-checkbox">
                        <input
                          v-model="filterOn"
                          id="filter_endpoint"
                          class="custom-control-input"
                          type="checkbox"
                          value="instance_id" />
                          <label class="custom-control-label" for="filter_endpoint">Instance ID</label>
                      </div>
                      <div class="custom-control custom-control-inline custom-checkbox">
                        <input
                          v-model="filterOn"
                          id="filter_tag_list"
                          class="custom-control-input"
                          type="checkbox"
                          value="tag_list" />
                          <label class="custom-control-label" for="filter_tag_list">Tags</label>
                      </div>
                    </b-form-checkbox-group>
                  </b-form-group>
                </b-col>
              </b-row>
            </div>
            <!-- Main table element -->
            <b-table
              :items="formattedItems"
              :fields="fields"
              :filter="filter"
              :filter-included-fields="filterOn"
              :busy="isBusy"
              :current-page="currentPage"
              :per-page="perPage"
              stacked="md"
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
                <b-button v-if="!selected_amc_instances.map(x => x.instance_id).includes(row.item.instance_id)" size="sm" class="mr-1" @click="select(row.item)">
                  Select
                </b-button>
                <b-button v-if="selected_amc_instances.map(x => x.instance_id).includes(row.item.instance_id)" size="sm" class="mr-1" @click="unselectEndpoint(row.item)">
                  Unselect
                </b-button>
              </template>
            </b-table>
            <b-pagination
              v-if="formattedItems.length > perPage"
              v-model="currentPage"
              align="center"
              :per-page="perPage"
              :total-rows="formattedItems.length"
              aria-controls="shotTable"
            ></b-pagination>
            <div v-if="isBusy === false">
              <b-button size="sm" @click="selectAll">
                Select all
              </b-button> &nbsp;
              <b-button size="sm" @click="clearAll">
                Clear all
              </b-button>
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
  name: "Step2",
  components: {
    Header, Sidebar
  },
  data() {
    return {
      currentPage: 1,
      perPage: 5,
      isBusy: false,
      isStep2Active: true,
      available_amc_instances: [{"tags": [], "instance_id": "", "advertiser_id": "", "marketplace_id": "", "data_upload_account_id": ""}],
      filtered_amc_instances: [],
      fields: [
        {key: 'actions', label: 'Actions' },
        {key: 'instance_id', label: 'AMC Instance ID'},
        {key: 'advertiser_id', label: 'Amazon Ads Advertiser ID'},
        {key: 'marketplace_id', label: 'Amazon Ads MarketPlace ID'},
        {key: 'data_upload_account_id', label: 'Data Upload Account ID'},
        {key: 'tags', label: 'Tags', sortable: false}
      ],
      filter: null,
      filterOn: [],
      showServerError: false,
      showFormError: false,
      response: '',
      selected_amc_instances: []
    }
  },
  computed: {
    formattedItems () {
      if (!this.available_amc_instances) return []
      return this.available_amc_instances.map(item => {
        item._rowVariant = ""
        for(let index in this.selected_amc_instances){
          if (this.selected_amc_instances[index].instance_id === item.instance_id){
            item._rowVariant = "info"
            break
          }
        }
        return item
      })
    },
    ...mapState(['amc_instances_selected']),
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
    onFiltered(filteredItems) {
      this.filtered_amc_instances = filteredItems
    },
    selectAll() {
      // apply select all to the filtered table result if it has been filtered
      if (this.filtered_amc_instances.length > 0) {
        this.filtered_amc_instances.forEach(x => this.select(x))
      } else {
        this.selected_amc_instances = this.available_amc_instances.map(x => x)
      }
    },
    clearAll() {
      this.selected_amc_instances = []
    },
    select(item) {
      this.showFormError = false
      if (!(this.selected_amc_instances.map(x => x.instance_id).includes(item.instance_id))) {
        this.selected_amc_instances.push(item)
      }
    },
    unselectEndpoint(item) {
      this.selected_amc_instances.map(
        (x, index) => {
          if (x.instance_id === item.instance_id){
            this.selected_amc_instances.splice(index, 1)
          }
        })
    },
    onSubmit() {
      this.showServerError = false
      this.showFormError = false
      if (this.validateForm()) {
        this.$store.commit('updateSelectedAmcInstances', this.selected_amc_instances)
        this.$router.push({path: '/step3'})
      }
    },
    validateForm() {
      if (this.selected_amc_instances.length === 0) {
        this.showFormError = true;
        return false
      }
      return true
    },
    async read_system_configuration(method, resource) {
      this.showServerError = false
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
          this.available_amc_instances = response[0]["Value"]
          // set default instance_id if there is only one to choose
          if (this.available_amc_instances.length == 1) {
            this.select(this.available_amc_instances[0])
          }
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
.hidden_header {
  display: none;
}
</style>
