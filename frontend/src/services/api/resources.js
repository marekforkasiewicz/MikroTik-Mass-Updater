import api, { resetRefreshState } from './client'

export const authApi = {
  async login(username, password) {
    const response = await api.post(
      '/auth/login',
      new URLSearchParams({ username, password }),
      { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
    )
    resetRefreshState()
    return response
  },
  loginJson: (username, password) => api.post('/auth/login/json', { username, password }),
  logout: () => api.post('/auth/logout'),
  refresh: () => api.post('/auth/refresh'),
  me: () => api.get('/auth/me'),
  changePassword: (currentPassword, newPassword) =>
    api.post('/auth/change-password', { current_password: currentPassword, new_password: newPassword })
}

export const usersApi = {
  list: (params = {}) => api.get('/users', { params }),
  get: (id) => api.get(`/users/${id}`),
  create: (data) => api.post('/users', data),
  update: (id, data) => api.put(`/users/${id}`, data),
  delete: (id) => api.delete(`/users/${id}`),
  listApiKeys: () => api.get('/users/me/api-keys'),
  createApiKey: (data) => api.post('/users/me/api-keys', data),
  deleteApiKey: (id) => api.delete(`/users/me/api-keys/${id}`),
  revokeApiKey: (id) => api.post(`/users/me/api-keys/${id}/revoke`)
}

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

export const groupsApi = {
  list: (params = {}) => api.get('/groups', { params }),
  getTree: () => api.get('/groups/tree'),
  get: (id) => api.get(`/groups/${id}`),
  create: (data) => api.post('/groups', data),
  update: (id, data) => api.put(`/groups/${id}`, data),
  delete: (id) => api.delete(`/groups/${id}`),
  addRouters: (id, routerIds) => api.post(`/groups/${id}/routers`, { router_ids: routerIds }),
  removeRouters: (id, routerIds) => api.delete(`/groups/${id}/routers`, { data: { router_ids: routerIds } }),
  getRouters: (id, includeChildren = false) =>
    api.get(`/groups/${id}/routers`, { params: { include_children: includeChildren } }),
  search: (query) => api.get(`/groups/search/${query}`)
}

export const scanApi = {
  quickScan: (routerIds = null) => api.post('/scan/quick', routerIds ? { router_ids: routerIds } : null),
  fullScan: (routerIds = null) => api.post('/scan/full', routerIds ? { router_ids: routerIds } : null),
  quickScanSingle: (routerId) => api.get(`/scan/quick/single/${routerId}`),
  checkFirmware: (routerId) => api.get(`/scan/firmware/${routerId}`)
}

export const taskApi = {
  list: (params = {}) => api.get('/tasks', { params }),
  get: (id) => api.get(`/tasks/${id}`),
  create: (data) => api.post('/tasks', data),
  cancel: (id) => api.post(`/tasks/${id}/cancel`),
  delete: (id) => api.delete(`/tasks/${id}`),
  startUpdate: (config) => api.post('/tasks/update', config)
}

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
  describeCron: (cron) => api.get('/schedules/cron-describe', { params: { cron } })
}

export const notificationsApi = {
  listChannels: () => api.get('/notifications/channels'),
  getChannel: (id) => api.get(`/notifications/channels/${id}`),
  createChannel: (data) => api.post('/notifications/channels', data),
  updateChannel: (id, data) => api.put(`/notifications/channels/${id}`, data),
  deleteChannel: (id) => api.delete(`/notifications/channels/${id}`),
  testChannel: (id, message) => api.post(`/notifications/channels/${id}/test`, { message }),
  listRules: (params = {}) => api.get('/notifications/rules', { params }),
  createRule: (data) => api.post('/notifications/rules', data),
  updateRule: (id, data) => api.put(`/notifications/rules/${id}`, data),
  deleteRule: (id) => api.delete(`/notifications/rules/${id}`),
  getLogs: (params = {}) => api.get('/notifications/logs', { params }),
  getEventTypes: () => api.get('/notifications/event-types')
}

export const backupsApi = {
  list: (params = {}) => api.get('/backups', { params }),
  get: (id) => api.get(`/backups/${id}`),
  create: (data) => api.post('/backups', data),
  createBulk: (data) => api.post('/backups/bulk', data),
  delete: (id) => api.delete(`/backups/${id}`),
  download: (id) => api.get(`/backups/${id}/download`, { responseType: 'blob' }),
  restore: (data) => api.post('/backups/restore', data),
  getRollbackLogs: (params = {}) => api.get('/backups/rollback-logs', { params }),
  cleanup: (days = 30) => api.post('/backups/cleanup', null, { params: { days } })
}

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

