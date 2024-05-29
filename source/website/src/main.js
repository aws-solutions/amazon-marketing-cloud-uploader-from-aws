// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

console.warn = () => {}

import * as AmplifyModules from "aws-amplify"
import { Amplify, Auth, Hub } from "aws-amplify"
import { BIconClipboard, BIconExclamationTriangleFill, BIconPlusSquare, BIconQuestionCircleFill, BIconXCircle, BootstrapVue } from 'bootstrap-vue'
import 'bootstrap-vue/dist/bootstrap-vue.css'
import 'bootstrap/dist/css/bootstrap.css'
import { createApp } from 'vue'
import App from './App.vue'
import router from './router.js'
import store from './store'

const getRuntimeConfig = async () => {
  const runtimeConfig = await fetch("/runtimeConfig.json");
  return runtimeConfig.json()
};

const syncCurrentSession = async () => {
  try {
    const currentUserSession = await Auth.currentAuthenticatedUser({ bypassCache: true });
    return currentUserSession;
  } catch (error) {
    console.log(error)
    return {}
  }
};

const checkAMCRedirect = () => {
  // Return true if this is an auth redirect from AMC/Amazon Login
  // Cognito redirects to / (root)
  // Amazon Login redirects to /redirect
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.has('code') && urlParams.has('state') && window.location.pathname.endsWith('/redirect');
}

const updateAndRedirect = () => {
  // Rename the code and state parameters to prevent Amplify from processing them
  const currentUrl = new URL(window.location.href);
  const codeValue = currentUrl.searchParams.get('code');
  const stateValue = currentUrl.searchParams.get('state');
  if (codeValue) {
    currentUrl.searchParams.set('amz-code', codeValue);
    currentUrl.searchParams.delete('code');
  }
  if (stateValue) {
    currentUrl.searchParams.set('amz-state', stateValue);
    currentUrl.searchParams.delete('state');
  }
  if (codeValue || stateValue) {
    // force a refresh
    window.location.href = currentUrl.href;
  }
}

// rename the parameters and refresh the page if we're returning from AMC/Amazon Login
if (checkAMCRedirect()) {
  console.log('Redirect from AMC/Amazon Login detected');
  updateAndRedirect();
}

Promise.all([getRuntimeConfig, syncCurrentSession]).then((promiseObj) => {
  promiseObj[0]().then(function (json) {
    const awsconfig = {
      Auth: {
        region: json.AWS_REGION,
        userPoolId: json.USER_POOL_ID,
        userPoolWebClientId: json.USER_POOL_CLIENT_ID,
        identityPoolId: json.IDENTITY_POOL_ID,
        oauth: {
          domain: json.HOSTED_UI_DOMAIN,
          scope: ["profile", "openid"],
          redirectSignIn: json.COGNITO_CALLBACK_URL,
          redirectSignOut: json.COGNITO_LOGOUT_URL,
          responseType: "code"
        }
      },
      Storage: {
        AWSS3: {
          region: json.AWS_REGION
        }
      },
      API: {
        endpoints: [
          {
            name: "amcufa-api",
            endpoint: json.API_ENDPOINT,
            service: "execute-api",
            region: json.AWS_REGION
          },
        ]
      }
    };

    console.log("Runtime config: " + JSON.stringify(json));
    Amplify.configure(awsconfig);

    promiseObj[1]().then(function (data) {
      const app = createApp({
        router,
        ...App
      })

      app.use(AmplifyModules)
      app.use(BootstrapVue);
      app.use(store);
      app.component('BIconClipboard', BIconClipboard)
      app.component('BIconQuestionCircleFill', BIconQuestionCircleFill)
      app.component('BIconXCircle', BIconXCircle)
      app.component('BIconPlusSquare', BIconPlusSquare)
      app.component('BIconExclamationTriangleFill', BIconExclamationTriangleFill)

      app.mixin({
        data() {
          return {
            // Distribute runtime configs into every Vue component
            AWS_REGION: json.AWS_REGION,
            API_ENDPOINT: json.API_ENDPOINT,
            DATA_BUCKET_NAME: json.DATA_BUCKET_NAME,
            ARTIFACT_BUCKET_NAME: json.ARTIFACT_BUCKET_NAME,
            ENCRYPTION_MODE: json.ENCRYPTION_MODE,
            USER_POOL_ID: json.USER_POOL_ID
          }
        },
      });

      router.beforeResolve(async (to, from, next) => {
        if (to.matched.some(record => record.meta.requiresAuth)) {
          try {
            await Auth.currentAuthenticatedUser();
            next();
          } catch (e) {
            console.error(e);
            Auth.federatedSignIn();
          }
        }
        else {
          console.log(next);
          next();
        }
      });

      Hub.listen("auth", (data) => {
        console.log(`Hub event ${data.payload.event}`)
        switch (data.payload.event) {
          case "signIn":
            console.log("user signed in");
            router.push({ path: "/step6" });
            break;
          case "signOut":
            console.log("user signed out");
            Auth.federatedSignIn();
            break;
        }
      });

      app.mount("#app")
    })
  })
})
