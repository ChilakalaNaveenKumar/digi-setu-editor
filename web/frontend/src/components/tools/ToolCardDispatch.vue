<!--
  ToolCardDispatch — by-name routing for tool cards.
  Add new specialized cards (read, bash, …) here as they're built.
  Mirrors pi-web-ui's renderer-registry approach but kept as a Vue
  component switch — simpler than a runtime registry, with same effect.
-->
<script setup lang="ts">
import type { ToolCall } from "../../types/rpc";
import ToolCallCard from "../ToolCallCard.vue";
import BashToolCard from "./BashToolCard.vue";
import EditToolCard from "./EditToolCard.vue";
import FindToolCard from "./FindToolCard.vue";
import GrepToolCard from "./GrepToolCard.vue";
import LsToolCard from "./LsToolCard.vue";
import ProcessToolCard from "./ProcessToolCard.vue";
import ReadToolCard from "./ReadToolCard.vue";
import WriteToolCard from "./WriteToolCard.vue";

defineProps<{ call: ToolCall }>();
</script>

<template>
  <WriteToolCard v-if="call.name === 'write'" :call="call" />
  <EditToolCard v-else-if="call.name === 'edit'" :call="call" />
  <BashToolCard v-else-if="call.name === 'bash'" :call="call" />
  <ProcessToolCard v-else-if="call.name === 'process'" :call="call" />
  <ReadToolCard v-else-if="call.name === 'read'" :call="call" />
  <GrepToolCard v-else-if="call.name === 'grep'" :call="call" />
  <LsToolCard v-else-if="call.name === 'ls'" :call="call" />
  <FindToolCard v-else-if="call.name === 'find'" :call="call" />
  <ToolCallCard v-else :call="call" />
</template>
