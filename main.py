from pathlib import Path
import sqlite3
from datetime import date
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "sports_turf.db"
app = FastAPI(title="PlayField Sports Turf API", version="1.0.0",
              description="Sports turf booking and player matchmaking demo API")

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def rows(query, params=()):
    conn = db()
    try:
        return [dict(r) for r in conn.execute(query, params).fetchall()]
    finally:
        conn.close()

def row(query, params=()):
    result = rows(query, params)
    return result[0] if result else None

def init_db():
    # Keep the uploaded database and its schema; ensure a few future demo slots exist.
    conn = db()
    try:
        future = conn.execute("SELECT COUNT(*) FROM slots WHERE slot_date >= ?", (date.today().isoformat(),)).fetchone()[0]
        if future == 0:
            facilities = conn.execute("SELECT facility_id, price FROM facilities").fetchall()
            if not facilities:
                conn.executemany("INSERT INTO facilities(facility_name,address,sport_type,price) VALUES(?,?,?,?)", [
                    ("Play Arena Turf", "Andheri, Mumbai", "Football", 1200),
                    ("Champions Turf", "Bandra, Mumbai", "Football", 1500),
                    ("Smash Court", "Powai, Mumbai", "Badminton", 600)])
                facilities = conn.execute("SELECT facility_id, price FROM facilities").fetchall()
            from datetime import timedelta
            for f in facilities:
                for day_offset in range(1, 8):
                    d = (date.today() + timedelta(days=day_offset)).isoformat()
                    for start, end in [("07:00","08:00"),("18:00","19:00"),("19:00","20:00"),("20:00","21:00")]:
                        exists = conn.execute("SELECT 1 FROM slots WHERE facility_id=? AND slot_date=? AND start_time=?", (f["facility_id"],d,start)).fetchone()
                        if not exists:
                            conn.execute("""INSERT INTO slots(facility_id,slot_date,start_time,end_time,price,availability_status)
                                            VALUES(?,?,?,?,?,'available')""", (f["facility_id"],d,start,end,f["price"]))
        conn.commit()
    finally:
        conn.close()

init_db()

class PlayerCreate(BaseModel):
    player_name: str = Field(min_length=2, max_length=80)
    phone: str = Field(min_length=7, max_length=20)
    email: str
    home_location: str = "Mumbai"
    skill_level: str = "intermediate"

class BookingCreate(BaseModel):
    player_id: int
    slot_id: int

class GameCreate(BaseModel):
    booking_id: int
    host_player_id: int
    sport_type: str
    roster_size: int = Field(ge=2, le=30)
    minimum_skill_level: str = "beginner"

class JoinCreate(BaseModel):
    player_id: int

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "PlayField Sports Turf API"}

@app.get("/api/stats")
def stats():
    return {
        "facilities": row("SELECT COUNT(*) AS n FROM facilities")["n"],
        "available_slots": row("SELECT COUNT(*) AS n FROM slots WHERE availability_status='available' AND slot_date>=?", (date.today().isoformat(),))["n"],
        "players": row("SELECT COUNT(*) AS n FROM players")["n"],
        "open_games": row("SELECT COUNT(*) AS n FROM games WHERE game_status='open'")["n"]
    }

@app.get("/api/facilities")
def facilities(sport: str = "", q: str = ""):
    sql = """SELECT f.facility_id, f.facility_name, f.address, f.sport_type, f.price,
             COUNT(CASE WHEN s.availability_status='available' AND s.slot_date>=? THEN 1 END) AS available_slots
             FROM facilities f LEFT JOIN slots s ON s.facility_id=f.facility_id"""
    params = [date.today().isoformat()]
    where = []
    if sport and sport.lower() != "all":
        where.append("LOWER(f.sport_type)=LOWER(?)"); params.append(sport)
    if q:
        where.append("(LOWER(f.facility_name) LIKE ? OR LOWER(f.address) LIKE ?)")
        params.extend([f"%{q.lower()}%", f"%{q.lower()}%"])
    if where: sql += " WHERE " + " AND ".join(where)
    sql += " GROUP BY f.facility_id ORDER BY f.facility_name"
    return rows(sql, params)

