# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.11] - 2025-04-11

### Security

- Updated npm dependencies

## [3.0.10] - 2025-03-14

### Security

- Updated npm dependencies

## [3.0.9] - 2025-03-03

### Security

- Updated python and npm dependencies

## [3.0.8] - 2024-11-25

### Security

- Updated npm dependencies

## [3.0.7] - 2024-11-01

### Changed

- Set awswrangler to version 3.9.1 for compatibility

## [3.0.6] - 2024-10-30

### Security

- Vulnerability patches to address CVE-2024-21536.

## [3.0.5] - 2024-09-17

### Security

- Vulnerability patches to address CVE-2024-45296, CVE-2024-43788, CVE-2024-4067, and CVE-2024-43799.

## [3.0.4] - 2024-08-20

### Security

- Update axios to version 1.7.4 to address vulnerability CVE-2024-39338.

## [3.0.3] - 2024-08-02

### Security

- Update fast-xml-parser to version 4.4.1 to address vulnerability CVE-2024-41818.

## [3.0.2] - 2024-07-26

### Changed

- Remove Android (AAID) and iOS (IDFA) options for Mobile Ad Id (MAID) because MAID now supersedes AAID and IDFA.

### Fixed

- Avoid dropping Country Code when LiveRamp, Experian, or Mobile Ad IDs are used for identity resolution instead of hashed PII.
- Upload with manifest files rather than individual files so that the partitions of large files do not overwrite each other when using the FULL_REPLACE update strategy.
- Fix error parsing the Glue ETL parameter for timestamp_column when country_code parameter is unspecified.

## [3.0.1] - 2024-06-21

### Security

- Updated npm and python dependencies

## [3.0.0] - 2024-05-29

### Added

- Added a link to the front-end URL to the welcome email.

### Changed

- Migrated all AMC requests to use OAuth and the AMC API provided by Amazon Ads instead of instance-level APIs.
- Migrated the front-end to align with the AMC API provided by Amazon Ads.
- Migrated the front-end to use the Amazon Cognito hosted user interface for login instead of AWS Amplify.
- Replaced time-series based file partitioning (which the AMC API no longer requires) with a strategy based on file size so that pseudonymized files will not exceed 500MB (compressed).

### Security

- Updated npm dependencies

## [2.3.1] - 2024-03-28

### Security

- Update npm dependencies for vue-cli

## [2.3.0] - 2024-02-29

### Changed

- Provide country code when creating dataset in AMC.  

### Security

- Update npm dependencies for awswrangler, aws-amplify, bootstrap, and Vue.js

## [2.2.2] - 2024-01-09

### Fixed

- Resolve a defect that causes Glue ETL dependencies to be deleted after updating the Cloud Formation stack from v2.0.0, v2.1.0, v2.2.0, or v2.2.1 to a newer version.  

### Changed

- The Artifact Bucket resource is no longer automatically removed when the stack is removed. Customers will need to remove this bucket manually after removing the stack.

## [2.2.1] - 2023-12-07

### Added

- Added the option for users to specify CSV/JSON file format when uploading to existing datasets.

### Fixed

- Resolved an error that occurs when uploading files with an unexpected content type from a CloudFormation stack that was updated from v2.1.0.
- Resolved a defect that prevented users from being able to upload Dimension datasets to multiple AMC instances.

## [2.2.0] - 2023-11-01

### Added

- Added the option for users to specify CSV/JSON file format in the dataset definition web form.
- Added an optional parameter to API resources /get_data_columns and /start_amc_transformation that allows users to specify CSV/JSON file format.

### Changed

- Resolve code quality issues identified by SonarQube in the front-end.
- Remove Autodetect and PT1M options from the dataset definition web form.

## [2.1.1] - 2023-09-11

### Fixed

- Resolve a defect in the reporting of anonymous metrics that prevents CloudFormation events from being properly recorded.

## [2.1.0] - 2023-06-01

### Added

- Added instructions for automating uploads via S3 trigger to Step 5 in the front-end.
- Added support for Mobile Ad ID column types.

### Changed

- Alphabetize the country code list shown in dataset definition web form
- Enhance the protection of S3 access logs. (#232)

### Fixed

- Allow stack names to contain upper case characters
- Avoid redirecting / web requests to /step5

### Security

- Update npm dependencies for vuejs, vue-cli, aws-amplify, bootstrap, webpack-subresource-integrity, and eslint.
- Removed the eslint package in order to avoid a vulnerability in one of its dependencies

## [2.0.0] - 2023-04-17

### Added

- Support for eu-west-1 [#45]
- Upload to multiple AMC instances [#133, #145, #150, #172, #180, #183]
- Upload to existing datasets [#73]
- Upload multiple files at once [#41]
- Upload gzipped JSON and CSV files [#159]
- Improved data normalization for US, UK, JP, IN, IT, ES, CA, DE, FR [#61, #63, #72, #108, #109]
- Glue ETL performance metrics [#52]
- FACT partition size option [#52, #138]
- Country code option [#83, #132, #155, #157]
- LiveRamp support [#40, #85]
- Import/Export dataset schema [#102]
- Show API errors in front-end [#104]
- Retry on AMC request timeouts. [#117, #160]
- Custom lambda layer for aws-xray-sdk [#37, #68, #172]
- Automated integration tests [#34, #42, #173]
- Automated unit tests [#105, #120]
- AWS Solutions quality bar [#47, #64, #91, #103, #113, #153, #154, #156, #162]
- AWS Solutions pipeline integration [#81, #96]
- Add Pre-commit, fix SonarCube/SonarLint issues [#16]
- Add Unit Tests, combine coverage report for source/api/tests and source/tests. [#100]
- API documentation [#152]
- Show upload failure messages when provided by AMC [#221]

### Changed

- Prefix S3 bucket names with CF stack name to help organize S3 resources [#29]
- Allocate more time to HelperFunction for removing stack resources [#58]
- Remove unused lambda layer [#37]
- Architecture diagram [#177]
- Set s3 object ownership in order to maintain compatibility with s3 access logging [#229]

### Fixed

- Redundant log group [#168]
- Sorting of front-end tables [#148, #151]
- UX/UI issues for dataset schema [#93]
- Dropping first record [#23]

### Security

- Enable integrity checks for front-end assets [#39]
- Migrate python 3.9 to python 3.10 in build script [#33, #95]

## [1.0.0] - 2023-01-05

### Added

- Initial release.
