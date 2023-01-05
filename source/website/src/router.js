// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import Vue from 'vue'
import VueRouter from 'vue-router'
import Login from '@/views/Login.vue'
import Step1 from '@/views/Step1.vue'
import Step2 from '@/views/Step2.vue'
import Step3 from '@/views/Step3.vue'
import Step4 from '@/views/Step4.vue'
import Step5 from '@/views/Step5.vue'

Vue.use(VueRouter);

const router = new VueRouter({
  mode: 'history',
  base: process.env.BASE_URL,
  routes: [
    {
      path: '/step1',
      name: 'Step1',
      component: Step1,
      meta: { requiresAuth: true }
    },
    {
      path: '/step2',
      name: 'Step2',
      component: Step2,
      meta: { requiresAuth: true }
    },
    {
      path: '/step3',
      name: 'Step3',
      component: Step3,
      meta: { requiresAuth: true }
    },
    {
      path: '/step4',
      name: 'Step4',
      component: Step4,
      meta: { requiresAuth: true }
    },
    {
      path: '/step5',
      alias: '/',
      name: 'Step5',
      component: Step5,
      meta: { requiresAuth: true }
    },
    {
      path: "/login",
      name: "Login",
      component: Login,
      meta: { requiresAuth: false },
    }
  ]
});

router.beforeResolve(async (to, from, next) => {
  if (to.matched.some(record => record.meta.requiresAuth)) {
    try {
      await Vue.prototype.$Amplify.Auth.currentAuthenticatedUser();
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

export default router;
