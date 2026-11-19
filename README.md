# Mountain Hut

Software Engineering II, PoliTo 2026/27, team 13.

```
client/   frontend, React + Vite
server/   backend, FastAPI + SQLAlchemy + SQLite
```

## Run the backend

Windows, in PowerShell:

```
cd server
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd ..
python -m server.scripts.db_setup migrate
uvicorn server.main:app --reload
```

If PowerShell says that running scripts is disabled, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once and open a new terminal. If `python` opens the Microsoft Store, use `py` instead.

macOS and Linux:

```
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..
python -m server.scripts.db_setup migrate
uvicorn server.main:app --reload
```

The first `migrate` creates the database with the sample data. The server does not create the tables by itself, so run it again after pulling new migrations. The API runs on http://localhost:8000 and its documentation on http://localhost:8000/docs.

## Database setup & migrations

The database uses SQLite and SQLAlchemy with foreign key constraints enabled.

Run commands from the project root (with Python virtual environment active):

- **Apply pending migrations:**
  ```powershell
  python -m server.scripts.db_setup migrate
  ```
- **Seed sample data (users, tables, slots, bookings):** `migrate` already loads it, because `002_seed_data.sql` is one of the migrations. `seed` loads it only into a database that has the tables but not the data yet.
  ```powershell
  python -m server.scripts.db_setup seed
  ```
- **Reset database (drop all, re-create, and seed):**
  ```powershell
  python -m server.scripts.db_setup reset
  ```
- **Inspect database status and row counts:**
  ```powershell
  python -m server.scripts.db_setup status
  ```

Complete SQL DDL and seed scripts are also available in `doc/sql.txt` and `server/migrations/`.

## Run the frontend

```
cd client
npm install
npm run dev
```

The app runs on http://localhost:5173. Calls to `/api/...` are forwarded to the backend, so start both.

## Run with Docker

The whole app runs in one container. Nginx serves the pages and passes `/api` to the backend, and the database is kept in the Docker volume `mountainhut-data`. A GitHub Action builds the image and publishes it as `ghcr.io/polito-se2-26-13/mountainhut`: the release of each sprint, from `main`, is tagged `latest`, the latest work, from `dev`, is tagged `dev`, and every image is also tagged with its commit id.

1. Install Docker Desktop, which includes Docker Compose, and start it.
2. Put the secrets in `server/.env`. They are not on GitHub: the teachers find the file in `Team13-secrets.zip`, in the "Elaborati" section of the portal, and extract it into the project root so that it becomes `server/.env`. Anyone else copies `server/.env.example` to `server/.env` and sets `SECRET_KEY` to a long random text, because without it the logins end at every restart of the container. `SMTP_EMAIL` and `SMTP_PASSWORD` are the account that sends the confirmation emails; without them the bookings work but no email is sent.
3. From the project root, start the published image:

   ```
   docker compose -f docker-compose.release.yml pull
   docker compose -f docker-compose.release.yml up -d
   ```

   To build the image from this code instead, run `docker compose up --build -d`.
4. Open http://localhost:3000. http://localhost:3000/api/health answers `{"status":"ok"}`.

At every start the container applies the migrations it has not applied yet, so a new image keeps the data of the volume. To update, run `pull` and `up -d` again. `docker compose -f docker-compose.release.yml down` stops the app and keeps the data, while `down -v` also deletes the database.

## Test users

The sample data has one user for each role, all with the password `Password123!`.

| Role | Email |
|---|---|
| Warden | warden@mountainhut.com |
| Employee | employee@mountainhut.com |
| Hiker | hiker1@example.com |
| Hiker | hiker2@example.com |
| Hiker | hiker3@example.com |

## Tests

With the virtual environment active:

```
cd server
pytest
```

The end-to-end tests are in `client/e2e` and use Playwright. They start the backend and the frontend by themselves, on the ports 8100 and 5199, and every run puts the sample data back in `server/mountainHut.sqlite`. They need `server/.venv`, created as written above.

```
cd client
npx playwright install chromium
npm run e2e
```

`npx playwright install chromium` is needed only the first time.

## Branches

- `main` holds what we show at the sprint review. It only receives the merge of `dev` at the end of each sprint.
- `dev` is where the work comes together. Nobody pushes to it directly.
- Every task gets its own short branch, created from an up to date `dev` and named after its YouTrack card: `MH-<number>-<short-description>`, for example `MH-34-slot-api`.
- Commit messages start with the card ID too, for example `MH-34 add slot API`.
- When the task is done, open a pull request into `dev`. Another member reviews and approves it, then it is merged and the branch is deleted.

## Licence
- *GNU General Public License version 3.0*<br/>
We chose GPL-3.0 because it prevents commercial exploitation of our work. It forces anyone who benefits from or modifies our software to share their source code openly under the exact same terms, protecting our community's collective contribution from being hidden away in closed-source software.
