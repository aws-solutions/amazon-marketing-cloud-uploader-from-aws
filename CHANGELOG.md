# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

### Changed

- Prefix S3 bucket names with CF stack name to help organize S3 resources [#29]
- Allocate more time to HelperFunction for removing stack resources [#58]
- Remove unused lambda layer [#37]
- Architecture diagram [#177]

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
