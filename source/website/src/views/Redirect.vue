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
            <Sidebar />
          </b-col>
          <b-col cols="10">
            <b-alert
              v-model="showServerError"
              variant="danger"
            >
              Server error: See Cloudwatch logs for API resource.
              <b-button variant="info" @click="redirect_settings_step">
                Dismiss
              </b-button>
            </b-alert>
            <b-alert
              v-model="showUnAuthroizedError"
              variant="danger"
            >
              Error: AMC Request Unauthorized.
              <b-button variant="info" @click="redirect_settings_step">
                Dismiss
              </b-button>
            </b-alert>
            <b-col v-if="show_progress_bar()" cols="10">
              <p> Redirecting ...</p>
              <b-progress :value="value" :max="max" class="mb-3"></b-progress>
            </b-col>
          </b-col>
        </b-row>
      </b-container>
    </div>
  </div>
</template>
<script>
    import { API } from 'aws-amplify';
    import Header from '@/components/Header.vue'
    import Sidebar from '@/components/Sidebar.vue'
    import { mapState } from 'vuex'
    export default {
      name: "Redirect",
      components: {
        Header, Sidebar
      },
      data() {
        return {
          value: 0,
          max: 100,
          timer: null,
          userId: null,
          showServerError: false,
          showUnAuthroizedError: false,
          defaultStep: "/settings"
        }
      },
      computed: {
        ...mapState(['amc_instances_selected', 's3key', 'dataset_definition', 'selected_dataset', 'deleted_columns', 'step3_form_input', 'amc_monitor', 'amc_selector_visible_state']),
      },
      mounted: function() {
        const vm = this;
        let i = 0;
        this.timer = setInterval(() => {
          vm.value = i
          i++
        }, 100)
        this.userId = this.USER_POOL_ID
        this.new_s3key = this.s3key
        this.new_dataset_definition = this.dataset_definition
        this.new_selected_dataset = this.selected_dataset
        this.new_deleted_columns = this.deleted_columns
        this.new_amc_monitor = this.amc_monitor
        this.new_amc_selector_visible_state = this.amc_selector_visible_state
        this.new_amc_instances_selected = this.amc_instances_selected
        this.loadRedirectUri()

      },
      beforeDestroy() {
        this.clear_timer()
      },
      methods: {
        show_progress_bar(){
          return (!this.showUnAuthroizedError && !this.showServerError)
        },
        clear_timer(){
          clearInterval(this.timer)
          this.timer = null
        },
        deny_redirect() {
          this.showUnAuthroizedError = true
          this.clear_timer()
        },
        redirect_settings_step() {
          this.$router.push({path: this.defaultStep})
        },
        loadRedirectUri() {
          const currentUrl = new URL(window.location.href);
          const state = currentUrl.searchParams.get("amz-state");
          const state_key = atob(decodeURIComponent(state));
          let state_vars = JSON.parse(localStorage.getItem(state_key) || "{}")
          if (Object.keys(state_vars).length === 0) {
            console.log("Warning: Invalid State.")
          } else {
            localStorage.removeItem(state_key)
          }
          this.keep_step_state(state_vars || {})
          const current_page = state_vars.current_page || this.defaultStep
          if (currentUrl.searchParams.get("error") == "access_denied") {
            this.deny_redirect()
          } else {
            const auth_code = currentUrl.searchParams.get("amz-code");
            this.send_request('POST', 'validate_amc_request', { "auth_code": auth_code, "user_id": this.userId }, current_page)
          }
        },
        async send_request(method, resource, data, state) {
          this.showServerError = false
          console.log("sending " + method + " " + resource + " " + JSON.stringify(data))
          const apiName = 'amcufa-api'
          this.isBusy = true;
          let response = {}
          try {
            if (method === "GET") {
              await API.get(apiName, resource);
            } else if (method === "POST") {
              let requestOpts = {
                headers: {'Content-Type': 'application/json'},
                body: data
              };
              response = await API.post(apiName, resource, requestOpts);
            }
            if (response.authorize_url || response.Status === "Error"){
              this.deny_redirect()
            }else{
              // redirect to step after authroization
              this.$router.push({path: state})
            }

          }
          catch (e) {
            this.showServerError = true;
            console.log(e)
          } finally {
            this.isBusy = false;
          }
        },
        keep_step_state(state_vars){
          // keep state between steps when redirecting.
          this.$store.commit('updateSelectedAmcInstances', state_vars.amc_instances_selected)
          this.$store.commit('updateS3key', state_vars.s3key)
          this.$store.commit('updateDatasetDefinition', state_vars.dataset_definition)
          this.$store.commit('updateSelectedDataset', state_vars.selected_dataset)
          this.$store.commit('updateDeletedColumns', state_vars.deleted_columns)
          this.$store.commit('saveStep3FormInput', state_vars.step3_form_input)
          this.$store.commit('updateAmcMonitor', state_vars.amc_monitor)
          this.$store.commit('updateAmcSelectorVisibility', state_vars.amc_selector_visible_state)
        }
      }
    }
</script>
