import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  },
  withCredentials: true
})

let refreshPromise = null
let refreshFailed = false

function clearAuthState() {
  localStorage.removeItem('isAuthenticated')
}

function redirectToLogin() {
  if (window.location.pathname !== '/login') {
    window.location.href = '/login'
  }
}

async function refreshSession() {
  if (!refreshPromise) {
    refreshPromise = api.post('/auth/refresh')
      .catch((error) => {
        refreshFailed = true
        clearAuthState()
        redirectToLogin()
        throw error
      })
      .finally(() => {
        refreshPromise = null
      })
  }

  await refreshPromise
}

api.interceptors.response.use(
  (response) => response.data,
  async (error) => {
    const originalRequest = error.config

    if (!originalRequest) {
      return Promise.reject(error)
    }

    const isRefreshRequest = originalRequest.url?.includes('/auth/refresh')

    if (error.response?.status === 401 && !isRefreshRequest && !originalRequest._retry && !refreshFailed) {
      originalRequest._retry = true

      try {
        await refreshSession()
        return api(originalRequest)
      } catch (refreshError) {
        return Promise.reject(refreshError)
      }
    }

    if (error.response?.status === 401 && isRefreshRequest) {
      refreshFailed = true
      clearAuthState()
      redirectToLogin()
    }

    const message = error.response?.data?.detail || error.message || 'An error occurred'
    console.error('API Error:', message)
    return Promise.reject(new Error(message))
  }
)

export function resetRefreshState() {
  refreshFailed = false
}

export default api
