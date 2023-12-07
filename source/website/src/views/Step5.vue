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
            <b-modal ok-only scrollable id="modal-lg" size="lg" title="Automate uploads to AMC with Amazon S3 Trigger">
              <p>The following steps describe how to create an AWS Lambda function to automatically normalize and upload any new file matching the pattern <b>s3://{{ this.DATA_BUCKET_NAME }}/{{ prefix }}*{{ suffix }}</b> to AMC. Each file will upload into the (previously defined) dataset, <b>{{s3_trigger_dataset_id}}</b>, so be sure that dataset exists and every input file complies with the schema defined for that dataset. This procedure assumes you are using MacOS or Linux and have installed and configured the <a href="https://aws.amazon.com/cli/">AWS Command Line Interface</a> to interact with your AWS account.
              </p>
              <ol>
                <li>
                  Verify the following configurations:
                  <table><!-- //NOSONAR -->
                  <tr>
                    <td>Target dataset:</td>
                    <td>
                      <b-form-input size="sm" v-model="s3_trigger_dataset_id" placeholder="Enter dataset name"></b-form-input>
                    </td>
                  </tr>
                  <tr>
                    <td>S3 key filter prefix: </td>
                    <td>
                      <b-form-input size="sm" v-model="prefix" placeholder="Enter prefix"></b-form-input>
                    </td>
                  </tr>
                  <tr>
                    <td>S3 key filter suffix: </td>
                    <td>
                      <b-form-input size="sm" v-model="suffix" placeholder="Enter suffix"></b-form-input>
                    </td>
                  </tr>
                  </table>
                </li>
                <li>
                  Download the following files:
                  <ul>
                    <li>
                      <b-link @click="saveTrustPolicy">trust_policy.json</b-link>
                    </li>
                    <li>
                      <b-link @click="savePermissionsPolicy">permissions_policy.json</b-link>
                    </li>
                    <li>
                      <b-link @click="saveFile">lambda_function.py</b-link>
                    </li>
                  </ul>
                </li>
                <li>
                  Create the IAM policy by running the following commands. Be sure to specify valid paths to the two policy files downloaded in the previous step.
                  <b-card no-body style="padding-bottom: 0">
                    <b-card-text class="highlight">
                      <b-button size="sm" variant="link" class="clipboard" v-b-tooltip.hover :title=clipboard_title @click="copyText('createRole')" @mouseenter="clipboard_title='Copy to Clipboard'">
                        <b-icon-clipboard></b-icon-clipboard>
                      </b-button>
                      <code id="createRole">$ aws iam create-role --role-name AmcUploaderS3TriggerRole --assume-role-policy-document <b>file://trust_policy.json</b><br>
                        $ aws iam put-role-policy --role-name AmcUploaderS3TriggerRole --policy-name AmcUploaderS3TriggerRolePolicy --policy-document <b>file://permissions_policy.json</b><br>
                        $ ROLE_ARN=$(aws iam get-role --role-name AmcUploaderS3TriggerRole --query 'Role.Arn' --output text)
                      </code>
                    </b-card-text>
                  </b-card>
                </li>
                <li>Create a .zip deployment package with the following commands. Be sure to specify the correct path to <b>lambda_function.py</b>.
                  <b-card no-body style="padding-bottom: 0">
                    <b-card-text class="highlight">
                      <b-button size="sm" variant="link" class="clipboard" v-b-tooltip.hover :title=clipboard_title @click="copyText('createZipFile')" @mouseenter="clipboard_title='Copy to Clipboard'">
                        <b-icon-clipboard></b-icon-clipboard>
                      </b-button>
                      <code id="createZipFile">$ pip3 install --target ./package requests<br>
                        $ cd package<br>
                        $ zip -r ../amc-uploader-s3-trigger.zip .<br>
                        $ cd ..<br>
                        $ zip amc-uploader-s3-trigger.zip lambda_function.py<br>
                        $ rm -rf package<br>
                      </code>
                    </b-card-text>
                  </b-card>
                </li>
                <li>Deploy the Lambda function with the following command.
                  <b-card no-body style="padding-bottom: 0">
                    <b-card-text class="highlight">
                      <b-button size="sm" variant="link" class="clipboard" v-b-tooltip.hover :title=clipboard_title @click="copyText('createFunction')" @mouseenter="clipboard_title='Copy to Clipboard'">
                        <b-icon-clipboard></b-icon-clipboard>
                      </b-button>
                      <code id="createFunction">$ aws lambda create-function --function-name AmcUploaderS3Trigger --runtime python3.10 --role ${ROLE_ARN} --zip-file fileb://amc-uploader-s3-trigger.zip --handler lambda_function.lambda_handler --region
                        {{ AWS_REGION }}
                      </code>
                    </b-card-text>
                  </b-card>
                </li>
                <li>Add an S3 trigger to the Lambda function with the following command:<br>
                  <b-card no-body style="padding-bottom: 0">
                    <b-card-text class="highlight">
                      <b-button size="sm" variant="link" class="clipboard" v-b-tooltip.hover :title=clipboard_title @click="copyText('addS3Trigger')" @mouseenter="clipboard_title='Copy to Clipboard'">
                        <b-icon-clipboard></b-icon-clipboard>
                      </b-button>
                      <code id="addS3Trigger">$ FUNCTION_ARN=$(aws lambda get-function --function-name AmcUploaderS3Trigger --query 'Configuration.FunctionArn' --region {{ AWS_REGION }})<br>
                        $ aws lambda add-permission --region {{ AWS_REGION }} --function-name AmcUploaderS3Trigger --action "lambda:InvokeFunction" --principal s3.amazonaws.com --source-arn arn:aws:s3:::{{ DATA_BUCKET_NAME}} --statement-id s3-trigger<br>
                        $ aws s3api put-bucket-notification-configuration --region {{ AWS_REGION }} --bucket {{ DATA_BUCKET_NAME}} --notification-configuration '{
                        "LambdaFunctionConfigurations": [
                        {
                        "LambdaFunctionArn": '${FUNCTION_ARN}',
                        "Events": ["s3:ObjectCreated:*"],
                        "Filter": {
                        "Key": {
                        "FilterRules": [
                        {
                        "Name": "prefix",
                        "Value": "{{ prefix }}"
                        },
                        {
                        "Name": "suffix",
                        "Value": "{{ suffix }}"
                        }
                        ]
                        }
                        }
                        }
                        ]
                        }'
                      </code>
                    </b-card-text>
                  </b-card>
                </li>
                <li>To test this automation, copy a file matching the pattern <b>{{ prefix }}*{{ suffix }}</b> to <b>s3://{{ DATA_BUCKET_NAME }}/</b> then go to Step 6 to monitor the upload. If you do not see the upload, look for errors in the Amazon CloudWatch log for the AmcUploaderS3Trigger Lambda function.</li>
              </ol>
              <hr>
              <h5>Clean up:</h5>
              Run the following commands to clean up and remove the resources  created above:<br>
              <b-card no-body style="padding-bottom: 0">
                <b-card-text class="highlight">
                  <b-button size="sm" variant="link" class="clipboard" v-b-tooltip.hover :title=clipboard_title @click="copyText('cleanup')" @mouseenter="clipboard_title='Copy to Clipboard'">
                    <b-icon-clipboard></b-icon-clipboard>
                  </b-button>
                  <code id="cleanup">$ rm amc-uploader-s3-trigger.zip lambda_function.py permissions_policy.json trust_policy.json<br>
                    $ aws lambda delete-function --function-name AmcUploaderS3Trigger --region {{ AWS_REGION }}<br>
                    $ aws iam delete-role-policy --policy-name AmcUploaderS3TriggerRolePolicy --role-name AmcUploaderS3TriggerRole<br>
                    $ aws iam delete-role --role-name AmcUploaderS3TriggerRole<br>
                  </code>
                </b-card-text>
              </b-card>
            </b-modal>
            <h3>Confirm Details</h3>
            <b-row>
              <b-col sm="7">
                <p v-if="isValid">
                  Click <b-link @click="onSubmit">Submit</b-link> to record this dataset in AMC.
                  <br>
                  To setup this request as an Amazon S3 triggered Lambda function, click <b-link v-b-modal.modal-lg>here</b-link>.
                </p>
                <p v-else class="text-danger">
                  Invalid dataset. Verify that your dataset definition is complete.
                </p>
              </b-col>
              <b-col sm="3" text-align="right">
                <button type="submit" class="btn btn-outline-primary mb-2" @click="$router.push({path: '/step4'})">
                  Previous
                </button> &nbsp;
                <button type="submit" class="btn btn-primary mb-2" :disabled="!isValid || isBusy || disable_submit" @click="onSubmit">
                  Submit
                  <b-spinner v-if="isBusy" style="vertical-align: sub" small label="Spinning"></b-spinner>
                </button>
              </b-col>
            </b-row>
            <b-row>
              <b-col cols="11">
                <h5>Input files:</h5>
                <div v-if="s3key !== ''">
                  <ul>
                    <li v-for="item in s3key.split(',')" :key="item">
                      {{ "s3://" + DATA_BUCKET_NAME + "/" + item }}
                    </li>
                  </ul>
                </div>
                <div v-else>
                  <br>
                </div>
                <h5>Destinations:</h5>
                <ul>
                  <li v-for="endpoint in destination_endpoints" :key="endpoint">
                    <div v-if="endpoint_request(endpoint).is_busy">
                      {{ endpoint }} <b-spinner small></b-spinner>
                    </div>
                    <div v-else>
                      <div v-if="!endpoint_request(endpoint).status">
                        {{ endpoint }} {{ endpoint_request(endpoint).status }}
                      </div>
                      <div v-else-if="endpoint_request(endpoint).status.toLowerCase().includes('error')">
                        {{ endpoint }} <p class="text-danger" style="display:inline">
                          <br>{{ endpoint_request(endpoint).status }}
                        </p>
                      </div>
                      <div v-else-if="JSON.stringify(endpoint_request(endpoint).status).length > 0">
                        {{ endpoint }} (<b-link variant="link" @click="onClickMonitor(endpoint)">
                          monitor
                        </b-link>)
                      </div>
                    </div>
                  </li>
                </ul>
                <br>
                <h5>Dataset Attributes:</h5>
                <b-table
                  small
                  outlined
                  :items="dataset.other_attributes"
                  thead-class="hidden_header"
                  show-empty
                >
                </b-table>
                <template #empty="scope">
                  {{ scope.emptyText }}
                </template>
              </b-col>
            </b-row>
            <b-row>
              <b-col cols="10">
                <h5>Columns:</h5>
                <div v-if="deleted_columns.length > 0">
                  Excluding columns {{ deleted_columns }} in {{ s3key }} from upload.
                </div>
                <b-table
                  v-if="dataset.columns && dataset.columns.length > 0"
                  small
                  outlined
                  :fields="column_fields"
                  :items="dataset.columns"
                >
                </b-table>
                <b-table
                  v-else
                  small
                  outlined
                  :items="dataset.columns"
                  show-empty
                ></b-table>
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
    name: "Step5",
    components: {
      Header, Sidebar
    },
    data() {
      return {
        s3_trigger_dataset_id: "",
        prefix: "incoming/",
        suffix: ".json",
        clipboard_title: "Copy to Clipboard",
        disable_submit: false,
        destination_fields: [
          {key: 'endpoint', label: 'AMC Endpoint', sortable: true},
          {key: 'actions', label: 'Actions'},
        ],
        column_fields: ['name', 'description', 'dataType', 'columnType', 'nullable', 'isMainUserId', 'isMainUserIdType', 'isMainUserId', 'externalUserIdType.type','externalUserIdType.identifierType','isMainEventTime'],
        dataset_fields: [{key: '0', label: 'Name'}, {key: '1', label: 'Value'}],
        endpoint_request_state: [],
        isStep5Active: true,
        response: '',
        apiName: 'amcufa-api'
      }
    },
    computed: {
      ...mapState(['deleted_columns', 'dataset_definition', 's3key', 'selected_dataset', 'destination_endpoints']),
      isBusy() {
        // if any endpoint is busy then return true
        return this.endpoint_request_state.filter(x => x.is_busy === true).length > 0
      },
      isValid() {
        return !(this.s3key === '' || this.destination_endpoints.length === 0 || !this.dataset.columns || this.dataset.columns.length === 0)
      },
      encryption_key() {
        if (this.CUSTOMER_MANAGED_KEY === "") {
          return "default"
        } else {
          return this.CUSTOMER_MANAGED_KEY
        }
      },
      pii_fields() {
         return (this.dataset.columns.filter(x => x.externalUserIdType && x.externalUserIdType.identifierType).map(x => (new Object( {'column_name':x.name, 'pii_type': x.externalUserIdType.identifierType}))))
      },
      timestamp_column_name() {
        const timestamp_column = this.dataset.columns.filter(x => x.isMainEventTime).map(x => x.name)
        // The Glue ETL job requires timestamp_column_name to be an empty string
        // for all DIMENSION datasets.
        const dataset_type = this.dataset_definition['dataSetType']
        if (dataset_type === 'FACT' && timestamp_column && timestamp_column.length > 0)
          return timestamp_column[0]
        else
          return ''
      },
      dataset() {
        let {columns, ...other_attributes} = this.dataset_definition
        other_attributes['encryption_mode'] = this.ENCRYPTION_MODE
        return {"columns": columns, "other_attributes": Object.entries(other_attributes)}
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
      this.endpoint_request_state = this.destination_endpoints.map(x => ({
        "endpoint": x,
        "status": null,
        "is_busy": false
      }))
      this.s3_trigger_dataset_id = this.dataset_definition.dataSetId
    },
    methods: {
      copyText(elementId) {
        const element = document.getElementById(elementId);
        navigator.clipboard.writeText(element.textContent.replace('$ ', '').replaceAll('$ ', '\n'));
        this.clipboard_title = "Copied!"
      },
      onClickMonitor(endpoint) {
        this.$store.commit('updateAmcMonitor', endpoint)
        this.$router.push({path: '/step6'})
      },
      endpoint_request(endpoint) {
        const i =  this.endpoint_request_state.findIndex(x => x.endpoint === endpoint)
        if (i !== null) {
          return this.endpoint_request_state[i]
        }
      },
      onSubmit() {
        this.disable_submit = true
        // Send a request to create datasets to each endpoint in parallel.
        if (this.selected_dataset === null) {
          this.create_datasets(this.destination_endpoints)
        } else {
          this.check_dataset_exists(this.destination_endpoints, this.selected_dataset)
        }
        console.log("Finished defining datasets.")
        // Wait for all those requests to complete, then start the glue job.
        this.start_amc_transformation('POST', 'start_amc_transformation', {
          'sourceBucket': this.DATA_BUCKET_NAME,
          // 'sourceKey' is added in start_amc_transformation().
          'outputBucket': this.ARTIFACT_BUCKET_NAME,
          'piiFields': JSON.stringify(this.pii_fields),
          'deletedFields': JSON.stringify(this.deleted_columns),
          'timestampColumn': this.timestamp_column_name,
          'datasetId': this.dataset_definition.dataSetId,
          'period': this.dataset_definition.period,
          'countryCode': this.dataset_definition.countryCode,
          'fileFormat': this.dataset_definition.fileFormat,
          'destination_endpoints': JSON.stringify(this.destination_endpoints)
        })
      },
      check_dataset_exists(destination_endpoints, dataset_id) {
        // set busy status to show spinner for each endpoint
        this.endpoint_request_state = this.destination_endpoints.map(x => ({
          "endpoint": x,
          "status": "",
          "is_busy": true
        }))
        destination_endpoints.forEach(endpoint => {
          this.send_request('POST', 'describe_dataset', {
            'body': this.dataset_definition,
            'dataSetId': dataset_id,
            'destination_endpoint': endpoint
          }).then(result => {
            console.log("describe_dataset() result for " + endpoint + ":")
            console.log(JSON.stringify(result))
            const j = this.endpoint_request_state.findIndex(x => x.endpoint === endpoint)
            if (j != null) {
              this.endpoint_request_state[j].is_busy = false
              this.endpoint_request_state[j].status = JSON.stringify(result)
            }
          })
        })
      },
      create_datasets(destination_endpoints) {
        // set busy status to show spinner for each endpoint
        this.endpoint_request_state = this.destination_endpoints.map(x => ({
          "endpoint": x,
          "status": "",
          "is_busy": true
        }))
        destination_endpoints.forEach(endpoint => {
          this.send_request('POST', 'create_dataset', {
            'body': this.dataset_definition,
            'destination_endpoint': endpoint
          }).then(result => {
            console.log("create_dataset() result for " + endpoint + ":")
            console.log(JSON.stringify(result))
            const j = this.endpoint_request_state.findIndex(x => x.endpoint === endpoint)
            if (j != null) {
              this.endpoint_request_state[j].is_busy = false
              this.endpoint_request_state[j].status = JSON.stringify(result)
            }
          })
        })
      },
      async send_request(method, resource, data) {
        this.modal_title = ''
        this.response = ''
        console.log("sending " + method + " " + resource + " " + JSON.stringify(data))
        let requestOpts = {
          headers: {'Content-Type': 'application/json'},
          body: data
        };
        try {
          return await this.$Amplify.API.post(this.apiName, resource, requestOpts)
        } catch (e) {
          console.log(e.toString())
          return e.toString()
        }
      },
      async start_amc_transformation(method, resource, data) {
        try {
          // Start Glue ETL job now that the dataset has been accepted by AMC
          let s3keysList = this.s3key.split(',').map((item) => item.trim())
          for (let key of s3keysList) {
            data["sourceKey"] = key
            console.log("Starting Glue ETL job for s3://" + this.DATA_BUCKET_NAME + "/" + key)
            let requestOpts = {
              headers: {'Content-Type': 'application/json'},
              body: data
            };
            console.log("POST " + resource + " " + JSON.stringify(requestOpts))
            this.response = await this.$Amplify.API.post(this.apiName, resource, requestOpts);
            console.log("Started Glue ETL job")
            console.log(JSON.stringify(this.response))
          }
        } catch (e) {
          console.log(e.toString())
        }
      },
      savePermissionsPolicy() {
        const account_id = "*"
        const api_name = this.API_ENDPOINT.split("https://")[1].split(".")[0]
        const permissions_policy = 
            "{\n" +
            "    \"Version\": \"2012-10-17\",\n" +
            "    \"Statement\": [\n" +
            "        {\n" +
            "            \"Action\": [\n" +
            "                \"execute-api:Invoke\"\n" +
            "            ],\n" +
            "            \"Resource\": [\n" +
            "                \"arn:aws:execute-api:" + this.AWS_REGION + ":" + account_id + ":" + api_name + "/api/GET/version\",\n" +
            "                \"arn:aws:execute-api:" + this.AWS_REGION + ":" + account_id + ":" + api_name + "/api/POST/start_amc_transformation\"\n" +
            "            ],\n" +
            "            \"Effect\": \"Allow\"\n" +
            "        },\n" +
            "        {\n" +
            "            \"Effect\": \"Allow\",\n" +
            "            \"Action\": \"logs:CreateLogGroup\",\n" +
            "            \"Resource\": \"arn:aws:logs:" + this.AWS_REGION + ":" + account_id + ":*\"\n" +
            "        },\n" +
            "        {\n" +
            "            \"Effect\": \"Allow\",\n" +
            "            \"Action\": [\n" +
            "                \"logs:CreateLogStream\",\n" +
            "                \"logs:PutLogEvents\"\n" +
            "            ],\n" +
            "            \"Resource\": [\n" +
            "                \"arn:aws:logs:" + this.AWS_REGION + ":" + account_id + ":log-group:/aws/lambda/*:*\"\n" +
            "            ]\n" +
            "        }\n" +
            "    ]\n" +
            "}"
        
        const blob = new Blob([permissions_policy], {type: 'text/plain'});
        const e = document.createEvent('MouseEvents'),
            a = document.createElement('a');
        a.download = "permissions_policy.json";
        a.href = window.URL.createObjectURL(blob);
        a.dataset.downloadurl = ['text/plain', a.download, a.href].join(':');
        e.initEvent('click', true, false, window, 0, 0, 0, 0, 0, false, false, false, false, 0, null); //NOSONAR
        a.dispatchEvent(e);
      },
      saveTrustPolicy() {
        const trust_policy = 
            "{\n" +
            "  \"Version\": \"2012-10-17\",\n" +
            "  \"Statement\": {\n" +
            "    \"Effect\": \"Allow\",\n" +
            "    \"Principal\": {\n" +
            "      \"Service\": \"lambda.amazonaws.com\"\n" +
            "    },\n" +
            "    \"Action\": \"sts:AssumeRole\"\n" +
            "  }\n" +
            "}"
        
        const blob = new Blob([trust_policy], {type: 'text/plain'});
        const e = document.createEvent('MouseEvents'),
            a = document.createElement('a');
        a.download = "trust_policy.json";
        a.href = window.URL.createObjectURL(blob);
        a.dataset.downloadurl = ['text/plain', a.download, a.href].join(':');
        e.initEvent('click', true, false, window, 0, 0, 0, 0, 0, false, false, false, false, 0, null); //NOSONAR
        a.dispatchEvent(e);
      },
      saveFile() {
        const sigv4_post_python_code = 
            "#Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.\n" +
            "#SPDX-License-Identifier: Apache-2.0\n" +
            "\n" +
            "import sys, os, base64, datetime, hashlib, hmac, logging\n" +
            "import requests\n" + 
            "\n" + 
            "# format log messages like this:\n" +
            "formatter = logging.Formatter(\n" +
            "    \"{%(pathname)s:%(lineno)d} %(levelname)s - %(message)s\"\n" +
            ")\n" +
            "handler = logging.StreamHandler()\n" +
            "handler.setFormatter(formatter)\n" +
            "\n" +
            "# Remove the default logger in order to avoid duplicate log messages\n" +
            "# after we attach our custom logging handler.\n" +
            "logging.getLogger().handlers.clear()\n" +
            "logger = logging.getLogger()\n" +
            "logger.setLevel(logging.INFO)\n" +
            "logger.addHandler(handler)\n" +
            "\n" +
            "# Key derivation functions. See:\n" +
            "# http://docs.aws.amazon.com/general/latest/gr/signature-v4-examples.html#signature-v4-examples-python\n" +
            "def sign(key, msg):\n" +
            "    return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()\n" +
            "\n" +
            "def get_signature_key(key, date_stamp, region_name, service_name):\n" +
            "    k_date = sign(('AWS4' + key).encode('utf-8'), date_stamp)\n" +
            "    k_region = sign(k_date, region_name)\n" +
            "    k_service = sign(k_region, service_name)\n" +
            "    k_signing = sign(k_service, 'aws4_request')\n" +
            "    return k_signing\n" +
            "\n" +
            "\n" +
            "def lambda_handler(event, context):\n" +
            "    logger.info(\"We got the following event:\\n\")\n" +
            "    logger.info(\"event:\\n {s}\".format(s=event))\n" +
            "    logger.info(\"context:\\n {s}\".format(s=context))\n" +
            "\n" +
            "    method = 'POST'\n" +
            "    service = 'execute-api'\n" +
            "    host = '" + this.API_ENDPOINT.split('/')[2] + "'\n" +
            "    region = '" + this.AWS_REGION + "'\n" +
            "    endpoint = '" + this.API_ENDPOINT + "start_amc_transformation'\n" +
            "    # POST requests use a content type header.\n" +
            "    content_type = 'application/json'\n" + 
            "    source_key = event['Records'][0]['s3']['object']['key']\n" + 
            "    \n" +
            "    # POST data\n" +
            "    body_data = '{' + \\\n" +
            "    '\"sourceBucket\": \"" + this.DATA_BUCKET_NAME + "\",' + \\\n" +
            "    '\"outputBucket\": \"" + this.ARTIFACT_BUCKET_NAME + "\",' + \\\n" +
            "    '\"piiFields\": \"" + JSON.stringify(this.pii_fields).replace(/"/g, '\\\\"') + "\",' + \\\n" +
            "    '\"deletedFields\": \"" + JSON.stringify(this.deleted_columns).replace(/"/g, '\\\\"') + "\",' + \\\n" +
            "    '\"timestampColumn\": \"" + this.timestamp_column_name + "\",' + \\\n" +
            "    '\"datasetId\": \"" + this.s3_trigger_dataset_id + "\",' + \\\n" +
            "    '\"period\": \"" + this.dataset_definition.period + "\",' + \\\n" +
            "    '\"fileFormat\": \"" + this.dataset_definition.fileFormat + "\",' + \\\n" +
            "    '\"countryCode\": \"" + this.dataset_definition.countryCode + "\",' + \\\n" +
            "    '\"destination_endpoints\": \"" + JSON.stringify(this.destination_endpoints).replace(/"/g, '\\\\"') + "\",' + \\\n" +
            "    '\"sourceKey\": \"' + source_key + '\"}'\n" +
            "    \n" +
            "    # Read AWS access key from env. variables or configuration file. Best practice is NOT\n" +
            "    # to embed credentials in code.\n" +
            "    access_key = os.environ.get('AWS_ACCESS_KEY_ID')\n" +
            "    secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')\n" +
            "    session_token = os.environ.get('AWS_SESSION_TOKEN')\n" +
            "    \n" +
            "    if access_key is None or secret_key is None:\n" +
            "        print('No access key is available.')\n" +
            "        sys.exit()\n" +
            "    \n" +
            "    # Create a date for headers and the credential string\n" +
            "    t = datetime.datetime.utcnow()\n" +
            "    amzdate = t.strftime('%Y%m%dT%H%M%SZ')\n" +
            "    datestamp = t.strftime('%Y%m%d') # Date w/o time, used in credential scope\n" +
            "    \n" +
            "    # ************* TASK 1: CREATE A CANONICAL REQUEST *************\n" +
            "    # https://docs.aws.amazon.com/IAM/latest/UserGuide/create-signed-request.html\n" +
            "    \n" +
            "    # Step 1 is to define the verb (GET, POST, etc.)--already done.\n" +
            "    \n" +
            "    # Step 2: Create canonical URI--the part of the URI from domain to query \n" +
            "    # string (use '/' if no path)\n" +
            "    canonical_uri = '/api/start_amc_transformation' \n" +
            "    \n" +
            "    # Step 3: Create the canonical query string. In this example (a GET request),\n" +
            "    # request parameters are in the query string. Query string values must\n" +
            "    # be URL-encoded (space=%20). The parameters must be sorted by name.\n" +
            "    # For this example, the query string is pre-formatted in the request_parameters variable.\n" +
            "    canonical_querystring = ''\n" +
            "    \n" +
            "    # Step 4: Create the canonical headers and signed headers. Header names\n" +
            "    # must be trimmed and lowercase, and sorted in code point order from\n" +
            "    # low to high. Note that there is a trailing \\n.\n" +
            "    canonical_headers = 'host:' + host + '\\n' + 'x-amz-date:' + amzdate + '\\n' + 'x-amz-security-token:' + session_token + '\\n'\n" +
            "    \n" +
            "    # Step 5: Create the list of signed headers. This lists the headers\n" +
            "    # in the canonical_headers list, delimited with \";\" and in alpha order.\n" +
            "    # Note: The request can include any headers; canonical_headers and\n" +
            "    # signed_headers lists those that you want to be included in the \n" +
            "    # hash of the request. \"Host\" and \"x-amz-date\" are always required.\n" +
            "    signed_headers = 'host;x-amz-date;x-amz-security-token'\n" +
            "    \n" +
            "    # Step 6: Create payload hash. In this example, the payload (body of\n" +
            "    # the request) contains the request parameters.\n" +
            "    payload_hash = hashlib.sha256(body_data.encode('utf-8')).hexdigest()\n" +
            "    \n" +
            "    # Step 7: Combine elements to create canonical request\n" +
            "    canonical_request = method + '\\n' + canonical_uri + '\\n' + canonical_querystring + '\\n' + canonical_headers + '\\n' + signed_headers + '\\n' + payload_hash\n" +
            "    \n" +
            "    # ************* TASK 2: CREATE THE STRING TO SIGN*************\n" +
            "    # Match the algorithm to the hashing algorithm you use, either SHA-1 or\n" +
            "    # SHA-256 (recommended)\n" +
            "    algorithm = 'AWS4-HMAC-SHA256'\n" +
            "    credential_scope = datestamp + '/' + region + '/' + service + '/' + 'aws4_request'\n" +
            "    string_to_sign = algorithm + '\\n' +  amzdate + '\\n' +  credential_scope + '\\n' +  hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()\n" +
            "    \n" +
            "    # ************* TASK 3: CALCULATE THE SIGNATURE *************\n" +
            "    # Create the signing key using the function defined above.\n" +
            "    signing_key = get_signature_key(secret_key, datestamp, region, service)\n" +
            "    \n" +
            "    # Sign the string_to_sign using the signing_key\n" +
            "    signature = hmac.new(signing_key, (string_to_sign).encode('utf-8'), hashlib.sha256).hexdigest()\n" +
            "    \n" +
            "    # ************* TASK 4: ADD SIGNING INFORMATION TO THE REQUEST *************\n" +
            "    # The signing information can be either in a query string value or in \n" +
            "    # a header named Authorization. This code shows how to use a header.\n" +
            "    # Create authorization header and add to request headers\n" +
            "    authorization_header = algorithm + ' ' + 'Credential=' + access_key + '/' + credential_scope + ', ' +  'SignedHeaders=' + signed_headers + ', ' + 'Signature=' + signature\n" +
            "    \n" +
            "    # The request can include any headers, but MUST include \"host\", \"x-amz-date\", \n" +
            "    # and (for this scenario) \"Authorization\". \"host\" and \"x-amz-date\" must\n" +
            "    # be included in the canonical_headers and signed_headers, as noted\n" +
            "    # earlier. Order here is not significant.\n" +
            "    # Python note: The 'host' header is added automatically by the Python 'requests' library.\n" +
            "    headers = {'Authorization': authorization_header, 'x-amz-date': amzdate, 'x-amz-security-token': session_token, 'content-type': content_type}\n" +
            "    \n" +
            "    # ************* SEND THE REQUEST *************\n" +
            "    print('\\nBEGIN REQUEST++++++++++++++++++++++++++++++++++++')\n" +
            "    print('Request URL = ' + endpoint)\n" +
            "    print('request_parameters = ' + str(body_data))\n" +
            "    r = requests.post(endpoint, data=body_data, headers=headers)\n" +
            "    \n" +
            "    print('\\nRESPONSE++++++++++++++++++++++++++++++++++++')\n" +
            "    print('Response code: %d\\n' % r.status_code)\n" +
            "    print(r.text)"
        
        const blob = new Blob([sigv4_post_python_code], {type: 'text/plain'});
        const e = document.createEvent('MouseEvents'),
            a = document.createElement('a');
        a.download = "lambda_function.py";
        a.href = window.URL.createObjectURL(blob);
        a.dataset.downloadurl = ['text/plain', a.download, a.href].join(':');
        e.initEvent('click', true, false, window, 0, 0, 0, 0, 0, false, false, false, false, 0, null); //NOSONAR
        a.dispatchEvent(e);
      },
    }
  }
</script>

<style>
.hidden_header {
  display: none;
}
.clipboard {
  position: absolute;
  top: 0;
  right: 0;
  color: black;
}
.highlight {
  margin-bottom: 0;
  padding: 1rem;
  background-color: #f7f7f9;
}
</style>
