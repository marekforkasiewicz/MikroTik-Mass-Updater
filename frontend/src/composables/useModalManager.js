import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { Modal } from 'bootstrap'

/**
 * Composable for managing Bootstrap modals
 * Centralizes modal initialization and lifecycle
 */
export function useModalManager() {
  const modals = ref({})
  const modalInstances = {}

  const registerModal = (name, elementRef) => {
    modals.value[name] = elementRef
  }

  const initModals = () => {
    nextTick(() => {
      Object.entries(modals.value).forEach(([name, elementRef]) => {
        if (elementRef.value && !modalInstances[name]) {
          modalInstances[name] = new Modal(elementRef.value)
        }
      })
    })
  }

  const showModal = (name) => {
    modalInstances[name]?.show()
  }

  const hideModal = (name) => {
    modalInstances[name]?.hide()
  }

  const destroyModals = () => {
    Object.values(modalInstances).forEach(modal => {
      try {
        modal?.dispose()
      } catch (e) {
        // Modal already disposed
      }
    })
  }

  onMounted(() => {
    initModals()
  })

  onUnmounted(() => {
    destroyModals()
  })

  return {
    registerModal,
    initModals,
    showModal,
    hideModal
  }
}
