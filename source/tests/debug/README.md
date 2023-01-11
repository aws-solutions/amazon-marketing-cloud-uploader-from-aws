### Notes
Debug/Run this project (website and app) in localhost mode without deploying through CloudFormation multiple time to test. This will simplifies manual testing for the API and front-end. You need to have deployed once already to use this. The glue console scripts i.e amc_transformations and lambda scripts i.e amc_uploader needs to deployed and created along with Cognito.

### Backend
 - update variables in `config.json` in `source/api/.chalice`
```
$ ./local_mode.sh --run_app
```

### Frontend
 - update variables in `runtimeConfig.json` in `source/website/public` with your deployed stack info.
```
$ ./local_mode.sh --run_web
```
 - then go to `http://localhost:8080/` and login with the same creds used in your `runtimeConfig.json` `USER_POOL_ID`.

### Show help
 - Help?
```
$ ./local_mode.sh --help
```
```
Usage: ./local_mode.sh [arguments]
  Available options:
  -h, --help      Print this help and exit.
  -rw, --run_web    Builds and runs npm site in localhost.
  -ra, --run_app    Runs REST API in chalice local test server.
```