<template>
  <div class="results-summary">
    <div class="row text-center">
      <div class="col">
        <div class="fs-3 text-primary">{{ total }}</div>
        <small class="text-muted">Total</small>
      </div>
      <div class="col">
        <div class="fs-3 text-success">{{ successful }}</div>
        <small class="text-muted">Successful</small>
      </div>
      <div class="col">
        <div class="fs-3 text-danger">{{ failed }}</div>
        <small class="text-muted">Failed</small>
      </div>
      <div class="col" v-if="showSkipped">
        <div class="fs-3 text-warning">{{ skipped }}</div>
        <small class="text-muted">Skipped</small>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  total: {
    type: Number,
    default: 0
  },
  successful: {
    type: Number,
    default: 0
  },
  failed: {
    type: Number,
    default: 0
  },
  skipped: {
    type: Number,
    default: 0
  },
  showSkipped: {
    type: Boolean,
    default: false
  }
})
</script>
