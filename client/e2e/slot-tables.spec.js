import { test, expect } from '@playwright/test'
import { signIn, daysFromToday, typeInPicker, choose } from './helpers.js'

// MH-02: an employee defines the tables and seats of a slot, and hikers can book only those seats
test('an employee creates a slot with its tables and a hiker sees its free seats', async ({ page, browser }) => {
  // the sample data has no slots two weeks from today
  const day = daysFromToday(14)
  await signIn(page, 'employee@mountainhut.com')
  await expect(page).toHaveURL(/\/home\/employee/)
  await page.getByRole('link', { name: /Times & tables/ }).click()

  await typeInPicker(page, 'Date', day)
  await typeInPicker(page, 'Starting time', '12:00')
  await typeInPicker(page, 'Ending time', '14:00')
  await choose(page, 'Meal type', 'Lunch')
  await page.getByRole('button', { name: '+ Add a table' }).click()
  await page.getByLabel('Table number 1').fill('T1')
  await page.getByLabel('Seats at table 1').fill('4')
  await page.getByRole('button', { name: '+ Add a table' }).click()
  await page.getByLabel('Table number 2').fill('T2')
  await page.getByLabel('Seats at table 2').fill('6')
  await page.getByRole('button', { name: 'Save time slot' }).click()
  await expect(page.getByText('Slot created successfully')).toBeVisible()

  // a hiker, in a browser of their own, finds the new slot with the 10 seats of its two tables
  const hiker = await (await browser.newContext()).newPage()
  await signIn(hiker, 'hiker3@example.com')
  await expect(hiker).toHaveURL(/\/home\/hiker/)
  await hiker.goto('/customer/book-table')
  await typeInPicker(hiker, 'Date', day)
  await choose(hiker, 'Service time', '12:00 – 14:00 · Lunch')
  await expect(hiker.getByText('10 seats remaining')).toBeVisible()
})