@app.get("/api/slots")
def slots(facility_id: int | str = 0, slot_date: str = ""):
    sql = """SELECT s.slot_id, s.facility_id, f.facility_name, f.address, f.sport_type,
             s.slot_date, s.start_time, s.end_time, s.price, s.availability_status
             FROM slots s JOIN facilities f ON f.facility_id=s.facility_id
             WHERE s.availability_status='available' AND s.slot_date>=?"""
    params = [date.today().isoformat()]
    try:
        fid = int(facility_id) if facility_id else 0
    except (ValueError, TypeError):
        fid = 0
    if fid:
        sql += " AND s.facility_id=?"; params.append(fid)
    if slot_date:
        sql += " AND s.slot_date=?"
        params.append(str(slot_date).strip())
    sql += " ORDER BY s.slot_date, s.start_time LIMIT 100"
    return rows(sql, params)

@app.get("/api/players")
def players():
    return rows("SELECT player_id, player_name, email, home_location, skill_level FROM players ORDER BY player_name")

@app.post("/api/players", status_code=201)
def create_player(data: PlayerCreate):
    if data.skill_level not in {"beginner","intermediate","advanced","competitive"}:
        raise HTTPException(400, "Choose a valid skill level.")
    conn = db()
    try:
        cur = conn.execute("""INSERT INTO players(player_name,phone,email,home_location,skill_level)
                              VALUES(?,?,?,?,?)""",
                           (data.player_name.strip(), data.phone.strip(), data.email.strip().lower(),
                            data.home_location.strip(), data.skill_level))
        conn.commit()
        return row("SELECT player_id, player_name, email, home_location, skill_level FROM players WHERE player_id=?", (cur.lastrowid,))
    except sqlite3.IntegrityError as e:
        raise HTTPException(409, "That phone number or email is already registered.") from e
    finally:
        conn.close()

@app.post("/api/bookings", status_code=201)
def create_booking(data: BookingCreate):
    conn = db()
    try:
        conn.execute("BEGIN IMMEDIATE")
        player = conn.execute("SELECT player_id FROM players WHERE player_id=?", (data.player_id,)).fetchone()
        slot = conn.execute("""SELECT slot_id, facility_id, price, availability_status, slot_date
                               FROM slots WHERE slot_id=?""", (data.slot_id,)).fetchone()
        if not player: raise HTTPException(404, "Player profile not found.")
        if not slot: raise HTTPException(404, "Time slot not found.")
        if slot["slot_date"] < date.today().isoformat(): raise HTTPException(400, "Past slots cannot be booked.")
        if slot["availability_status"] != "available": raise HTTPException(409, "This slot has just been booked. Please choose another.")
        cur = conn.execute("""INSERT INTO bookings(player_id,facility_id,slot_id,payment_amount,booking_status)
                              VALUES(?,?,?,?, 'confirmed')""",
                           (data.player_id, slot["facility_id"], data.slot_id, slot["price"]))
        conn.execute("UPDATE slots SET availability_status='booked' WHERE slot_id=?", (data.slot_id,))
        conn.commit()
        return {"booking_id": cur.lastrowid, "booking_status": "confirmed", "payment_amount": slot["price"],
                "message": "Demo booking confirmed. No real payment was processed."}
    except HTTPException:
        conn.rollback(); raise
    except sqlite3.IntegrityError as e:
        conn.rollback()
        raise HTTPException(409, "This slot is already booked. Refresh and choose another.") from e
    finally:
        conn.close()

@app.get("/api/bookings")
def bookings(player_id: int = 0):
    sql = """SELECT b.booking_id, b.player_id, p.player_name, b.facility_id, f.facility_name,
             s.slot_id, s.slot_date, s.start_time, s.end_time, b.payment_amount, b.booking_status
             FROM bookings b JOIN players p ON p.player_id=b.player_id
             JOIN facilities f ON f.facility_id=b.facility_id JOIN slots s ON s.slot_id=b.slot_id"""
    params = []
    if player_id:
        sql += " WHERE b.player_id=?"; params.append(player_id)
    sql += " ORDER BY s.slot_date DESC, s.start_time"
    return rows(sql, params)

