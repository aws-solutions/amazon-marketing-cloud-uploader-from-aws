# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