export const monitoringApi = {
  getOverview: () => api.get('/monitoring/overview'),
  getConfig: () => api.get('/monitoring/config'),
  updateConfig: (data) => api.put('/monitoring/config', data),
  getRouterConfig: (routerId) => api.get(`/monitoring/routers/${routerId}/config`),
  createRouterConfig: (routerId, data) => api.post(`/monitoring/routers/${routerId}/config`, data),
  triggerCheck: (routerId, checkType = 'full') =>
    api.post(`/monitoring/routers/${routerId}/check`, null, { params: { check_type: checkType } }),
  getHealthHistory: (routerId, params = {}) =>
    api.get(`/monitoring/routers/${routerId}/history`, { params }),
  getAlerts: (params = {}) => api.get('/monitoring/alerts', { params }),
  getActiveAlerts: () => api.get('/monitoring/alerts/active'),
  acknowledgeAlerts: (alertIds) => api.post('/monitoring/alerts/acknowledge', { alert_ids: alertIds }),
  resolveAlerts: (alertIds) => api.post('/monitoring/alerts/resolve', { alert_ids: alertIds }),
  getAlert: (id) => api.get(`/monitoring/alerts/${id}`)
}

export const reportsApi = {
  generate: (data) => api.post('/reports', data),
  list: () => api.get('/reports'),
  download: (filename) => api.get(`/reports/download/${filename}`, { responseType: 'blob' }),
  delete: (filename) => api.delete(`/reports/${filename}`),
  quickInventory: (format = 'csv') => api.get('/reports/quick/inventory', { params: { format } }),
  quickHealth: (format = 'csv') => api.get('/reports/quick/health', { params: { format } })
}

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

export const versionsApi = {
  get: () => api.get('/versions'),
  refresh: () => api.get('/versions/refresh')
}

export const discoveryApi = {
  discover: (timeout = 5, force = false) => api.get('/discovery', { params: { timeout, force } }),
  getCached: () => api.get('/discovery/cached'),
  clearCache: () => api.post('/discovery/clear-cache')
}

export const templatesApi = {
  list: (params = {}) => api.get('/templates', { params }),
  get: (id) => api.get(`/templates/${id}`),
  create: (data) => api.post('/templates', data),
  update: (id, data) => api.put(`/templates/${id}`, data),
  delete: (id) => api.delete(`/templates/${id}`),
  getCategories: () => api.get('/templates/categories'),
  validate: (content) => api.post('/templates/validate', { content }),
  validateExisting: (id) => api.post(`/templates/${id}/validate`),
  preview: (id, data = {}) => api.post(`/templates/${id}/preview`, data),
  deploy: (id, data) => api.post(`/templates/${id}/deploy`, data),
  listProfiles: (params = {}) => api.get('/templates/profiles', { params }),
  getProfile: (id) => api.get(`/templates/profiles/${id}`),
  createProfile: (data) => api.post('/templates/profiles', data),
  updateProfile: (id, data) => api.put(`/templates/profiles/${id}`, data),
  deleteProfile: (id) => api.delete(`/templates/profiles/${id}`),
  getProfileRouters: (id) => api.get(`/templates/profiles/${id}/routers`),
  listDeployments: (params = {}) => api.get('/templates/deployments', { params }),
  getDeployment: (id) => api.get(`/templates/deployments/${id}`)
}

export const complianceApi = {
  exportConfig: (routerId, hideSensitive = true) =>
    api.get(`/compliance/routers/${routerId}/export`, { params: { hide_sensitive: hideSensitive } }),
  diffConfigs: (data) => api.post('/compliance/diff', data),
  listBaselines: (params = {}) => api.get('/compliance/baselines', { params }),
  getBaseline: (id) => api.get(`/compliance/baselines/${id}`),
  createBaseline: (data) => api.post('/compliance/baselines', data),
  updateBaseline: (id, data) => api.put(`/compliance/baselines/${id}`, data),
  deleteBaseline: (id) => api.delete(`/compliance/baselines/${id}`),
  runCheck: (data) => api.post('/compliance/check', data),
  listChecks: (params = {}) => api.get('/compliance/checks', { params }),
  getCheck: (id) => api.get(`/compliance/checks/${id}`),
  getSummary: (baselineId = null) =>
    api.get('/compliance/summary', { params: baselineId ? { baseline_id: baselineId } : {} })
}

export const topologyApi = {
  getMap: () => api.get('/topology/map'),
  getNeighbors: (routerId) => api.get(`/topology/neighbors/${routerId}`),
  refreshNeighbors: (routerId) => api.post(`/topology/neighbors/${routerId}/refresh`),
  refreshAllNeighbors: () => api.post('/topology/neighbors/refresh-all'),
  saveLayout: (layout) => api.post('/topology/layout', layout),
  getLayout: () => api.get('/topology/layout')
}
