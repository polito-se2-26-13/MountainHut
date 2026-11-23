import { test, expect } from '@playwright/test'
import { signIn, daysFromToday, choose } from './helpers.js'

// MH-06: a hiker changes a booking more than 48 hours before the meal.
// The sample data has two lunch bookings one week from today: Alex for 4 people and Elena for 2, both at 12:00.
test('a hiker changes the time and the guests of a booking and sees the new details', async ({ page }) => {
  await signIn(page, 'hiker1@example.com')
  await expect(page).toHaveURL(/\/home\/hiker/)
  await page.goto('/customer/reservations')

  const booking = page.getByRole('listitem').filter({ hasText: 'MH-20261030-ALX01' })
  await booking.getByRole('button', { name: 'Modify booking' }).click()
  const dialog = page.getByRole('dialog', { name: 'Modify booking' })
  await choose(page, 'Service time', '13:00 – 14:00 · Lunch')
  await dialog.getByRole('spinbutton', { name: 'Number of guests' }).fill('5')
  await dialog.getByRole('button', { name: 'Save changes' }).click()

  await expect(page.getByText('Booking updated. A confirmation email is on its way.')).toBeVisible()
  await expect(booking).toContainText(`${daysFromToday(7)} · 13:00–14:00`)
  await expect(booking).toContainText('5 guests · CONFIRMED')
})

test('a change that does not fit is refused and the booking stays as it was', async ({ page }) => {
  await signIn(page, 'hiker2@example.com')
  await expect(page).toHaveURL(/\/home\/hiker/)
  await page.goto('/customer/reservations')

  const booking = page.getByRole('listitem').filter({ hasText: 'MH-20261030-ELN02' })
  await booking.getByRole('button', { name: 'Modify booking' }).click()
  const dialog = page.getByRole('dialog', { name: 'Modify booking' })
  await dialog.getByRole('spinbutton', { name: 'Number of guests' }).fill('500')
  await dialog.getByRole('button', { name: 'Save changes' }).click()

  await expect(dialog.getByText('Your original booking remains unchanged.')).toBeVisible()
  await dialog.getByRole('button', { name: 'Cancel' }).click()
  await expect(booking).toContainText('2 guests · CONFIRMED')
})
