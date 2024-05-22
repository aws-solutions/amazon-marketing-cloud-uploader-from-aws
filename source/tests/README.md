## Instructions for Running Unit Tests
---

The following steps can be done to run the unit tests contained in the `tests` directory:

1. Open a terminal window and navigate to the project `/deployment` directory.
2. Run this command in the terminal:
```shell
$ sh run-unit-tests.sh
```
3. A new virtual environment should now be created with the script with test environment variables. The tests will also execute.
4. A coverage report will be generated for SonarQube and can be viewed in the `tests/coverage-reports` directory.


#### From the project test directory

Unit Test
```shell
$ ./run_test.sh --run_unit_test
----
$ ./run_test.sh -h
-rut, --run_unit_test    Run Unit Test.
        [--test_file-name TEST_FILE_NAME] (e.g `test_api.py` or `test_api.py::test_get_etl_jobs` for a single test.)
        [--aws-region AWS_REGION] (optional, Default is us-east-1.))
```

Integration Test
```shell
$ ./run_test.sh --run_integ_test
-------
$ ./run_test.sh -h
 -rit, --run_integ_test    Run Integ Test.
        [--stack-name STACK_NAME] (An existing deployed stack with code changes/version to run integration test on.)
        [--aws-region AWS_REGION]
        [--aws-default-profile AWS_DEFAULT_PROFILE] (AWS default profiles with creds) (Required if --aws-access-key-id and --aws-secret-access-key is not provided)
        [--aws-access-key-id AWS_ACCESS_KEY_ID] [--aws-secret-access-key AWS_SECRET_ACCESS_KEY] (Required if --aws-default-profile is not provided)
        [--data-bucket-name DATA_BUCKET_NAME] (Optional if --test-params-secret-name is provided )
        [--amc-instance-id AMC_INSTANCE_ID] (Optional if --test-params-secret-name is provided )
        [--amc-advertiser-id AMC_ADVERTISER_ID] (Optional if --test-params-secret-name is provided )
        [--amc-marketplace-id AMC_MARKETPLACE_ID] (Optional if --test-params-secret-name is provided )
        [--auth-code AUTH_CODE] (Amazon API auth code) (Optional if --refresh-token is provided) (Optional, but not eligible with --test-params-secret-name as refresh token is required )
        [--client-id CLIENT_ID] (Optional if --test-params-secret-name is provided )
        [--client-secret CLIENT_SECRET] (Optional if --test-params-secret-name is provided )
        [--refresh-token REFRESH_TOKEN] (Amazon API Refresh token) (Required, if --auth-code is not provided.) (Optional if --test-params-secret-name is provided )
        [--test-data-upload-account-id TEST_DATA_UPLOAD_ACCOUNT_ID] (Optional if --test-params-secret-name is provided )
        [--test-user-arn TEST_USER_ARN] (Optional, if not provided '/root' user will be used, with stack account id) (It also assumes user has admin priviledges.)
        [--aws-xray-sdk-enabled] (Optional, Default is false)
        [--boto-config] (Optional, Default is '{"region_name": "AWS_REGION"}')
        [--version] (Optional, Default is 0.0.0)
        [--solution-name] (Optional, Default is Amcufa Integration Test)
        [--test-params-secret-name] (Optional, Run integ test with variables stored in stack account aws secret manager.)
            ## secret-id amcufa_integ_test_secret
            ## secret-value sample, all variables are required.
                {
                    "instance_id": "abcd",
                    "advertiser_id": "ABCD12345",
                    "marketplace_id": "ABCD",
                    "data_upload_account_id": "1234567889",
                    "client_id": "amzn1.XXXXXXXXXX",
                    "client_secret": "amzn1.XXXXXXX",
                    "refresh_token": "Atzr|XXXXXXXXX",
                    "data_bucket_name": "s3-source-bucket",
                    "amc_endpoint_url": "https://some-api-endpoint.us-east-1.amazonawa.com/beta",
                }
        [--test-params-secret-name-region] (Optional, Default to us-east-1.)
        [--deep-test] (Optional, Default to false.) (100% test coverage, but set to false for tests optimization to prevent timeouts.)
```
