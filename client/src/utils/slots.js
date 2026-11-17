// GET /api/slots answers with a list of SlotDetail, in camelCase
export function normalizeSlots(response) {
  return Array.isArray(response) ? response : []
}

export function getSlotId(slot) {
  return slot.slotId
}

export function getSlotStart(slot) {
  return slot.startTime
}

export function getSlotEnd(slot) {
  return slot.endTime
}

export function formatSlotLabel(slot) {
  return `${slot.startTime} – ${slot.endTime}${slot.mealType ? ` · ${slot.mealType}` : ''}`
}

// today in the browser's time zone, as YYYY-MM-DD (toISOString alone would give the UTC day)
export function localDateString() {
  const now = new Date()
  return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 10)
}

// only a hint for the page: the server checks the deadline in Europe/Rome time and decides
export function isAtLeast(date, time, ms) {
  return Date.parse(`${date}T${time}`) - Date.now() >= ms
}
