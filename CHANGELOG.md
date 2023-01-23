# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Allow users to specify FACT partition size [#52]
- Record anonymous performance metrics to measure ETL workload size [#52]
- Automate integration tests [#42]
- Automate front-end tests [#32]
- Automate build and deploy tests [#34]  
- Invalid email addresses should normalize to empty string [#63]

### Changed

- Prefix S3 bucket names with CF stack name to help organize S3 resources [#29]
- Allocate more time to HelperFunction for removing stack resources [#58]
- Remove the us-east-1 restriction so users can attempt to deploy in any region [#45]
- Remove unused lambda layer [#37]

### Fixed

- Resolve a data loss issue in the normalization job [#23]

### Security
 
- Enable integrity checks for front-end assets [#39]



## [1.0.0] - 2023-01-05

### Added

- Initial release.


