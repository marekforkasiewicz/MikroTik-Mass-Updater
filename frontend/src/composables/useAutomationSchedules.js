import { computed, ref } from 'vue'
import cronstrue from 'cronstrue'

export function useAutomationSchedules({ schedulesStore }) {
  const schedules = computed(() => schedulesStore.schedules)
  const showScheduleModal = ref(false)
  const editingSchedule = ref(null)
  const scheduleForm = ref({
    name: '',
    task_type: 'scan',
    cron_expression: '0 2 * * *',
    enabled: true
  })

  function getCronDescription(cron) {
    if (!cron) return ''
    try {
      return cronstrue.toString(cron)
    } catch {
      return 'Invalid cron expression'
    }
  }

  function resetScheduleForm() {
    editingSchedule.value = null
    scheduleForm.value = {
      name: '',
      task_type: 'scan',
      cron_expression: '0 2 * * *',
      enabled: true
    }
  }

  function editSchedule(schedule, showModal) {
    editingSchedule.value = schedule
    scheduleForm.value = { ...schedule }
    showModal?.()
  }

  async function saveSchedule() {
    if (editingSchedule.value) {
      await schedulesStore.updateSchedule(editingSchedule.value.id, scheduleForm.value)
    } else {
      await schedulesStore.createSchedule(scheduleForm.value)
    }
  }

  function toggleSchedule(schedule) {
    if (schedule.enabled) {
      schedulesStore.disableSchedule(schedule.id)
    } else {
      schedulesStore.enableSchedule(schedule.id)
    }
  }

  return {
    schedules,
    showScheduleModal,
    editingSchedule,
    scheduleForm,
    getCronDescription,
    resetScheduleForm,
    editSchedule,
    saveSchedule,
    toggleSchedule
  }
}
