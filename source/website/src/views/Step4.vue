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
	           v-if="mainEventTimeSelected === false && new_dataset_definition.period !== 'DIMENSION'"
	           v-model="showIncompleteTimeFieldError"
	           variant="danger"
	           dismissible
        >
          Partition Scheme datasets must include a MainEventTime field.
        </b-alert>
        <b-alert
          v-if="mainEventTimeSelected && new_dataset_definition.period === 'DIMENSION'"
          v-model="showUnexpectedTimeFieldError"
          variant="danger"
          dismissible
        >
          Non-Partition Scheme datasets must not include a MainEventTime field.
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
                <b-col sm="3" text-align="right">
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
                  <div class="custom-control custom-checkbox">
                    <input type="checkbox" class="largerCheckbox" :value="data.item.column_type" v-model="data.item.nullable" @change="changeNullable()"/>
                  </div>
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
                <b-col cols="10">
                    <b-button id="import_button" type="button" variant="outline-secondary" class="mb-2" @click="onImport">
                      Import
                    </b-button> &nbsp;
                    <input type="file" class="form-control" id="importFile" @input="importFile" style="display:none;">
                  <b-button id="export_button" type="button" variant="outline-secondary" class="mb-2" @click="onExport">
                    Export
                  </b-button>
                </b-col>
                <b-col cols="2">
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
                <b-col sm="3" text-align="right" class="row align-items-end">
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
  import Header from '@/components/Header.vue';
  import Sidebar from '@/components/Sidebar.vue';
  import { API } from 'aws-amplify';
  import { mapState } from "vuex";

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
          { value: 'LiveRamp ID', text: 'LiveRamp ID', disabled: false},
          { value: 'Mobile Ad ID', text: 'Mobile Ad ID', disabled: false},
          { value: 'Experian ID', text: 'Experian ID', disabled: false},
        ],
        data_types_column_type_options: [
          {column_type: 'Experian ID', value: "STRING"},
          {column_type: 'LiveRamp ID', value: "STRING"},
          {column_type: 'Mobile Ad ID', value: "STRING"},
          {column_type: 'isMainEventTime', value: "TIMESTAMP"},
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
        isStep4Active: true,
        userId: null,
        new_s3key: null
      }
    },
    computed: {
      ...mapState(['deleted_columns','dataset_definition', 's3key', 'step3_form_input', 'selected_dataset', 'amc_instances_selected']),
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
      contains_liveramp_id() {
        return this.items.filter(x => (x.column_type === 'LiveRamp ID')).length > 0
      },
      contains_maid() {
        return this.items.filter(x => (x.column_type === 'Mobile Ad ID')).length > 0
      },
      contains_experian_id() {
        return this.items.filter(x => (x.column_type === 'Experian ID')).length > 0
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
      contains_identity() {
        return this.contains_hashed_identifier || this.contains_liveramp_id || this.contains_maid || this.contains_experian_id
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
      this.userId = this.USER_POOL_ID
      this.new_s3key = this.s3key
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
        e.initEvent('click', true, false, window, 0, 0, 0, 0, 0, false, false, false, false, 0, null); //NOSONAR
        a.dispatchEvent(e);
      },
      onReset() {
        this.$store.commit('updateDeletedColumns', [])
        this.get_datafile_columns(
            'POST',
            'get_data_columns',
            {
              's3bucket': this.DATA_BUCKET_NAME,
              's3key': this.s3key,
              'fileFormat': this.new_dataset_definition.fileFormat
            }
        )
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
        // Partition Scheme datasets must have a field designated as the main event time.
        if (this.new_dataset_definition.period !== 'DIMENSION'
            && this.mainEventTimeSelected === false) {
          this.showIncompleteTimeFieldError = true
          return false
        } else {
          this.showIncompleteTimeFieldError = false
        }
        // Non-Partition Scheme datasets must not have a field designated as the main event time.
        if (this.new_dataset_definition.period === 'DIMENSION'
            && this.mainEventTimeSelected === true) {
          this.showUnexpectedTimeFieldError = true
          return false
        } else {
          this.showUnexpectedTimeFieldError = false
        }
        return true
      },
      onSubmit() { // NOSONAR
        if (this.selected_dataset !== null) {
          this.extra_columns.forEach(x => this.deleteColumn(x))
          this.items = this.selected_dataset_items
          this.new_dataset_definition.dataSetId = this.selected_dataset
          this.new_dataset_definition.description = this.selected_dataset_description
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
        if (this.contains_hashed_identifier || this.contains_liveramp_id || this.contains_maid || this.contains_experian_id) {
          this.columns.push({
            "name": "user_id",
            "description": "The customer resolved id",
            "columnType": "DIMENSION",
            "dataType": "STRING",
            "nullable": true,
            "isMainUserId": true
          })
          this.columns.push({
            "name": "user_type",
            "description": "The customer resolved type",
            "columnType": "DIMENSION",
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
              "columnType": "DIMENSION",
              "dataType": x.data_type,
              "externalUserIdType": {
                "hashedPii": x.pii_type
              }
            }
            if (x.nullable === true) column_definition.nullable = true
            this.columns.push(column_definition)
          }
        )
        // add liveramp identifier
        this.items.filter(x => x.column_type === 'LiveRamp ID')
          .forEach(x => {
            const column_definition = {
              "name": x.name,
              "description": x.description,
              "dataType": x.data_type,
              "columnType": "DIMENSION",
              "externalUserIdType": {
                "externalIdentity": "LIVERAMP"
              }
            }
            if (x.nullable === true) column_definition.nullable = true
            this.columns.push(column_definition)
          })
        // add Mobile Ad identifier
         this.items.filter(x => x.column_type === 'Mobile Ad ID')
          .forEach(x => {
            const column_definition = {
              "name": x.name,
              "description": x.description,
              "dataType": x.data_type,
              "columnType": "DIMENSION",
              "externalUserIdType": {
                "externalIdentity": "MAID"
              }
            }
            if (x.nullable === true) column_definition.nullable = true
            this.columns.push(column_definition)
          })
        // add Experian
        this.items.filter(x => x.column_type === 'Experian ID')
          .forEach(x => {
            const column_definition = {
              "name": x.name,
              "description": x.description,
              "dataType": x.data_type,
              "columnType": "DIMENSION",
              "externalUserIdType": {
                "externalIdentity": "EXPERIAN"
              }
            }
            if (x.nullable === true) column_definition.nullable = true
            this.columns.push(column_definition)
          })
        // add identifier for main event timestamp column
        this.items.filter(x => x.column_type === 'isMainEventTime')
          .forEach(x => {
            const column_definition = {
              "name": x.name,
              "description": x.description,
              "columnType": "DIMENSION",
              "dataType": "TIMESTAMP",
              "isMainEventTime": true
            }
            this.columns.push(column_definition)

          })

        // add identifiers for non-PII columns
        this.items.filter(x => (x.pii_type === "" && (
            x.column_type !== 'isMainEventTime' &&
            x.column_type !== 'LiveRamp ID' &&
            x.column_type !== 'Mobile Ad ID' &&
            x.column_type !== 'Experian ID'
          )))
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

        this.new_dataset_definition["ContainsIdentity"] = this.contains_identity
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
      disable_column_type_options(column_type, disable){
        if (column_type !== 'PII' && column_type !== null && column_type.length > 0){
          let idx = this.column_type_options.findIndex((x => x.value === column_type))
          this.column_type_options[idx].disabled = disable
        }
      },
      changeColumnType(value, index) {
        // enable all column_type_options
        this.disable_column_type_options(this.items[index].column_type, false)
        // disable column_type option if that was just selected
        this.data_types_column_type_options.filter(x => {
          if (x.column_type === value){
            // automatically set data type.
            this.disable_column_type_options(value, true)
            this.items[index].data_type = x.value
          }
        })
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
        // This function gets the list of columns that are in the file that the user
        // is trying to upload. Those columns need to be the same as the columns defined
        // in the dataset, so this function will check that and show a warning in the
        // front-end if the dataset and files have different columns.
        data["instance_id"] = this.amc_instances_selected[0].instance_id
        data["marketplace_id"] = this.amc_instances_selected[0].marketplace_id
        data["advertiser_id"] = this.amc_instances_selected[0].advertiser_id
        data["user_id"] = this.userId
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
            response = await API.post(apiName, resource, requestOpts);
          }
          this.items = response.columns.map(x => {return {
            "name": x,
            "description": x.charAt(0).toUpperCase() + x.replace(/[^a-zA-Z0-9]/g, ' ').slice(1),
            "data_type": "STRING",
            "column_type": "",
            "pii_type": ""}
          }).filter(x => !this.deleted_columns.includes(x.name) )

          // The names "user_id" and "user_type" are reserved for columns that AMC generates.
          // If the upload file contains columns with those names, then show a warning.
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
          if (e.response?.status === 400) this.showBadRequestError = true;
          else this.showServerError = true;

          console.log("ERROR: " + e.response?.data.Message)
          this.busy_getting_datafile_columns = false;
          this.results = e.response?.data.Message
        }
        this.busy_getting_datafile_columns = false;
      },
      async describe_dataset() {
        this.selected_dataset_items = []
        const apiName = 'amcufa-api'
        let response = ""
        const method = 'POST'
        const resource = 'describe_dataset'
        const data = {
          'dataSetId': this.selected_dataset,
          'instance_id': this.amc_instances_selected[0].instance_id,
          "marketplace_id": this.amc_instances_selected[0].marketplace_id,
          "advertiser_id": this.amc_instances_selected[0].advertiser_id,
          "user_id": this.userId
        }
        this.busy_getting_dataset_definition = true;
        try {
          console.log("sending " + method + " " + resource + " " + JSON.stringify(data))
          let requestOpts = {
            headers: {'Content-Type': 'application/json'},
            body: data
          };
          response = await API.post(apiName, resource, requestOpts);
          if (response.authorize_url){
            const current_page = "step4"
            const state_key = current_page + this.userId + Date.now()
            const b64_state_key = btoa(current_page + this.userId + Date.now())
            let state_vars = {
              "amc_instances_selected": this.amc_instances_selected,
              "s3key": this.new_s3key,
              "dataset_definition": this.new_dataset_definition,
              "selected_dataset": this.selected_dataset,
              "deleted_columns": this.deleted_columns,
              "step3_form_input": this.items,
              "current_page": current_page
            }
            localStorage.setItem(state_key, JSON.stringify(state_vars))
            window.location.href = response.authorize_url + "&state=" + b64_state_key
          }
          this.selected_dataset_description = response.description
          // if no dataset period exists, set to DIMENSION so that it matches the 'CREATE' workflow
          this.selected_dataset_period = response.dataSet.period ? response.dataSet.period : 'DIMENSION'

          // read schema for externalUserIdType fields
          this.selected_dataset_items = this.selected_dataset_items.concat(
            response.dataSet.columns.filter(x => "externalUserIdType" in x).map(x => ({
              "name": x.name,
              "description": x.description,
              "data_type": x.dataType,
              "column_type": "DIMENSION",
              "nullable": x.isNullable,
              "pii_type": x.externalUserIdType.hashedPii
            }))
          )

          // read schema for Timestamp field
          this.selected_dataset_items = this.selected_dataset_items.concat(response.dataSet.columns.filter(x => x.isMainEventTime === true).map(x => ({"name": x.name, "description": x.description, "data_type": x.dataType, "column_type": "isMainEventTime", "pii_type":""})))
          // read schema for Dimension fields
          this.selected_dataset_items = this.selected_dataset_items.concat(response.dataSet.columns.filter(x => x.columnType === "DIMENSION").map(x => ({"name": x.name, "description": x.description, "data_type": x.dataType, "column_type": x.columnType, "pii_type":"", "nullable": x.isNullable})).filter(x => x.name !== "user_id" && x.name !== "user_type"))
          // read schema for Metric fields
          this.selected_dataset_items = this.selected_dataset_items.concat(response.dataSet.columns.filter(x => x.columnType === "METRIC").map(x => ({"name": x.name, "description": x.description, "data_type": x.dataType, "column_type": x.columnType, "pii_type":"", "nullable": x.isNullable})))

        }
        catch (e) {
          console.log("ERROR: " + e)
          this.response = e
        }
        this.busy_getting_dataset_definition = false;
      },
  }
}
</script>

<style>
input.largerCheckbox {
  width: 1rem;
  height: 1.25rem;
  position: absolute;
  left: 0;
}
</style>