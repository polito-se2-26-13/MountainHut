// password of every account of the sample data, server/migrations/002_seed_data.sql
const PASSWORD = 'Password123!'

export async function signIn(page, email) {
  await page.goto('/login')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill(PASSWORD)
  await page.getByRole('button', { name: 'Sign in' }).click()
}

// date in the YYYY-MM-DD format, counted like the sample data does (SQLite date('now', '+7 days'))
export function daysFromToday(days) {
  return new Date(Date.now() + days * 24 * 60 * 60 * 1000).toISOString().slice(0, 10)
}

// the date and time pickers of antd take what you type once you press Enter
export async function typeInPicker(page, label, value) {
  const field = page.getByRole('textbox', { name: label })
  await field.click()
  await field.press('Control+A')
  await field.pressSequentially(value)
  await field.press('Enter')
}

// a Select of antd: open it, then click the option with that text
export async function choose(page, label, option) {
  await page.getByLabel(label).click()
  await page.getByTitle(option).click()
}

export async function bookTable(page, { date, time, guests }) {
  await page.goto('/customer/book-table')
  await typeInPicker(page, 'Date', date)
  await choose(page, 'Service time', time)
  await page.getByRole('spinbutton', { name: 'Number of guests' }).fill(String(guests))
  await page.getByRole('button', { name: 'Confirm booking' }).click()
}
