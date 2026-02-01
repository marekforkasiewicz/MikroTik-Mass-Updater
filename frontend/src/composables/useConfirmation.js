import { ref } from 'vue'

/**
 * Composable for managing confirmation dialogs
 * Eliminates repeated confirmation logic across components
 */
export function useConfirmation() {
  const showConfirm = ref(false)
  const confirmTitle = ref('')
  const confirmMessage = ref('')
  const confirmVariant = ref('danger')
  const confirmButtonText = ref('Confirm')
  const confirmLoading = ref(false)

  let resolvePromise = null

  const confirm = (message, options = {}) => {
    return new Promise((resolve) => {
      confirmTitle.value = options.title || 'Confirm'
      confirmMessage.value = message
      confirmVariant.value = options.variant || 'danger'
      confirmButtonText.value = options.buttonText || 'Confirm'
      showConfirm.value = true
      resolvePromise = resolve
    })
  }

  const handleConfirm = async (callback) => {
    confirmLoading.value = true
    try {
      if (callback) {
        await callback()
      }
      resolvePromise?.(true)
    } finally {
      confirmLoading.value = false
      showConfirm.value = false
    }
  }

  const handleCancel = () => {
    showConfirm.value = false
    resolvePromise?.(false)
  }

  return {
    showConfirm,
    confirmTitle,
    confirmMessage,
    confirmVariant,
    confirmButtonText,
    confirmLoading,
    confirm,
    handleConfirm,
    handleCancel
  }
}
