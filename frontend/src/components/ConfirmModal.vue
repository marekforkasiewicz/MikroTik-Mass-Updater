<template>
  <Teleport to="body">
    <div v-if="visible" class="modal fade show" tabindex="-1" style="display: block;">
      <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
          <div class="modal-header" :class="headerClass">
            <h5 class="modal-title">
              <i :class="iconClass" class="me-2"></i>{{ title }}
            </h5>
            <button type="button" class="btn-close" :class="{ 'btn-close-white': variant === 'danger' }"
                    @click="cancel" :disabled="loading"></button>
          </div>
          <div class="modal-body">
            <p class="mb-0">{{ message }}</p>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" @click="cancel" :disabled="loading">
              {{ cancelText }}
            </button>
            <button type="button" class="btn" :class="confirmButtonClass" @click="confirm" :disabled="loading">
              <span v-if="loading" class="spinner-border spinner-border-sm me-1"></span>
              {{ confirmText }}
            </button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="visible" class="modal-backdrop fade show"></div>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: 'Confirm'
  },
  message: {
    type: String,
    default: 'Are you sure?'
  },
  variant: {
    type: String,
    default: 'danger',
    validator: (v) => ['danger', 'warning', 'primary', 'info'].includes(v)
  },
  confirmText: {
    type: String,
    default: 'Confirm'
  },
  cancelText: {
    type: String,
    default: 'Cancel'
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['confirm', 'cancel'])

const headerClass = computed(() => {
  const classes = {
    danger: 'bg-danger text-white',
    warning: 'bg-warning text-dark',
    primary: 'bg-primary text-white',
    info: 'bg-info text-white'
  }
  return classes[props.variant] || ''
})

const iconClass = computed(() => {
  const icons = {
    danger: 'bi bi-exclamation-triangle-fill',
    warning: 'bi bi-exclamation-circle-fill',
    primary: 'bi bi-question-circle-fill',
    info: 'bi bi-info-circle-fill'
  }
  return icons[props.variant] || 'bi bi-question-circle'
})

const confirmButtonClass = computed(() => {
  return `btn-${props.variant}`
})

function confirm() {
  emit('confirm')
}

function cancel() {
  emit('cancel')
}
</script>
