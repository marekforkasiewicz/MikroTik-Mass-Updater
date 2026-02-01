<template>
  <div class="progress-tracker">
    <div class="d-flex justify-content-between mb-2">
      <span>{{ currentItem || 'Processing...' }}</span>
      <span>{{ progress }}/{{ total }}</span>
    </div>
    <div class="progress" :style="{ height: height }">
      <div
        class="progress-bar"
        :class="{
          'progress-bar-striped progress-bar-animated': isRunning,
          'bg-success': !isRunning && !hasErrors,
          'bg-warning': !isRunning && hasErrors
        }"
        :style="{ width: `${progressPercent}%` }"
      ></div>
    </div>
    <div class="text-center mt-1 small text-muted">
      {{ progressPercent }}%
      <span v-if="estimatedTime"> - Est. {{ estimatedTime }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  progress: {
    type: Number,
    default: 0
  },
  total: {
    type: Number,
    default: 0
  },
  currentItem: {
    type: String,
    default: ''
  },
  isRunning: {
    type: Boolean,
    default: false
  },
  hasErrors: {
    type: Boolean,
    default: false
  },
  height: {
    type: String,
    default: '20px'
  },
  estimatedTime: {
    type: String,
    default: ''
  }
})

const progressPercent = computed(() => {
  if (!props.total) return 0
  return Math.round((props.progress / props.total) * 100)
})
</script>
