import { test, expect } from '@playwright/test'
import { daysFromToday, typeInPicker } from './helpers.js'

// MH-04: anyone, also without an account, sees if there is room for the group and how it would be seated.
// The sample data has four slots ten days from today: 3 tables of 2 at 12:00, free seats 2 + 3 + 1 at 13:00,
// a full dinner at 19:00 and a closed one at 20:30.
test('a guest sees the free service times of a day and how the group would be seated', async ({ page }) => {
  await page.goto('/availability')
  await typeInPicker(page, 'Date', daysFromToday(10))
  await page.getByRole('spinbutton', { name: 'Party size' }).fill('6')

  // the full and the closed dinner are not offered
  await expect(page.getByRole('button', { name: /12:00–13:00/ })).toContainText('6 seats left')
  await expect(page.getByRole('button', { name: /13:00–14:00/ })).toContainText('6 seats left')
  await expect(page.getByRole('button', { name: /19:00|20:30/ })).toHaveCount(0)

  // the example of the PO: a party of 6 fits on 3 tables of 2
  await page.getByRole('button', { name: /12:00–13:00/ }).click()
  await expect(page.getByText('There is availability')).toBeVisible()
  await expect(page.getByText('2 + 2 + 2 seats')).toBeVisible()
  // without an account the page asks to sign in before booking
  await expect(page.getByRole('link', { name: /Sign in to book/ })).toBeVisible()
})

test('a group larger than the free seats finds no service time', async ({ page }) => {
  const day = daysFromToday(10)
  await page.goto('/availability')
  await typeInPicker(page, 'Date', day)
  await page.getByRole('spinbutton', { name: 'Party size' }).fill('7')

  await expect(page.getByText(`No available service times for ${day}.`)).toBeVisible()
})
