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
            <Sidebar :is-step4-active="true" />
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
            <h3>Select destinations</h3>
            <div v-if="isBusy === false">
              <b-row>
                <b-col>
              <p v-if="selected_amc_instances.length === 0" class="text-secondary">Click table rows to select AMC Instances for upload.</p>
              <p v-else-if="selected_amc_instances.length === 1">{{selected_amc_instances.length}} AMC instance selected.</p>
              <p v-else="selected_amc_instances.length > 1">{{selected_amc_instances.length}} AMC instances selected.</p>
                </b-col>
              <b-col sm="3" align="right" class="row align-items-end">
                <button type="submit" class="btn btn-outline-primary mb-2" @click="$router.push('Step3')">
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
                        <b-button :disabled="!filter" @click="filter = ''">Clear</b-button>
                      </b-input-group-append>
                    </b-input-group>
                  </b-form-group>
                </b-col>

                <b-col lg="5" class="my-1">
                  <b-form-group
                      label="Filter On"
                      description="Leave all unchecked to filter on all data"
                      label-cols-sm="3"
                      label-align-sm="right"
                      label-size="sm"
                      class="mb-0"
                      v-slot="{ ariaDescribedby }"
                  >
                    <b-form-checkbox-group
                        v-model="filterOn"
                        :aria-describedby="ariaDescribedby"
                        class="mt-1"
                    >
                      <b-form-checkbox value="name">Endpoint</b-form-checkbox>
                      <b-form-checkbox value="age">Account Id</b-form-checkbox>
                      <b-form-checkbox value="tag_list">Tags</b-form-checkbox>
                    </b-form-checkbox-group>
                  </b-form-group>
                </b-col>
              </b-row>
            </div>
            <!-- Main table element -->
            <b-table
                :items="available_amc_instances"
                :fields="fields"
                :filter="filter"
                :filter-included-fields="filterOn"
                :busy="isBusy"
                stacked="md"
                show-empty
                small
                selectable
                select-mode="multi"
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
    name: "Step4",
    components: {
      Header, Sidebar
    },
    data() {
      return {
        isBusy: false,
        isStep4Active: true,
        available_amc_instances: [{"endpoint": "","data_upload_account_id": "", "tags": []}],
        fields: [
          {key: 'selected'},
          {key: 'endpoint', label: 'AMC Endpoint', sortable: true, thStyle: { width: '50%'}},
          {key: 'data_upload_account_id', label: 'Data Upload Account Id', sortable: true},
          {key: 'tag_list', label: 'Tags', sortable: false}
        ],
        totalRows: 1,
        filter: null,
        filterOn: [],
        showServerError: false,
        showFormError: false,
        response: '',
        selected_amc_instances: []
      }
    },
    computed: {
      ...mapState(['destinations']),
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
      this.selected_amc_instances = this.destinations
    },
    methods: {
      onSubmit() {
        this.showServerError = false
        this.showFormError = false
        if (this.validateForm()) {
          this.$store.commit('updateDestinations', this.selected_amc_instances)
          this.$router.push('Step5')
        }
      },
      validateForm() {
        if (this.selected_amc_instances.length === 0) {
          this.showFormError = true;
          return false
        }
        return true
      },
      onRowSelected(items) {
        let selected_amc_instances = [];
        for(let item of items) selected_amc_instances.push(item.endpoint)
        this.selected_amc_instances = selected_amc_instances
      },
      async read_system_configuration(method, resource) {
        this.showServerError = false
        this.results = []
        console.log("sending " + method + " " + resource)
        const apiName = 'amcufa-api'
        let response = ""
        this.isBusy = true;
        try {
          if (method === "GET") {
            response = await this.$Amplify.API.get(apiName, resource);
          }
          if (response.length > 0 && "Value" in response[0]) {
            this.available_amc_instances = response[0]["Value"]
            console.log(JSON.stringify(this.available_amc_instances))
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
