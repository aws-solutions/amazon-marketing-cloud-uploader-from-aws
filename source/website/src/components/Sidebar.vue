<!--
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
-->

<template>
  <div>
    <b-row class="my-1">
      <b-col>
        Step 1
        <b-link
          id="step1"
          to="/step1"
          :active="isStep1Active"
        >
          <br>
          Select file
        </b-link>
        <hr>
        Step 2
        <b-link
          id="step2"
          to="/step2"
          :active="isStep2Active"
        >
          <br>
          Select destinations
        </b-link>
        <hr>
        Step 3
        <b-link
          id="step3"
          to="/step3"
          :class="{ active: isStep3Active }"
        >
          <br>
          Define dataset
        </b-link>
        <hr>
        Step 4
        <b-link
          id="step4"
          to="/step4"
          :class="{ active: isStep4Active }"
        >
          <br>
          Define columns
        </b-link>
        <hr>
        Step 5
        <b-link
          id="step5"
          to="/step5"
          :class="{ active: isStep5Active }"
        >
          <br>
          Confirm details
        </b-link>
        <hr>
        Step 6
        <b-link
          id="step6"
          to="/step6"
          :class="{ active: isStep6Active }"
        >
          <br>
          Monitor uploads
        </b-link>
        <hr>
        Settings
        <b-link
          id="settings"
          to="/settings"
          :class="{ active: isSettingsActive }"
        >
          <br>
          AMC Instances
        </b-link>
        <hr>
      </b-col>
    </b-row>
  </div>
</template>

<script>

export default {
  name: 'Sidebar',
  props: ['isStep1Active','isStep2Active','isStep3Active','isStep4Active', 'isStep5Active', 'isStep6Active', 'isTestActive', 'isSettingsActive'],
}

</script>

<style>
a.router-link-active {
  color: black;
}
</style>
