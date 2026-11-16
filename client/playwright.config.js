import { defineConfig } from '@playwright/test'
import process from 'node:process'

// the python of server/.venv, created as written in the README
const python = process.platform === 'win32' ? 'server\\.venv\\Scripts\\python.exe' : 'server/.venv/bin/python'

export default defineConfig({
  testDir: './e2e',
  // the tests share one database, so they run one at a time
  workers: 1,
  use: { baseURL: 'http://localhost:5199' },
  // other ports than the usual 8000 and 5173, so the servers you already have open don't get in the way
  webServer: [
    {
      // every run starts from the sample data; the mail goes to localhost:1, where nothing answers, so no real email leaves
      command: `${python} -m server.scripts.db_setup reset && ${python} -m uvicorn server.main:app --port 8100`,
      cwd: '..',
      url: 'http://localhost:8100/docs',
      env: { SMTP_HOST: 'localhost', SMTP_PORT: '1' },
    },
    {
      command: 'npx vite --port 5199 --strictPort',
      url: 'http://localhost:5199',
      env: { VITE_BACKEND_URL: 'http://localhost:8100' },
    },
  ],
})
