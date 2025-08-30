import sqlite3
import os

DB_FILE = os.path.join(os.path.dirname(__file__), "vehicles.db")

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS vehicles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        fuel_km_left INTEGER DEFAULT 100,
        oil_km_left INTEGER DEFAULT 1000
    )
    """)
    
    try:
        cur.execute("ALTER TABLE vehicles ADD COLUMN tyre INTEGER DEFAULT 100;")
    except sqlite3.OperationalError:
        # Column already exists
        pass
    conn.commit()
    conn.close()


def add_vehicle(user_id, name, fuel_km=0, oil_km=0):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("INSERT INTO vehicles (user_id, name, fuel_km_left, oil_km_left) VALUES (?, ?, ?, ?)",
                (user_id, name, fuel_km, oil_km))
    conn.commit()
    conn.close()

def list_vehicles(user_id):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT id, name, fuel_km_left, oil_km_left,tyre FROM vehicles WHERE user_id=?", (user_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

def update_vehicle_by_name(user_id, name, field, km):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    if field == "fuel":
        cur.execute("UPDATE vehicles SET fuel_km_left=? WHERE user_id=? AND name=?", (km, user_id, name))
    else:
        cur.execute("UPDATE vehicles SET oil_km_left=? WHERE user_id=? AND name=?", (km, user_id, name))
    conn.commit()
    conn.close()

def reset_user(user_id):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("DELETE FROM vehicles WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def remove_vehicle_by_name(user_id, name):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("DELETE FROM vehicles WHERE user_id=? AND name=?", (user_id, name))
    conn.commit()
    conn.close()


