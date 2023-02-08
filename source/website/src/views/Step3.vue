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
          v-model="showSchemaError"
          variant="danger"
          dismissible
        >
          Schemas must match for each file when multi-uploading.
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
          variant="danger"
          dismissible
          fade
          :show="showImportErrors"
          @dismissed="showImportErrors=false"
        >
          {{ errorImportMessage }}
        </b-alert>
        <b-row style="text-align: left">
          <b-col cols="2">
            <Sidebar :is-step3-active="true" />
          </b-col>
          <b-col cols="10">
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
              <b-col sm="3" align="right" class="row align-items-end">
                <button type="submit" class="btn btn-outline-primary mb-2" @click="$router.push({path: '/step2'})">
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
              :busy="isBusy"
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
              <b-col></b-col>
              <b-col sm="4" align="right" class="row align-items-end">
                <b-button v-b-tooltip.hover type="submit" title="Export column schema" variant="outline-primary" @click="onExport">
                  Export
                </b-button> &nbsp;
                <b-button v-b-tooltip.hover type="submit" title="Import column schema" variant="outline-primary" @click="onBrowseImports">
                  Import
                </b-button>&nbsp;
                <b-button type="submit" variant="outline-secondary" @click="onReset">
                  Reset
                </b-button>
                <b-form-file id="importFile" ref="file" accept="application/json" type="file" style="visibility: hidden" @change="onImport" />
              </b-col>
            </b-row>
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
    name: "Step3",
    components: {
      Header, Sidebar
    },
    data() {
      return {
        new_dataset_definition: {},
        isBusy: false,
        showServerError: false,
        showSchemaError: false,
        showMissingDataAlert: false,
        showIncompleteFieldsError: false,
        showIncompleteTimeFieldError: false,
        showUnexpectedTimeFieldError: false,
        showUserIdWarning: false,
        userIdWarningMessage: "Do not include user_id and user_type columns in data files containing hashed identifiers. These columns are used by AMC when a match is found in a hashed record.",
        items: [],
        columns: [],
        content_type: "",
        showImportErrors: false,
        errorImportMessage: "",
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
        isStep3Active: true
      }
    },
    computed: {
      ...mapState(['deleted_columns','dataset_definition', 's3key', 'step3_form_input']),
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
      if (!this.s3key) {
        this.showMissingDataAlert = true
      }
      else if (!this.step3_form_input.length) {
        this.send_request('POST', 'get_data_columns', {'s3bucket': this.DATA_BUCKET_NAME, 's3key':this.s3key})
      } else {
        this.items = this.step3_form_input
      }
    },
    methods: {
      deleteColumn(column_name) {
        this.items = this.items.filter(x => x.name !== column_name)
        this.deleted_columns.push(column_name)
        this.$store.commit('updateDeletedColumns', this.deleted_columns)
        console.log("deleted_columns: " + this.deleted_columns)
      },
      onReset() {
        this.$store.commit('updateDeletedColumns', [])
        this.send_request('POST', 'get_data_columns', {'s3bucket': this.DATA_BUCKET_NAME, 's3key':this.s3key})
        this.column_type_options.forEach(x => x.disabled = false)
        this.pii_type_options.forEach(x => x.disabled = false)
      },
      onExport() {
        if (!this.validateForm()) return
        const a = document.createElement("a");
        const file = new Blob([JSON.stringify({"columns": this.items })], { type:  "application/json"});
        a.href = URL.createObjectURL(file);
        a.download = "amcufa_exported_schema_" + Date.now() + ".json";
        a.click();
        console.log("Schema Exported: ".concat(JSON.stringify({"columns": this.items })))
      },
      onBrowseImports(){
        if (confirm("WARNING: This will reset the columns!")) {
          document.getElementById('importFile').click()
        }
      },
      showImportAlert(errorMessage){
        this.errorImportMessage = errorMessage
        this.showImportErrors = true
      },
      onImport(e){
          let files = e.target.files || e.dataTransfer.files;
          if (!files.length) return;
          let reader = new FileReader();
          reader.onload = e => {
            console.log("Imported schema: ".concat(e.target.result))
            let importJson = null;
            try {
              importJson = JSON.parse(e.target.result);
            } catch(e) { 
              console.log(e)
              this.showImportAlert("Invalid Schema: Json file is invalid");
              return 
            } finally {
              this.$refs['file'].reset()
            }

            if(importJson.constructor != Object){
              this.showImportAlert("Invalid Schema: Expecting a dictionary.");
              return
            }
            if (!Object.keys(importJson).length){
              this.showImportAlert("Invalid Schema: Json file is empty.");
              return
            }
            if (!("columns" in importJson)){
              this.showImportAlert("Invalid Schema: columns key is required in imported schema.");
              return
            }
            if (importJson.columns.constructor.name != "Array"){
              this.showImportAlert("Invalid Schema: Expecting an array type for columns key.");
              return
            }
            if (!importJson.columns.length){
              this.showImportAlert("Invalid Schema: columns key is empty.");
              return
            }

            let valid_keys = ["name", "description", "data_type", "column_type", "pii_type", "nullable"]
            for (var column_index in importJson.columns){
                let column = importJson.columns[column_index]
                for (var key in column){
                if (!valid_keys.includes(key)){
                  this.showImportAlert("Invalid Schema: Only these valid column keys ".concat(valid_keys).concat(" are required."));
                  return
                } 
              }
            }
           
            this.isBusy = true;
            this.column_type_options.forEach(x => x.disabled = false)
            this.pii_type_options.forEach(x => x.disabled = false)
            this.items = importJson.columns.map(x => {return {
                "name": x.name,
                "description": x.description.charAt(0).toUpperCase() + x.description.replace(/[^a-zA-Z0-9]/g, ' ').slice(1),
                "data_type": x.data_type,
                "column_type": x.column_type,
                "pii_type": x.pii_type,
                "nullable": x.nullable
              }
            })
            this.$store.commit('saveStep3FormInput', this.items)
            this.isBusy = false;
            this.showImportErrors = false
            console.log("Schema Imported.")
          };
          reader.readAsText(files[0]);
      },
      validateForm() {
        // All fields must have values.
        if (this.incompleteFields.errorItems.length > 0) {
          this.showIncompleteFieldsError = true
          return false
        } else {
          this.showIncompleteFieldsError = false
        }
        // FACT datasets must have a field designated as the main event time.
        if (this.dataset_definition.dataSetType === 'FACT'
            && this.mainEventTimeSelected === false) {
          this.showIncompleteTimeFieldError = true
          return false
        } else {
          this.showIncompleteTimeFieldError = false
        }
        // DIMENSION datasets must not have a field designated as the main event time.
        if (this.dataset_definition.dataSetType === 'DIMENSION'
            && this.mainEventTimeSelected === true) {
          this.showUnexpectedTimeFieldError = true
          return false
        } else {
          this.showUnexpectedTimeFieldError = false
        }
        return true
      },
      onSubmit() {
        if (!this.validateForm()) return
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
        this.$router.push({path: '/step4'})
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
      async send_request(method, resource, data) {
        console.log("sending " + method + " " + resource + " " + JSON.stringify(data))
        const apiName = 'amcufa-api'
        let response = ""
        this.isBusy = true;
        try {
          if (method === "GET") {
            response = await this.$Amplify.API.get(apiName, resource);
          } else if (method === "POST") {
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
          console.log(JSON.stringify(this.items))
        }
        catch (e) {
          if(e.response.status === 400) this.showSchemaError = true;
          else this.showServerError = true;

          console.log("ERROR: " + e.response.data.message)
          this.isBusy = false;
          this.results = e.response.data.message
        }
        this.isBusy = false;
      }
    }
  }
</script>
