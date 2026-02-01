<template>
  <div v-if="error" class="error-boundary">
    <div class="container py-5">
      <div class="card border-danger">
        <div class="card-header bg-danger text-white">
          <h5 class="mb-0">
            <i class="bi bi-exclamation-triangle-fill me-2"></i>
            Something went wrong
          </h5>
        </div>
        <div class="card-body">
          <p class="text-muted mb-3">An unexpected error occurred. Please try again or contact support if the problem persists.</p>

          <div v-if="showDetails" class="alert alert-secondary">
            <strong>Error:</strong> {{ error.message }}
            <pre v-if="error.stack" class="mt-2 mb-0 small" style="max-height: 200px; overflow: auto;">{{ error.stack }}</pre>
          </div>

          <div class="d-flex gap-2">
            <button class="btn btn-primary" @click="retry">
              <i class="bi bi-arrow-clockwise me-1"></i>
              Try Again
            </button>
            <button class="btn btn-outline-secondary" @click="goHome">
              <i class="bi bi-house me-1"></i>
              Go to Dashboard
            </button>
            <button class="btn btn-outline-secondary" @click="showDetails = !showDetails">
              <i class="bi bi-bug me-1"></i>
              {{ showDetails ? 'Hide' : 'Show' }} Details
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
  <slot v-else></slot>
</template>

<script setup>
import { ref, onErrorCaptured } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const error = ref(null)
const showDetails = ref(false)

onErrorCaptured((err, instance, info) => {
  error.value = err
  console.error('ErrorBoundary caught:', err, info)
  return false // Prevent error from propagating
})

function retry() {
  error.value = null
  showDetails.value = false
}

function goHome() {
  error.value = null
  showDetails.value = false
  router.push('/')
}

// Expose reset method for parent components
defineExpose({
  reset: () => {
    error.value = null
    showDetails.value = false
  }
})
</script>

<style scoped>
.error-boundary {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--bg-primary, #f8f9fa);
}
</style>
