<!--
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
-->

<template>
  <div>
    <div class="headerTextBackground">
      <Header />
      <b-container fluid>
        <b-alert
          v-model="showServerError"
          variant="danger"
          dismissible
        >
          Error reading file. See Cloudwatch logs for API resource, /api/get_data_columns.
        </b-alert>
        <b-alert
          v-model="showMissingDataAlert"
          variant="danger"
          dismissible
        >
          Missing s3key. Go back and select a file.
        </b-alert>
        <b-alert 
          v-model="showBadRequestError"
          variant="danger"
          dismissible
        >
          Error: {{ results }}
        </b-alert>
        <b-alert
          v-model="showUserIdWarning"
          variant="danger"
          dismissible
        >
          {{ userIdWarningMessage }}
        </b-alert>
        <b-alert
          v-if="incompleteFields.errorItems.length > 0"
          v-model="showIncompleteFieldsError"
          variant="danger"
          dismissible
        >
          {{ incompleteFields.errorType }} is missing for fields {{ incompleteFields.errorItems }}
        </b-alert>
        <b-alert
          v-if="mainEventTimeSelected && dataset_definition.dataSetType === 'FACT'"
          v-model="showIncompleteTimeFieldError"
          variant="danger"
          dismissible
        >
          FACT datasets must include a MainEventTime field.
        </b-alert>
        <b-alert
          v-if="mainEventTimeSelected && dataset_definition.dataSetType === 'DIMENSION'"
          v-model="showUnexpectedTimeFieldError"
          variant="danger"
          dismissible
        >
          DIMENSION datasets must not include a MainEventTime field.
        </b-alert>
        <b-alert
          :show="showImportError"
          variant="danger"
          dismissible
        >
          Import failed. Check data format.
        </b-alert>
        <b-row style="text-align: left">
          <b-col cols="2">
            <Sidebar :is-step4-active="true" />
          </b-col>
          <b-col cols="10">
            <div v-if="selected_dataset === null">
              <h3>Define Columns</h3>
              <b-alert
                show
                variant="warning"
                dismissible
              >
                <strong>IMPORTANT:</strong> When defining columns in this step, it is very important to carefully indicate which columns contain PII. If you neglect to indicate that a column contains PII, then that column will load as plain text into AMC.
              </b-alert>
              <b-row>
                <b-col>
                  Fill in the table to define properties for each field in the input data.
                </b-col>
                <b-col sm="3" align="right">
                  <button type="submit" class="btn btn-outline-primary mb-2" @click="$router.push({path: '/step3'})">
                    Previous
                  </button> &nbsp;
                  <button type="submit" class="btn btn-primary mb-2" @click="onSubmit">
                    Next
                  </button>
                </b-col>
              </b-row>
              <b-table
                :items="items"
                :fields="fields" 
                :busy="busy_getting_datafile_columns"
                head-variant="light"
                small
                borderless
              >
                <template #cell(Actions)="data">
                  <b-link
                    class="text-danger"
                    @click="deleteColumn(`${data.item.name}`)"
                  >
                    Delete
                  </b-link>
                </template>
                <template #cell(description)="data">
                  <b-form-input 
                    :value="data.item.description"
                    @change="x => changeDescription(x, data.index)"
                  >
                  </b-form-input>
                </template>
                <template #cell(data_type)="data">
                  <b-form-select 
                    id="dropdown-1" 
                    :options="data_type_options"
                    :value="data.item.data_type" 
                    @change="x => changeDataType(x, data.index)"
                  >
                  </b-form-select>
                </template>
                <template #cell(nullable)="data">
                  <b-form-checkbox
                    v-model="data.item.nullable"
                    :disabled="data.item.column_type === 'PII'"
                    @change="changeNullable()"
                  >
                  </b-form-checkbox>
                </template>
                <template #cell(column_type)="data">
                  <b-form-select 
                    id="dropdown-column-type" 
                    :options="column_type_options"
                    :value="data.item.column_type" 
                    @change="x => changeColumnType(x, data.index)"
                  >
                  </b-form-select>
                </template>
                <template #cell(pii_type)="data">
                  <b-form-select
                    id="dropdown-pii-type"
                    :options="pii_type_options"
                    :value="data.item.pii_type"
                    :disabled="data.item.column_type !== 'PII'"
                    @change="x => changePiiType(x, data.index)"
                  >
                  </b-form-select>
                </template>
                <template #table-busy>
                  <div class="text-center my-2">
                    <b-spinner class="align-middle"></b-spinner>
                    <strong>&nbsp;&nbsp;Loading...</strong>
                  </div>
                </template>
              </b-table>
              <b-row>
                <b-col align="left">
                  <b-button id="import_button" type="button" variant="outline-secondary" class="mb-2" @click="onImport">
                    Import
                  </b-button> &nbsp;
                  <b-form-file id="importFile" v-model="importFilename" style="display:none;" accept="application/json" @input="importFile"></b-form-file>
                  <b-button id="export_button" type="button" variant="outline-secondary" class="mb-2" @click="onExport">
                    Export
                  </b-button>
                </b-col>
                <b-col align="right">
                  <b-button id="reset_button" type="reset" variant="outline-secondary" class="mb-2" @click="onReset">
                    Reset
                  </b-button>
                </b-col>
              </b-row>
            </div>
            <div v-if="selected_dataset !== null">
              <h3>Validate Columns</h3>
              <!-- The following two alerts are intended to help the user know
              when their data file does not have the same columns that were defined
              for the dataset they want to merge with.
              -->
              <b-alert
                :show="missing_columns.length > 0 && busy_getting_datafile_columns === false && busy_getting_dataset_definition === false"
                variant="danger"
                dismissible
              >
                ERROR: Your data file is missing the following columns required to join with this dataset: {{ missing_columns }}
              </b-alert>
              <b-alert
                :show="extra_columns.length > 0 && busy_getting_datafile_columns === false && busy_getting_dataset_definition === false"
                variant="warning"
                dismissible
              >
                WARNING: The following columns will not be uploaded from {{ s3key }} because they are undefined for dataset {{ selected_dataset }}: {{ extra_columns }}
              </b-alert>
              <b-row>
                <b-col>
                  <div v-if="busy_getting_datafile_columns || busy_getting_dataset_definition">
                    Checking compatibility... &nbsp;<b-spinner small class="align-middle"></b-spinner>
                  </div>
                  <div v-else>
                    "<span style="font-family: monospace;">{{ s3key }}</span>" is <b>{{ missing_columns.length>0?"not compatible":"compatible" }}</b> with dataset "<span style="font-family: monospace;">{{ selected_dataset }}</span>".
                  </div>
                </b-col>
                <b-col sm="3" align="right" class="row align-items-end">
                  <button type="submit" class="btn btn-outline-primary mb-2" @click="$router.push({path: '/step3'})">
                    Previous
                  </button> &nbsp;
                  <button
                    :disabled="missing_columns.length > 0"
                    type="submit" 
                    class="btn btn-primary mb-2" 
                    @click="onSubmit"
                  >
                    Next
                  </button>
                </b-col>
              </b-row>
              <b-card>
                Dataset definition:
                <b-table
                  :items="selected_dataset_items"
                  :fields="selected_dataset_fields"
                  :busy="busy_getting_dataset_definition"
                  head-variant="light"
                  small
                  borderless
                >
                  <template #cell(description)="data">
                    <b-form-input
                      :value="data.item.description"
                      disabled
                    >
                    </b-form-input>
                  </template>
                  <template #cell(data_type)="data">
                    <b-form-select
                      id="dropdown-1"
                      :options="data_type_options"
                      :value="data.item.data_type"
                      disabled
                    >
                    </b-form-select>
                  </template>
                  <template #cell(nullable)="data">
                    <b-form-checkbox
                      v-model="data.item.nullable"
                      disabled
                    >
                    </b-form-checkbox>
                  </template>
                  <template #cell(column_type)="data">
                    <b-form-select
                      id="dropdown-column-type"
                      :options="column_type_options"
                      :value="data.item.column_type"
                      disabled
                    >
                    </b-form-select>
                  </template>
                  <template #cell(pii_type)="data">
                    <b-form-select
                      id="dropdown-pii-type"
                      :options="pii_type_options"
                      :value="data.item.pii_type"
                      disabled
                    >
                    </b-form-select>
                  </template>
                  <template #table-busy>
                    <div class="text-center my-2">
                      <b-spinner class="align-middle"></b-spinner>
                      <strong>&nbsp;&nbsp;Loading...</strong>
                    </div>
                  </template>
                </b-table>
              </b-card>
              <br>
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
  import {mapState} from "vuex";

  export default {
    name: "Step4",
    components: {
      Header, Sidebar
    },
    data() {
      return {
        new_dataset_definition: {},
        importFilename: null,
        showImportError: false,
        dismissSecs: 5,
        busy_getting_datafile_columns: false,
        busy_getting_dataset_definition: false,
        showServerError: false,
        showBadRequestError: false,
        showMissingDataAlert: false,
        showIncompleteFieldsError: false,
        showIncompleteTimeFieldError: false,
        showUnexpectedTimeFieldError: false,
        showUserIdWarning: false,
        userIdWarningMessage: "Do not include user_id and user_type columns in data files containing hashed identifiers. These columns are used by AMC when a match is found in a hashed record.",
        items: [],
        selected_dataset_items: [],
        selected_dataset_description: "",
        selected_dataset_period: "",
        selected_dataset_type: "",
        columns: [],
        selected_dataset_fields: [
          { key: 'name', sortable: true },
          { key: 'description', sortable: false },
          { key: 'data_type', sortable: true },
          { key: 'column_type', sortable: true },
          { key: 'pii_type', sortable: true },
          { key: 'nullable', sortable: false },
        ],
        content_type: "",
        fields: [
          { key: 'name', sortable: true },
          { key: 'description', sortable: false },
          { key: 'data_type', sortable: true },
          { key: 'column_type', sortable: true },
          { key: 'pii_type', sortable: true },
          { key: 'nullable', sortable: false },
          { key: 'Actions', sortable: false }
        ],
        data_type_options: [
          { value: 'STRING', text: 'String'},
          { value: 'DECIMAL', text: 'Decimal'},
          { value: 'INTEGER', text: 'Integer (32-bit)'},
          { value: 'LONG', text: 'Integer (64-bit)'},
          { value: 'TIMESTAMP', text: 'Timestamp'},
          { value: 'DATE', text: 'Date'}
        ],
        nullable_options: [true, false],
        column_type_options: [
          { value: 'PII', text: 'PII', disabled: false},
          { value: 'DIMENSION', text: 'Dimension', disabled: false},
          { value: 'METRIC', text: 'Metric', disabled: false},
          { value: 'isMainEventTime', text: 'MainEventTime', disabled: false},
        ],
        pii_type_options: [
          { value: 'EMAIL', text: 'EMAIL', disabled: false},
          { value: 'FIRST_NAME', text: 'FIRST_NAME', disabled: false},
          { value: 'LAST_NAME', text: 'LAST_NAME', disabled: false},
          { value: 'PHONE', text: 'PHONE', disabled: false},
          { value: 'ADDRESS', text: 'ADDRESS', disabled: false},
          { value: 'CITY', text: 'CITY', disabled: false},
          { value: 'ZIP', text: 'ZIP', disabled: false},
          { value: 'STATE', text: 'STATE', disabled: false}
        ],
        results: {},
        isStep4Active: true
      }
    },
    computed: {
      ...mapState(['deleted_columns','dataset_definition', 's3key', 'step3_form_input', 'selected_dataset', 'destination_endpoints']),
      extra_columns() {
        const dataset_columns = this.selected_dataset_items.map(x => x.name)
        const file_columns = this.items.map(x => x.name)
        return file_columns.filter(x => !dataset_columns.includes(x))
      },
      missing_columns() {
        const dataset_columns = this.selected_dataset_items.map(x => x.name)
        const file_columns = this.items.map(x => x.name)
        return dataset_columns.filter(x => !file_columns.includes(x))
      },
      contains_hashed_identifier() {
        return this.items.filter(x => (x.column_type === 'PII')).length > 0
      },
      incompleteFields() {
        // check PII type
        if(this.items.filter(x => ((x.column_type === 'PII') && !!x.pii_type === false)).length > 0)
          return {
            errorItems: this.items.filter(x => ((x.column_type === 'PII') && x.pii_type==='')).map(x => x.name),
            errorType: 'PII Type'
          }

        // check column type
        if(this.items.filter(x => (x.column_type === '')).length > 0)
          return {
            errorItems: this.items.filter(x => x.column_type === '').map(x => x.name),
            errorType: 'Column Type'
          }

        // return empty if no errors
        return {
            errorItems: [],
            errorType: null
          }
      },
      mainEventTimeSelected() {
        return this.items.filter(x => (x.column_type === 'isMainEventTime')).length > 0
      },
    },
    activated: function () {
      console.log('activated')
    },
    deactivated: function () {
      console.log('deactivated');
    },
    created: function () {
      console.log('created')
    },
    mounted: function() {
      this.new_dataset_definition = this.dataset_definition
      if (this.selected_dataset !== null) {
        // If the user opted to join to an existing dataset, then load that dataset's
        // schema into the web form and disable any changes:
        this.describe_dataset()
      }
      // Otherwise prompt the user to specify the schema for the new dataset 
      // that they want to create:
      if (!this.s3key) {
        this.showMissingDataAlert = true
      }
      else {
        this.onReset()
      }
    },
    methods: {
      deleteColumn(column_name) {
        this.items = this.items.filter(x => x.name !== column_name)
        this.deleted_columns.push(column_name)
        this.$store.commit('updateDeletedColumns', this.deleted_columns)
        console.log("deleted_columns: " + this.deleted_columns)
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
            if (Array.isArray(contents) && contents.length > 0 && Object.keys(contents[0]).includes("name") && Object.keys(contents[0]).includes("description") && Object.keys(contents[0]).includes("data_type") && Object.keys(contents[0]).includes("column_type") && Object.keys(contents[0]).includes("pii_type")) {
              vm.items = contents
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
        const table_data = JSON.stringify(this.items);
        const blob = new Blob([table_data], {type: 'text/plain'});
        const e = document.createEvent('MouseEvents'),
            a = document.createElement('a');
        a.download = "column_definitions.json";
        a.href = window.URL.createObjectURL(blob);
        a.dataset.downloadurl = ['text/json', a.download, a.href].join(':');
        e.initEvent('click', true, false, window, 0, 0, 0, 0, 0, false, false, false, false, 0, null);
        a.dispatchEvent(e);
      },
      onReset() {
        this.$store.commit('updateDeletedColumns', [])
        this.get_datafile_columns('POST', 'get_data_columns', {'s3bucket': this.DATA_BUCKET_NAME, 's3key':this.s3key})
        this.column_type_options.forEach(x => x.disabled = false)
        this.pii_type_options.forEach(x => x.disabled = false)
      },
      validateForm() {
        // Data sets should be valid
        if (this.showBadRequestError || this.showServerError) return false
        // All fields must have values.
        if (this.incompleteFields.errorItems.length > 0) {
          this.showIncompleteFieldsError = true
          return false
        } else {
          this.showIncompleteFieldsError = false
        }
        // FACT datasets must have a field designated as the main event time.
        if (this.new_dataset_definition.dataSetType === 'FACT'
            && this.mainEventTimeSelected === false) {
          this.showIncompleteTimeFieldError = true
          return false
        } else {
          this.showIncompleteTimeFieldError = false
        }
        // DIMENSION datasets must not have a field designated as the main event time.
        if (this.new_dataset_definition.dataSetType === 'DIMENSION'
            && this.mainEventTimeSelected === true) {
          this.showUnexpectedTimeFieldError = true
          return false
        } else {
          this.showUnexpectedTimeFieldError = false
        }
        return true
      },
      onSubmit() {
        if (this.selected_dataset !== null) {
          this.extra_columns.forEach(x => this.deleteColumn(x))
          this.items = this.selected_dataset_items
          this.new_dataset_definition.dataSetId = this.selected_dataset
          this.new_dataset_definition.description = this.selected_dataset_description
          this.new_dataset_definition.dataSetType = this.selected_dataset_type
          this.new_dataset_definition.period = this.selected_dataset_period
        }
        if (!this.validateForm()) {console.log(this.validateForm()) 
          return }

        // remove the nullable attribute if it is false
        this.items.map(x => {
          if (x.nullable === false) delete x.nullable
        })
        // ------- Save form ------- //
        //
        // If hashed identifiers are present, then add user_id and user_type columns
        if (this.contains_hashed_identifier) {
          this.columns.push({
            "name": "user_id",
            "description": "The customer resolved id",
            "dataType": "STRING",
            "nullable": true,
            "isMainUserId": true
          })
          this.columns.push({
            "name": "user_type",
            "description": "The customer resolved type",
            "dataType": "STRING",
            "nullable": true,
            "isMainUserIdType": true
          })
        }
        // add hashed identifiers for each PII column
        this.items.filter(x => x.pii_type !== "")
          .forEach(x => {
            const column_definition = {
              "name": x.name,
              "description": "hashed " + x.description,
              "dataType": x.data_type,
              "externalUserIdType": {
                "type": "HashedIdentifier",
                "identifierType": x.pii_type
              }
            }
            if (x.nullable === true) column_definition.nullable = true
            this.columns.push(column_definition)
          }
        )
        // add identifier for main event timestamp column
        this.items.filter(x => x.column_type === 'isMainEventTime')
          .forEach(x => {
            const column_definition = {
              "name": x.name,
              "description": x.description,
              "dataType": x.data_type,
              "isMainEventTime": true
            }
            this.columns.push(column_definition)

          })

        // add identifiers for non-PII columns
        this.items.filter(x => (x.pii_type === "" && x.column_type !== 'isMainEventTime'))
          .forEach(x => {
            const column_definition = {
              "name": x.name,
              "description": x.description,
              "dataType": x.data_type,
              "columnType": x.column_type,
            }
            if (x.nullable === true) column_definition.nullable = true
            this.columns.push(column_definition)
          }
          )
        this.new_dataset_definition['columns'] = this.columns
        if (this.content_type === "application/json")
          this.new_dataset_definition['fileFormat'] = 'JSON'
        else if (this.content_type === "text/csv")
          this.new_dataset_definition['fileFormat'] = 'CSV'
        else
          console.log("ERROR: unrecognized content_type, " + this.content_type)
          this.showServerError = true;

        this.$store.commit('updateDatasetDefinition', this.new_dataset_definition)
        this.$router.push({path: '/step5'})
      },
      changeDescription(value, index) {
        this.items[index].description = value;
        this.$store.commit('saveStep3FormInput', this.items)
      },
      changeDataType(value, index) {
        this.items[index].data_type = value;
        this.$store.commit('saveStep3FormInput', this.items)
      },
      changeNullable() {
        this.$store.commit('saveStep3FormInput', this.items)
      },
      changeColumnType(value, index) {
        // enable timestamp option if that was just deselected
        if (this.items[index].column_type === 'isMainEventTime') {
          let idx = this.column_type_options.findIndex((x => x.value === 'isMainEventTime'))
          this.column_type_options[idx].disabled = false
        }
        // disable timestamp option if that was just selected
        if (value === 'isMainEventTime') {
          let idx = this.column_type_options.findIndex((x => x.value === 'isMainEventTime'))
          this.column_type_options[idx].disabled = true
          // automatically set data type to timestamp if column type is timestamp
          this.items[index].data_type = "TIMESTAMP"
        }
        // if changing from PII column to another, the PII Type and Nullable columns should be reset
        if (value !== 'PII' && this.items[index].column_type === 'PII') {
          // re-enable the previous PII Type value when unselecting the PII Column type
          const previous_value = this.items[index].pii_type
          let idx = this.pii_type_options.findIndex((x => x.value === previous_value));
          if (previous_value !== "") this.pii_type_options[idx].disabled = false

          this.items[index].pii_type = ""
          this.items[index].nullable = false
        }

        this.items[index].column_type = value;
        this.$store.commit('saveStep3FormInput', this.items)
      },
      changePiiType(value, index) {
        // enable previously selected value
        if (this.items[index].pii_type !== "") {
          const previous_value = this.items[index].pii_type
          let idx = this.pii_type_options.findIndex((x => x.value === previous_value));
          this.pii_type_options[idx].disabled = false
        }
        // disable currently selected value
        let idx = this.pii_type_options.findIndex((x => x.value === value))
        this.pii_type_options[idx].disabled = true
        this.items[index].pii_type = value
        this.items[index].nullable = true
        this.$store.commit('saveStep3FormInput', this.items)
      },
      async get_datafile_columns(method, resource, data) {
        data['destination_endpoint'] = this.destination_endpoints[0]
        console.log("sending " + method + " " + resource + " " + JSON.stringify(data))
        this.items = []
        this.$store.commit('updateDeletedColumns', [])
        const apiName = 'amcufa-api'
        let response = ""
        this.busy_getting_datafile_columns = true;
        try {
          if (method === "POST") {
            let requestOpts = {
              headers: {'Content-Type': 'application/json'},
              body: data
            };
            response = await this.$Amplify.API.post(apiName, resource, requestOpts);
          }
          this.items = response.columns.map(x => {return {
            "name": x,
            "description": x.charAt(0).toUpperCase() + x.replace(/[^a-zA-Z0-9]/g, ' ').slice(1),
            "data_type": "STRING",
            "column_type": "",
            "pii_type": ""}
          }).filter(x => !this.deleted_columns.includes(x.name) )

          // warn if table contains hashed identifiers and user_id or user_type columns
          const idx = this.items.findIndex((x => x.name === "user_id"))
          if (idx >= 0) {
            this.items[idx]._rowVariant = 'danger'
            this.showUserIdWarning = true;
          }
          const idx2 = this.items.findIndex((x => x.name === "user_type"))
          if (idx2 >= 0) {
            this.items[idx2]._rowVariant = 'danger'
            this.showUserIdWarning = true;
          }
          this.content_type = response.content_type
        }
        catch (e) {
          if(e.response.status === 400) this.showBadRequestError = true;
          else this.showServerError = true;

          console.log("ERROR: " + e.response.data.message)
          this.busy_getting_datafile_columns = false;
          this.results = e.response.data.message
        }
        this.busy_getting_datafile_columns = false;
      },
      async describe_dataset() {
        this.selected_dataset_items = []
        const apiName = 'amcufa-api'
        let response = ""
        const method = 'POST'
        const resource = 'describe_dataset'
        const data = {'dataSetId': this.selected_dataset, 'destination_endpoint': this.destination_endpoints[0]}
        this.busy_getting_dataset_definition = true;
        try {
          console.log("sending " + method + " " + resource + " " + JSON.stringify(data))
          let requestOpts = {
            headers: {'Content-Type': 'application/json'},
            body: data
          };
          response = await this.$Amplify.API.post(apiName, resource, requestOpts);
          this.selected_dataset_type = response.dataSetType
          this.selected_dataset_description = response.description
          this.selected_dataset_period = response.period
          // read schema for PII fields
          this.selected_dataset_items = this.selected_dataset_items.concat(response.columns.filter(x => "externalUserIdType" in x).map(x => ({"name": x.name, "description": x.description, "data_type": x.dataType, "column_type": "PII", "nullable": x.isNullable, "pii_type": x.externalUserIdType.identifierType})))
          // read schema for Timestamp field
          this.selected_dataset_items = this.selected_dataset_items.concat(response.columns.filter(x => x.isMainEventTime === true).map(x => ({"name": x.name, "description": x.description, "data_type": x.dataType, "column_type": "isMainEventTime", "pii_type":""})))
          // read schema for Dimension fields
          this.selected_dataset_items = this.selected_dataset_items.concat(response.columns.filter(x => x.columnType === "DIMENSION").map(x => ({"name": x.name, "description": x.description, "data_type": x.dataType, "column_type": x.columnType, "pii_type":"", "nullable": x.isNullable})))
          // read schema for Metric fields
          this.selected_dataset_items = this.selected_dataset_items.concat(response.columns.filter(x => x.columnType === "METRIC").map(x => ({"name": x.name, "description": x.description, "data_type": x.dataType, "column_type": x.columnType, "pii_type":"", "nullable": x.isNullable})))
        }
        catch (e) {
          console.log("ERROR: " + e.response.data.message)
          this.response = e.response.data.message
        }
        this.busy_getting_dataset_definition = false;
      },
  }
}
</script>
