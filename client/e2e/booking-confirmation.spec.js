import { test, expect } from '@playwright/test'
import { signIn, daysFromToday, bookTable } from './helpers.js'

// MH-03: after booking, the hiker sees the confirmation with the details of the booking.
// The text of the email is checked by the integration test test_confirmation_email_follows_the_product_owner:
// here the mail of the test server goes to localhost:1, so no email leaves.
test('the confirmation shows reference, date, time and guests of the booking', async ({ page }) => {
  const day = daysFromToday(7)
  await signIn(page, 'hiker1@example.com')
  await expect(page).toHaveURL(/\/home\/hiker/)

  await bookTable(page, { date: day, time: '19:00 – 20:30 · Dinner', guests: 2 })

  const confirmation = page.getByRole('status', { name: 'Your table is reserved' })
  await expect(confirmation).toContainText(`${day} · 19:00–20:30 · 2 guests`)
  const reference = (await confirmation.locator('strong').first().textContent()).trim()
  expect(reference).toMatch(/^MH-\d{8}-[A-Z0-9]+$/)

  // the same details are kept by the server: the booking history reads them back
  await page.goto('/customer/reservations')
  const booking = page.getByRole('listitem').filter({ hasText: reference })
  await expect(booking).toContainText(`${day} · 19:00–20:30`)
  await expect(booking).toContainText('2 guests · CONFIRMED')
  // by default the confirmation goes to the email of the account
  await expect(booking).toContainText('hiker1@example.com')
})
