// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import Vue from 'vue'
import VueRouter from 'vue-router'
import Step1 from '@/views/Step1.vue'
import Step2 from '@/views/Step2.vue'
import Step3 from '@/views/Step3.vue'
import Step4 from '@/views/Step4.vue'
import Step5 from '@/views/Step5.vue'
import Step6 from '@/views/Step6.vue'
import Settings from '@/views/Settings.vue'
import Redirect from '@/views/Redirect.vue'

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
      name: 'Step5',
      component: Step5,
      meta: { requiresAuth: true }
    },
    {
      path: '/step6',
      alias: '/',
      name: 'Step6',
      component: Step6,
      meta: { requiresAuth: true }
    },
    {
      path: "/settings",
      name: "Settings",
      component: Settings,
      meta: {requiresAuth: true}
    },
    {
      path: "/redirect",
      name: "Redirect",
      component: Redirect,
      meta: {requiresAuth: true}
    }
  ]
});

export default router;
