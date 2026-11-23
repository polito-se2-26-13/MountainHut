import { test, expect } from '@playwright/test'
import { signIn, daysFromToday, typeInPicker, choose } from './helpers.js'

// MH-05: when booking, a hiker writes the dietary needs and allergies of the group, and they stay with the booking
test('a hiker books with an allergy and finds the requirements in the booking', async ({ page }) => {
  await signIn(page, 'hiker3@example.com')
  await expect(page).toHaveURL(/\/home\/hiker/)

  await page.goto('/customer/book-table')
  await typeInPicker(page, 'Date', daysFromToday(7))
  await choose(page, 'Service time', '12:00 – 13:00 · Lunch')
  await page.getByRole('spinbutton', { name: 'Number of guests' }).fill('3')
  // the example of the story: each requirement has its own allergy box
  await page.getByLabel('Requirement 1 description').fill('1 vegan, peanut allergy')
  await page.getByRole('checkbox', { name: 'This requirement involves an allergy' }).check()
  await page.getByRole('button', { name: 'Add requirement' }).click()
  await page.getByLabel('Requirement 2 description').fill('2 vegetarians')
  await page.getByRole('button', { name: 'Confirm booking' }).click()

  const confirmation = page.getByRole('status', { name: 'Your table is reserved' })
  const reference = (await confirmation.locator('strong').first().textContent()).trim()

  await page.goto('/customer/reservations')
  const booking = page.getByRole('listitem').filter({ hasText: reference })
  await expect(booking).toContainText('Requests: 1 vegan, peanut allergy, 2 vegetarians')

  // the allergy is kept too: the change form has the box ticked only on the first requirement
  await booking.getByRole('button', { name: 'Modify booking' }).click()
  const allergy = page.getByRole('dialog', { name: 'Modify booking' }).getByRole('checkbox', { name: 'This requirement involves an allergy' })
  await expect(allergy.nth(0)).toBeChecked()
  await expect(allergy.nth(1)).not.toBeChecked()
})
