export function normalizeSlots(response) {
  if (Array.isArray(response)) return response
  if (Array.isArray(response?.slots)) return response.slots
  if (Array.isArray(response?.items)) return response.items
  return []
}

export function getSlotId(slot) {
  return slot.slot_id ?? slot.slotId ?? slot.id
}

export function getSlotStart(slot) {
  return slot.start_time ?? slot.startTime ?? slot.time
}

export function getSlotEnd(slot) {
  return slot.end_time ?? slot.endTime ?? ''
}

export function formatSlotLabel(slot) {
  const end = getSlotEnd(slot)
  const meal = slot.meal_type ?? slot.mealType
  return `${getSlotStart(slot)}${end ? ` – ${end}` : ''}${meal ? ` · ${meal}` : ''}`
}

// only a hint for the page: the server checks the deadline in Europe/Rome time and decides
export function isAtLeast(date, time, ms) {
  return Date.parse(`${date}T${time}`) - Date.now() >= ms
}
