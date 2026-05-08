<!--
  App — global shell. Mounts the router-view and the singleton overlays
  (toasts, confirm modal). Per-route content lives in `views/`.
-->
<script setup lang="ts">
import { onMounted } from "vue";
import { RouterView } from "vue-router";

import ConfirmModal from "./components/ConfirmModal.vue";
import Toast from "./components/Toast.vue";
import { useConfigStore } from "./stores/config";

const cfg = useConfigStore();

// Fetch deploy mode once on boot — Picker.vue waits on `cfg.ready`.
onMounted(() => {
  void cfg.refresh();
});
</script>

<template>
  <div class="flex h-full w-full flex-col bg-background text-foreground">
    <RouterView />
    <Toast />
    <ConfirmModal />
  </div>
</template>
