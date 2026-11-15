import { test, expect } from '@playwright/test'
import { signIn, daysFromToday, typeInPicker, choose, bookTable } from './helpers.js'

// MH-01: a hiker books a table from the site, from the login to the confirmation
test('a hiker books a table and finds it in the booking history', async ({ page }) => {
  await signIn(page, 'hiker2@example.com')
  await expect(page).toHaveURL(/\/home\/hiker/)

  // the sample data has a dinner slot one week from today, with free tables
  await bookTable(page, { date: daysFromToday(7), time: '19:00 – 20:30 · Dinner', guests: 3 })

  const confirmation = page.getByRole('status', { name: 'Your table is reserved' })
  await expect(confirmation).toContainText('Table')
  const reference = (await confirmation.locator('strong').first().textContent()).trim()
  expect(reference).toMatch(/^MH-\d{8}-[A-Z0-9]+$/)

  await page.goto('/customer/reservations')
  const booking = page.getByRole('listitem').filter({ hasText: reference })
  await expect(booking).toContainText('3 guests · CONFIRMED')
})

test('a party larger than the free seats is refused, not booked with fewer guests', async ({ page }) => {
  await signIn(page, 'hiker3@example.com')
  await expect(page).toHaveURL(/\/home\/hiker/)
  await page.goto('/customer/book-table')

  await typeInPicker(page, 'Date', daysFromToday(7))
  await choose(page, 'Service time', '19:00 – 20:30 · Dinner')
  const guests = page.getByRole('spinbutton', { name: 'Number of guests' })
  await guests.fill('500')
  await guests.press('Tab')

  await expect(guests).toHaveValue('500')
  await expect(page.getByText(/Only \d+ seats remain for this time/)).toBeVisible()
  await expect(page.getByRole('button', { name: 'Confirm booking' })).toBeDisabled()
})
