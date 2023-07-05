<!--
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
-->

<template>
  <div>
    <amplify-authenticator></amplify-authenticator>
  </div>
</template>

<script>
import { Auth } from 'aws-amplify';
import { Hub } from 'aws-amplify';

export default {
  name: "Login",
  data() {
    return {};
  },
  mounted() {
    Hub.listen('auth', (data) => {
      switch (data.payload.event) {
        case 'signIn':
          console.log('user signed in');
          this.$router.push({path: "/step6"});
          break;
        case 'signOut':
          console.log('user signed out');
          this.$router.push({name: "Login"});
          break;
      }
    });
  },
  created() {
    // handle users who have already signed in 
    this.getLoginStatus()
  },
  methods: {
    getLoginStatus () {
      Auth.currentSession().then(data => {
        this.session = data;
        if (this.session != null) {
          console.log('user already signed in');
          console.log(this.session)
          this.$router.push({path: "/step6"});
        }
      }).catch(err => {
        console.log(err);
      })
    }
  }
};
</script>
