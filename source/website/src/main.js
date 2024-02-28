// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

console.warn = () => {}

import { createApp } from 'vue'
import { BootstrapVue, BIconClipboard, BIconQuestionCircleFill, BIconXCircle, BIconPlusSquare, BIconExclamationTriangleFill } from 'bootstrap-vue'
import 'bootstrap/dist/css/bootstrap.css'
import 'bootstrap-vue/dist/bootstrap-vue.css'
import App from './App.vue'
import store from './store'
import router from './router.js'
import { Amplify } from "aws-amplify"
import * as AmplifyModules from "aws-amplify";
import { AmplifyPlugin } from "aws-amplify-vue";

const getRuntimeConfig = async () => {
  const runtimeConfig = await fetch('/runtimeConfig.json');
  return runtimeConfig.json()
};

getRuntimeConfig().then(function(json) {
  const awsconfig = {
    Auth: {
      region: json.AWS_REGION,
      userPoolId: json.USER_POOL_ID,
      userPoolWebClientId: json.USER_POOL_CLIENT_ID,
      identityPoolId: json.IDENTITY_POOL_ID
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

  const app = createApp({
    router,
    ...App
  })

  app.use(AmplifyPlugin, AmplifyModules)
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
        ENCRYPTION_MODE: json.ENCRYPTION_MODE
      }
    },
  });

  router.beforeResolve(async (to, from, next) => {
    if (to.matched.some(record => record.meta.requiresAuth)) {
      try {
        await app.prototype.$Amplify.Auth.currentAuthenticatedUser();
        next();
      } catch (e) {
        console.log(e);
        next({
          path: "/login",
        });
      }
    }
    console.log(next);
    next();
  });

  app.mount('#app')
});
