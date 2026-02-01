<template>
  <div class="login-container d-flex align-items-center justify-content-center min-vh-100">
    <div class="card shadow-lg" style="width: 400px;">
      <div class="card-body p-5">
        <div class="text-center mb-4">
          <i class="bi bi-router fs-1 text-primary"></i>
          <h2 class="mt-2">MikroTik Mass Updater</h2>
          <p class="text-muted">Sign in to continue</p>
        </div>

        <form @submit.prevent="handleLogin">
          <div class="mb-3">
            <label class="form-label">Username</label>
            <div class="input-group">
              <span class="input-group-text">
                <i class="bi bi-person"></i>
              </span>
              <input
                type="text"
                class="form-control"
                v-model="username"
                placeholder="Enter username"
                required
                :disabled="loading"
              />
            </div>
          </div>

          <div class="mb-4">
            <label class="form-label">Password</label>
            <div class="input-group">
              <span class="input-group-text">
                <i class="bi bi-lock"></i>
              </span>
              <input
                :type="showPassword ? 'text' : 'password'"
                class="form-control"
                v-model="password"
                placeholder="Enter password"
                required
                :disabled="loading"
              />
              <button
                type="button"
                class="btn btn-outline-secondary"
                @click="showPassword = !showPassword"
              >
                <i :class="showPassword ? 'bi bi-eye-slash' : 'bi bi-eye'"></i>
              </button>
            </div>
          </div>

          <div v-if="error" class="alert alert-danger py-2">
            <i class="bi bi-exclamation-circle me-2"></i>{{ error }}
          </div>

          <button
            type="submit"
            class="btn btn-primary w-100"
            :disabled="loading"
          >
            <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
            {{ loading ? 'Signing in...' : 'Sign In' }}
          </button>
        </form>

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const username = ref('')
const password = ref('')
const showPassword = ref(false)
const loading = ref(false)
const error = ref('')

async function handleLogin() {
  error.value = ''
  loading.value = true

  try {
    const success = await authStore.login(username.value, password.value)
    if (success) {
      const redirect = route.query.redirect || '/'
      router.push(redirect)
    } else {
      error.value = 'Invalid username or password'
    }
  } catch (e) {
    error.value = e.message || 'Login failed'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
</style>