@app.post("/api/games", status_code=201)
def create_game(data: GameCreate):
    conn = db()
    try:
        booking = conn.execute("SELECT booking_id,player_id,facility_id FROM bookings WHERE booking_id=? AND booking_status='confirmed'", (data.booking_id,)).fetchone()
        if not booking: raise HTTPException(400, "A confirmed booking is required to host an open game.")
        if booking["player_id"] != data.host_player_id: raise HTTPException(403, "Only the booking owner can create a game for this booking.")
        existing = conn.execute("SELECT game_id FROM games WHERE booking_id=?", (data.booking_id,)).fetchone()
        if existing: raise HTTPException(409, "An open game already exists for this booking.")
        if data.minimum_skill_level not in {"beginner","intermediate","advanced","competitive"}:
            raise HTTPException(400, "Choose a valid minimum skill level.")
        sport = row("SELECT sport_type FROM facilities WHERE facility_id=?", (booking["facility_id"],))["sport_type"]
        cur = conn.execute("""INSERT INTO games(booking_id,host_player_id,sport_type,roster_size,minimum_skill_level,game_status)
                              VALUES(?,?,?,?,?,'open')""",
                           (data.booking_id, data.host_player_id, data.sport_type or sport, data.roster_size, data.minimum_skill_level))
        conn.execute("INSERT INTO roster(game_id,player_id,skill_level,join_status) SELECT ?,player_id,skill_level,'confirmed' FROM players WHERE player_id=?",
                     (cur.lastrowid, data.host_player_id))
        conn.commit()
        return {"game_id": cur.lastrowid, "message": "Your game is open for players to join."}
    except HTTPException:
        conn.rollback(); raise
    except sqlite3.IntegrityError as e:
        conn.rollback(); raise HTTPException(409, "Could not create game. Check the booking and try again.") from e
    finally:
        conn.close()

@app.get("/api/games")
def games():
    return rows("""SELECT g.game_id,g.booking_id,g.host_player_id,p.player_name AS host_name,
                   g.sport_type,g.roster_size,g.minimum_skill_level,g.game_status,
                   f.facility_name,f.address,s.slot_date,s.start_time,s.end_time,
                   (SELECT COUNT(*) FROM roster r WHERE r.game_id=g.game_id AND r.join_status='confirmed') AS joined_count
                   FROM games g JOIN players p ON p.player_id=g.host_player_id
                   JOIN bookings b ON b.booking_id=g.booking_id JOIN facilities f ON f.facility_id=b.facility_id
                   JOIN slots s ON s.slot_id=b.slot_id
                   WHERE g.game_status='open' ORDER BY s.slot_date,s.start_time""")

@app.post("/api/games/{game_id}/join")
def join_game(game_id: int, data: JoinCreate):
    conn = db()
    try:
        conn.execute("BEGIN IMMEDIATE")
        game = conn.execute("SELECT * FROM games WHERE game_id=? AND game_status='open'", (game_id,)).fetchone()
        player = conn.execute("SELECT player_id,skill_level FROM players WHERE player_id=?", (data.player_id,)).fetchone()
        if not game: raise HTTPException(404, "This game is no longer open.")
        if not player: raise HTTPException(404, "Player profile not found.")
        count = conn.execute("SELECT COUNT(*) FROM roster WHERE game_id=? AND join_status='confirmed'", (game_id,)).fetchone()[0]
        if count >= game["roster_size"]:
            conn.execute("UPDATE games SET game_status='full' WHERE game_id=?", (game_id,))
            conn.commit()
            raise HTTPException(409, "This game is full.")
        conn.execute("INSERT INTO roster(game_id,player_id,skill_level,join_status) VALUES(?,?,?,'confirmed')",
                     (game_id, data.player_id, player["skill_level"]))
        count += 1
        if count >= game["roster_size"]:
            conn.execute("UPDATE games SET game_status='full' WHERE game_id=?", (game_id,))
        conn.commit()
        return {"message": "You joined the game successfully.", "joined_count": count}
    except HTTPException:
        conn.rollback(); raise
    except sqlite3.IntegrityError as e:
        conn.rollback(); raise HTTPException(409, "You may already be in this game's roster.") from e
    finally:
        conn.close()

@app.get("/api/games/{game_id}/roster")
def game_roster(game_id: int):
    if not row("SELECT game_id FROM games WHERE game_id=?", (game_id,)):
        raise HTTPException(404, "Game not found.")
    return rows("""SELECT p.player_id,p.player_name,r.skill_level,r.join_status
                   FROM roster r JOIN players p ON p.player_id=r.player_id
                   WHERE r.game_id=? AND r.join_status='confirmed' ORDER BY r.roster_id""", (game_id,))

app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
@app.get("/")
def home():
    return FileResponse(ROOT / "static" / "index.html")
