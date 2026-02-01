/**
 * Shared badge/status utilities
 */

export function getStatusBadgeClass(status) {
  const classes = {
    // General statuses
    success: 'badge bg-success',
    completed: 'badge bg-success',
    ok: 'badge bg-success',
    active: 'badge bg-success',
    online: 'badge bg-success',
    enabled: 'badge bg-success',

    // Warning statuses
    warning: 'badge bg-warning text-dark',
    pending: 'badge bg-warning text-dark',
    in_progress: 'badge bg-warning text-dark',
    running: 'badge bg-primary',
    retrying: 'badge bg-info',

    // Error statuses
    failed: 'badge bg-danger',
    error: 'badge bg-danger',
    critical: 'badge bg-danger',
    offline: 'badge bg-danger',

    // Neutral statuses
    disabled: 'badge bg-secondary',
    cancelled: 'badge bg-secondary',
    unknown: 'badge bg-secondary'
  }
  return classes[status?.toLowerCase()] || 'badge bg-secondary'
}

export function getStatusIcon(status) {
  const icons = {
    success: 'bi-check-circle-fill',
    completed: 'bi-check-circle-fill',
    ok: 'bi-check-circle-fill',
    online: 'bi-check-circle-fill',

    pending: 'bi-hourglass',
    running: 'bi-gear',
    in_progress: 'bi-arrow-repeat',

    failed: 'bi-x-circle-fill',
    error: 'bi-x-circle-fill',
    critical: 'bi-exclamation-triangle-fill',
    offline: 'bi-x-circle-fill',

    cancelled: 'bi-slash-circle',
    unknown: 'bi-question-circle'
  }
  return icons[status?.toLowerCase()] || 'bi-circle'
}

export function getChannelBadgeClass(channel) {
  if (!channel) return 'bg-secondary'
  const ch = channel.toLowerCase()
  if (ch.includes('stable')) return 'bg-success'
  if (ch.includes('long-term')) return 'bg-info'
  if (ch.includes('testing')) return 'bg-warning text-dark'
  if (ch.includes('development')) return 'bg-danger'
  return 'bg-secondary'
}

export function getRoleBadgeClass(role) {
  const badges = {
    admin: 'badge bg-danger',
    operator: 'badge bg-primary',
    viewer: 'badge bg-secondary'
  }
  return badges[role] || 'badge bg-secondary'
}

export function getBackupTypeBadge(type) {
  const badges = {
    config: 'badge bg-primary',
    export: 'badge bg-info',
    cloud: 'badge bg-success'
  }
  return badges[type] || 'badge bg-secondary'
}

export function getSeverityIcon(severity) {
  const icons = {
    critical: 'bi bi-exclamation-triangle-fill text-danger',
    warning: 'bi bi-exclamation-circle-fill text-warning',
    info: 'bi bi-info-circle-fill text-info'
  }
  return icons[severity] || 'bi bi-bell text-secondary'
}
