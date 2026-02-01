<template>
  <div class="console-output" ref="consoleEl">
    <div v-for="(msg, index) in messages" :key="index" :class="getLineClass(msg.type)">
      {{ msg.text }}
    </div>
    <div v-if="messages.length === 0" class="text-muted">
      {{ placeholder }}
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'

const props = defineProps({
  messages: {
    type: Array,
    default: () => []
  },
  placeholder: {
    type: String,
    default: 'No output yet...'
  },
  autoScroll: {
    type: Boolean,
    default: true
  }
})

const consoleEl = ref(null)

function getLineClass(type) {
  const classes = {
    success: 'line-success',
    error: 'line-error',
    warning: 'line-warning',
    info: 'line-info'
  }
  return classes[type] || ''
}

watch(() => props.messages.length, () => {
  if (props.autoScroll) {
    nextTick(() => {
      if (consoleEl.value) {
        consoleEl.value.scrollTop = consoleEl.value.scrollHeight
      }
    })
  }
})
</script>

<style scoped>
.console-output {
  background-color: var(--console-bg, #1e1e1e);
  color: var(--console-text, #d4d4d4);
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  padding: 1rem;
  border-radius: 0.375rem;
  max-height: 400px;
  overflow-y: auto;
}

.line-success { color: #4ec9b0; }
.line-error { color: #f14c4c; }
.line-warning { color: #cca700; }
.line-info { color: #3794ff; }
</style>
