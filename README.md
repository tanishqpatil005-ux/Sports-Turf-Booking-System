# PlayField: Sports Turf Booking & Player Matchmaking

A student-project demo built from the supplied SRS and SQLite database. It includes a responsive web frontend, a Python FastAPI REST backend, and database-backed facilities, slots, bookings, player profiles, open games, and joining a game.

## Stack
- Frontend: HTML, CSS, vanilla JavaScript
- Backend: Python + FastAPI + Uvicorn
- Database: SQLite (uses the supplied `sports_turf.db`)
- REST API: `/api/...`

## Requirements
Install Python 3.10 or later. The project is designed to be easy to open in Google Antigravity IDE or VS Code.

## Run locally (Windows PowerShell)
1. Extract the ZIP file to a folder, for example `E:\sports_turf_website`.
2. Open that folder in Antigravity IDE: **File → Open Folder**.
3. Open the IDE terminal (**Terminal → New Terminal**).
4. Create a virtual environment:
   ```powershell
   py -m venv .venv
   ```
5. Activate it:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
   If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal, then activate again. You can also skip activation and run `.venv\Scripts\python.exe -m pip install -r requirements.txt`.
6. Install dependencies:
   ```powershell
   python -m pip install -r requirements.txt
   ```
7. Start the backend and website:
   ```powershell
   python -m uvicorn main:app --reload
   ```
8. Open **http://127.0.0.1:8000** in your browser.
9. API documentation is at **http://127.0.0.1:8000/docs**. Health check: **http://127.0.0.1:8000/api/health**.

## Features implemented
- Browse/filter facilities by sport and text query
- Display upcoming available slots, optionally filtered by date
- Create player profiles
- Book an available future slot; booking and slot status are saved in SQLite
- Create an open game from a confirmed booking
- Browse open games and join a game
- Dashboard counts for facilities, slots, players, and open games
- Basic validation, duplicate prevention, and database transaction around booking/joining

## API routes
| Method | Route | Purpose |
|---|---|---|
| GET | `/api/health` | Check backend |
| GET | `/api/stats` | Dashboard counts |
| GET | `/api/facilities?sport=Football&q=andheri` | Browse/filter facilities |
| GET | `/api/slots?facility_id=1&slot_date=YYYY-MM-DD` | Upcoming available slots |
| GET | `/api/players` | List demo players |
| POST | `/api/players` | Create profile |
| GET | `/api/bookings` | List bookings |
| POST | `/api/bookings` | Create booking |
| GET | `/api/games` | Browse open games |
| POST | `/api/games` | Create open game |
| POST | `/api/games/{game_id}/join` | Join a game |
| GET | `/api/games/{game_id}/roster` | View confirmed roster |

## Demo data and limitations
- The supplied database is copied into this project. If it has no upcoming slots, the app adds a small set of future demo slots while retaining existing rows.
- Existing example player profiles are displayed as demo data. You can create additional profiles from the website.
- Booking confirmation is simulated. **No real payment is collected**, and this version does not integrate a payment gateway, SMS, email, GPS/maps, OTP verification, production authentication, or owner/admin permissions.
- The original SRS describes PostgreSQL and third-party integrations for a production deployment. This implementation keeps SQLite to match the uploaded project database and make local setup straightforward.
- This is a local prototype, not a production-secure booking service. Do not put real customer personal/payment data into it.

## Suggested presentation flow
1. Show the home page and facility search.
2. Select a slot and make a demo booking.
3. Explain that JavaScript sends a JSON request to FastAPI.
4. Show `/docs` and test `GET /api/facilities`.
5. Explain that FastAPI reads/writes the SQLite database and returns JSON.
6. Create an open game from the confirmed booking, then join it with another player.
