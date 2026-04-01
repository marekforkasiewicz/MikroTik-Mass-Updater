function buildWebSocketUrl(path) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}${path}`
}

function createJsonWebSocket(path, { onMessage, onError, onOpen, onClose } = {}) {
  const ws = new WebSocket(buildWebSocketUrl(path))

  if (onOpen) {
    ws.onopen = onOpen
  }

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      onMessage?.(data)
    } catch (error) {
      console.error('WebSocket message parse error:', error)
    }
  }

  ws.onerror = (error) => {
    console.error('WebSocket error:', error)
    onError?.(error)
  }

  if (onClose) {
    ws.onclose = onClose
  }

  return ws
}

export function createTaskWebSocket(taskId, onMessage, onError) {
  return createJsonWebSocket(`/ws/tasks/${taskId}`, {
    onMessage,
    onError,
    onOpen: () => console.log(`WebSocket connected for task ${taskId}`),
    onClose: () => console.log(`WebSocket closed for task ${taskId}`)
  })
}

export function createStatusWebSocket(onMessage, onError) {
  return createJsonWebSocket('/ws/status', {
    onMessage,
    onError
  })
}

export function createTemplateDeployWebSocket(taskId, onMessage, onError) {
  return createTaskWebSocket(taskId, onMessage, onError)
}
