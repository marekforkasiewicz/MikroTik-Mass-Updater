<template>
  <div class="card" :class="cardClass">
    <div class="card-body">
      <div class="d-flex justify-content-between align-items-start">
        <div>
          <h3 class="mb-0">{{ value }}</h3>
          <small :class="textClass">{{ label }}</small>
        </div>
        <i :class="[icon, 'fs-1 opacity-50']"></i>
      </div>
      <div v-if="trend !== null" class="mt-2">
        <small :class="trendClass">
          <i :class="trendIcon"></i>
          {{ Math.abs(trend) }}% {{ trend >= 0 ? 'increase' : 'decrease' }}
        </small>
      </div>
      <div v-if="$slots.action" class="mt-2">
        <slot name="action"></slot>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  label: {
    type: String,
    required: true
  },
  value: {
    type: [String, Number],
    required: true
  },
  icon: {
    type: String,
    default: 'bi bi-circle'
  },
  variant: {
    type: String,
    default: 'primary',
    validator: (v) => ['primary', 'success', 'danger', 'warning', 'info', 'secondary'].includes(v)
  },
  trend: {
    type: Number,
    default: null
  }
})

const cardClass = computed(() => {
  return `bg-${props.variant} ${props.variant === 'warning' ? 'text-dark' : 'text-white'}`
})

const textClass = computed(() => {
  return props.variant === 'warning' ? 'text-dark' : ''
})

const trendClass = computed(() => {
  return props.trend >= 0 ? 'text-success' : 'text-danger'
})

const trendIcon = computed(() => {
  return props.trend >= 0 ? 'bi bi-arrow-up' : 'bi bi-arrow-down'
})
</script>
