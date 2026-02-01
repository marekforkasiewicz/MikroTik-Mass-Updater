import axios from 'axios'

// Create axios instance
const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  },
  withCredentials: true  // For cookies
})

// Request interceptor
api.interceptors.request.use(
  config => {
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// Flag to prevent multiple refresh attempts
let isRefreshing = false
let refreshFailed = false

// Response interceptor
api.interceptors.response.use(
  response => response.data,
  async error => {
    const originalRequest = error.config

    // Handle case where error.config is undefined (network errors, etc.)
    if (!originalRequest) {
      return Promise.reject(error)
    }

    // Don't try to refresh if:
    // - This IS the refresh endpoint
    // - Already tried to refresh this request
    // - A refresh is in progress
    // - A refresh recently failed
    const isRefreshRequest = originalRequest.url?.includes('/auth/refresh')

    if (error.response?.status === 401 && !isRefreshRequest && !originalRequest._retry && !isRefreshing && !refreshFailed) {
      originalRequest._retry = true
      isRefreshing = true

      try {
        await api.post('/auth/refresh')
        isRefreshing = false
        return api(originalRequest)
      } catch (refreshError) {
        isRefreshing = false
        refreshFailed = true
        // Clear auth state and redirect to login
        localStorage.removeItem('isAuthenticated')
        window.location.href = '/login'
        return Promise.reject(refreshError)
      }
    }

    // If refresh endpoint itself returns 401, go to login
    if (error.response?.status === 401 && isRefreshRequest) {
      refreshFailed = true
      localStorage.removeItem('isAuthenticated')
      window.location.href = '/login'
      return Promise.reject(error)
    }

    const message = error.response?.data?.detail || error.message || 'An error occurred'
    console.error('API Error:', message)
    return Promise.reject(new Error(message))
  }
)

// =============================================================================
// Auth API
// =============================================================================
// Reset refresh failed flag on successful login
export const resetRefreshState = () => {
  refreshFailed = false
}

export const authApi = {
  login: async (username, password) => {
    const response = await api.post('/auth/login',
      new URLSearchParams({ username, password }),
      { headers: { 'Content-Type': 'application/x-www-form-urlencoded' }}
    )
    resetRefreshState()  // Reset on successful login
    return response
  },
  loginJson: (username, password) => api.post('/auth/login/json', { username, password }),
  logout: () => api.post('/auth/logout'),
  refresh: () => api.post('/auth/refresh'),
  me: () => api.get('/auth/me'),
  changePassword: (currentPassword, newPassword) =>
    api.post('/auth/change-password', { current_password: currentPassword, new_password: newPassword })
}

// =============================================================================
// Users API
// =============================================================================
export const usersApi = {
  list: (params = {}) => api.get('/users', { params }),
  get: (id) => api.get(`/users/${id}`),
  create: (data) => api.post('/users', data),
  update: (id, data) => api.put(`/users/${id}`, data),
  delete: (id) => api.delete(`/users/${id}`),
  // API Keys
  listApiKeys: () => api.get('/users/me/api-keys'),
  createApiKey: (data) => api.post('/users/me/api-keys', data),
  deleteApiKey: (id) => api.delete(`/users/me/api-keys/${id}`),
  revokeApiKey: (id) => api.post(`/users/me/api-keys/${id}/revoke`)
}

// =============================================================================
// Router API
// =============================================================================
export const routerApi = {
  list: (params = {}) => api.get('/routers', { params }),
  get: (id) => api.get(`/routers/${id}`),
  create: (data) => api.post('/routers', data),
  update: (id, data) => api.put(`/routers/${id}`, data),
  delete: (id) => api.delete(`/routers/${id}`),
  import: (content, replace = false) => api.post('/routers/import', { content, replace }),
  importFile: () => api.post('/routers/import-file'),
  changeChannel: (id, channel) => api.post(`/routers/${id}/change-channel`, null, { params: { channel } })
}

// =============================================================================
// Groups API
// =============================================================================
export const groupsApi = {
  list: (params = {}) => api.get('/groups', { params }),
  getTree: () => api.get('/groups/tree'),
  get: (id) => api.get(`/groups/${id}`),
  create: (data) => api.post('/groups', data),
  update: (id, data) => api.put(`/groups/${id}`, data),
  delete: (id) => api.delete(`/groups/${id}`),
  addRouters: (id, routerIds) => api.post(`/groups/${id}/routers`, { router_ids: routerIds }),
  removeRouters: (id, routerIds) => api.delete(`/groups/${id}/routers`, { data: { router_ids: routerIds }}),
  getRouters: (id, includeChildren = false) =>
    api.get(`/groups/${id}/routers`, { params: { include_children: includeChildren }}),
  search: (query) => api.get(`/groups/search/${query}`)
}

// =============================================================================
// Scan API
// =============================================================================
export const scanApi = {
  quickScan: (routerIds = null) => api.post('/scan/quick', routerIds ? { router_ids: routerIds } : null),
  fullScan: (routerIds = null) => api.post('/scan/full', routerIds ? { router_ids: routerIds } : null),
  quickScanSingle: (routerId) => api.get(`/scan/quick/single/${routerId}`),
  checkFirmware: (routerId) => api.get(`/scan/firmware/${routerId}`)
}

// =============================================================================
// Task API
// =============================================================================
export const taskApi = {
  list: (params = {}) => api.get('/tasks', { params }),
  get: (id) => api.get(`/tasks/${id}`),
  create: (data) => api.post('/tasks', data),
  cancel: (id) => api.post(`/tasks/${id}/cancel`),
  delete: (id) => api.delete(`/tasks/${id}`),
  startUpdate: (config) => api.post('/tasks/update', config)
}

// =============================================================================
// Schedules API
// =============================================================================
export const schedulesApi = {
  list: (params = {}) => api.get('/schedules', { params }),
  get: (id) => api.get(`/schedules/${id}`),
  create: (data) => api.post('/schedules', data),
  update: (id, data) => api.put(`/schedules/${id}`, data),
  delete: (id) => api.delete(`/schedules/${id}`),
  enable: (id) => api.post(`/schedules/${id}/enable`),
  disable: (id) => api.post(`/schedules/${id}/disable`),
  runNow: (id) => api.post(`/schedules/${id}/run-now`),
  getExecutions: (id, params = {}) => api.get(`/schedules/${id}/executions`, { params }),
  describeCron: (cron) => api.get('/schedules/cron-describe', { params: { cron }})
}

// =============================================================================
// Notifications API
// =============================================================================
export const notificationsApi = {
  // Channels
  listChannels: () => api.get('/notifications/channels'),
  getChannel: (id) => api.get(`/notifications/channels/${id}`),
  createChannel: (data) => api.post('/notifications/channels', data),
  updateChannel: (id, data) => api.put(`/notifications/channels/${id}`, data),
  deleteChannel: (id) => api.delete(`/notifications/channels/${id}`),
  testChannel: (id, message) => api.post(`/notifications/channels/${id}/test`, { message }),
  // Rules
  listRules: (params = {}) => api.get('/notifications/rules', { params }),
  createRule: (data) => api.post('/notifications/rules', data),
  updateRule: (id, data) => api.put(`/notifications/rules/${id}`, data),
  deleteRule: (id) => api.delete(`/notifications/rules/${id}`),
  // Logs
  getLogs: (params = {}) => api.get('/notifications/logs', { params }),
  // Event types
  getEventTypes: () => api.get('/notifications/event-types')
}

// =============================================================================
// Backups API
// =============================================================================
export const backupsApi = {
  list: (params = {}) => api.get('/backups', { params }),
  get: (id) => api.get(`/backups/${id}`),
  create: (data) => api.post('/backups', data),
  createBulk: (data) => api.post('/backups/bulk', data),
  delete: (id) => api.delete(`/backups/${id}`),
  download: (id) => api.get(`/backups/${id}/download`, { responseType: 'blob' }),
  restore: (data) => api.post('/backups/restore', data),
  getRollbackLogs: (params = {}) => api.get('/backups/rollback-logs', { params }),
  cleanup: (days = 30) => api.post('/backups/cleanup', null, { params: { days }})
}

// =============================================================================
// Scripts API
// =============================================================================
export const scriptsApi = {
  list: (params = {}) => api.get('/scripts', { params }),
  get: (id) => api.get(`/scripts/${id}`),
  create: (data) => api.post('/scripts', data),
  update: (id, data) => api.put(`/scripts/${id}`, data),
  delete: (id) => api.delete(`/scripts/${id}`),
  validate: (data) => api.post('/scripts/validate', data),
  execute: (id, data) => api.post(`/scripts/${id}/execute`, data),
  executeBulk: (id, data) => api.post(`/scripts/${id}/bulk-execute`, data),
  getExecutions: (id, params = {}) => api.get(`/scripts/${id}/executions`, { params }),
  getCategories: () => api.get('/scripts/categories')
}

// =============================================================================
// Monitoring API
// =============================================================================
export const monitoringApi = {
  getOverview: () => api.get('/monitoring/overview'),
  getConfig: () => api.get('/monitoring/config'),
  updateConfig: (data) => api.put('/monitoring/config', data),
  getRouterConfig: (routerId) => api.get(`/monitoring/routers/${routerId}/config`),
  createRouterConfig: (routerId, data) => api.post(`/monitoring/routers/${routerId}/config`, data),
  triggerCheck: (routerId, checkType = 'full') =>
    api.post(`/monitoring/routers/${routerId}/check`, null, { params: { check_type: checkType }}),
  getHealthHistory: (routerId, params = {}) =>
    api.get(`/monitoring/routers/${routerId}/history`, { params }),
  // Alerts
  getAlerts: (params = {}) => api.get('/monitoring/alerts', { params }),
  getActiveAlerts: () => api.get('/monitoring/alerts/active'),
  acknowledgeAlerts: (alertIds) => api.post('/monitoring/alerts/acknowledge', { alert_ids: alertIds }),
  resolveAlerts: (alertIds) => api.post('/monitoring/alerts/resolve', { alert_ids: alertIds }),
  getAlert: (id) => api.get(`/monitoring/alerts/${id}`)
}

// =============================================================================
// Reports API
// =============================================================================
export const reportsApi = {
  generate: (data) => api.post('/reports', data),
  list: () => api.get('/reports'),
  download: (filename) => api.get(`/reports/download/${filename}`, { responseType: 'blob' }),
  delete: (filename) => api.delete(`/reports/${filename}`),
  quickInventory: (format = 'csv') => api.get('/reports/quick/inventory', { params: { format }}),
  quickHealth: (format = 'csv') => api.get('/reports/quick/health', { params: { format }})
}

// =============================================================================
// Dashboard API
// =============================================================================
export const dashboardApi = {
  get: () => api.get('/dashboard'),
  getStats: () => api.get('/dashboard/stats'),
  getChart: (chartType) => api.get(`/dashboard/charts/${chartType}`),
  getTimeSeries: (metric, params = {}) => api.get(`/dashboard/time-series/${metric}`, { params }),
  getUptime: (routerId, params = {}) => api.get(`/dashboard/uptime/${routerId}`, { params }),
  getActivity: (params = {}) => api.get('/dashboard/activity', { params }),
  getSchedules: (params = {}) => api.get('/dashboard/schedules', { params }),
  getSystemStatus: () => api.get('/dashboard/system-status')
}

// =============================================================================
// Webhooks API
// =============================================================================
export const webhooksApi = {
  list: (params = {}) => api.get('/webhooks', { params }),
  get: (id) => api.get(`/webhooks/${id}`),
  create: (data) => api.post('/webhooks', data),
  update: (id, data) => api.put(`/webhooks/${id}`, data),
  delete: (id) => api.delete(`/webhooks/${id}`),
  test: (id, data) => api.post(`/webhooks/${id}/test`, data),
  getDeliveries: (id, params = {}) => api.get(`/webhooks/${id}/deliveries`, { params }),
  resendDelivery: (webhookId, deliveryId) => api.post(`/webhooks/${webhookId}/deliveries/${deliveryId}/resend`),
  getRecentDeliveries: (params = {}) => api.get('/webhooks/deliveries/recent', { params }),
  getEvents: () => api.get('/webhooks/events')
}

// =============================================================================
// Versions API
// =============================================================================
export const versionsApi = {
  get: () => api.get('/versions'),
  refresh: () => api.get('/versions/refresh')
}

// =============================================================================
// Discovery API (MNDP)
// =============================================================================
export const discoveryApi = {
  discover: (timeout = 5, force = false) =>
    api.get('/discovery', { params: { timeout, force } }),
  getCached: () => api.get('/discovery/cached'),
  clearCache: () => api.post('/discovery/clear-cache')
}

// =============================================================================
// WebSocket helpers
// =============================================================================
export const createTaskWebSocket = (taskId, onMessage, onError) => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/ws/tasks/${taskId}`

  const ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    console.log(`WebSocket connected for task ${taskId}`)
  }

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      onMessage(data)
    } catch (e) {
      console.error('WebSocket message parse error:', e)
    }
  }

  ws.onerror = (error) => {
    console.error('WebSocket error:', error)
    if (onError) onError(error)
  }

  ws.onclose = () => {
    console.log(`WebSocket closed for task ${taskId}`)
  }

  return ws
}

export const createStatusWebSocket = (onMessage) => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/ws/status`

  const ws = new WebSocket(wsUrl)

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      onMessage(data)
    } catch (e) {
      console.error('WebSocket message parse error:', e)
    }
  }

  return ws
}

export default api
