<!--
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
-->

<template>
  <div>
    <b-navbar
      toggleable="lg"
      type="dark"
      variant="dark"
    >
      <b-navbar-brand to="/">
        Amazon Marketing Cloud uploader from AWS
      </b-navbar-brand>
      <b-navbar-toggle target="nav-collapse" />

      <b-collapse
        id="nav-collapse"
        is-nav
      >
        <!-- Right aligned nav items -->
        <b-navbar-nav class="ml-auto">
          <b-nav-item
            @click="signOut()"
          >
            Sign Out
          </b-nav-item>
        </b-navbar-nav>
      </b-collapse>
    </b-navbar>
    <br>
  </div>
</template>

<script>
export default {
  name: 'Header',
  props: ['isCollectionActive', 'isUploadActive'],
  methods: {
    openWindow: function (url) {
      window.open(url, "noopener,noreferer");
    },
    signOut() {
      this.$Amplify.Auth.signOut()
          .then(() => this.$router.push({name: "Login"}))
          .catch(err => console.log(err));
    }
  }
}
</script>

<style>

#signOutBtn {
color: #ED900E;
}

</style>
