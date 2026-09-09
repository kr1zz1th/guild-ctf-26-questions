import os
import time
import sqlite3
import secrets
from threading import BoundedSemaphore
from flask import Flask, request, session, jsonify, render_template, g

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

DB_PATH = "/tmp/shop.db"
FLAG = os.environ.get("FLAG", "flag{fake_flag_for_testing}")
GIFTCARD_CODE = "WELCOME50"
GIFTCARD_BONUS = 50
FLAG_PRICE = 1000
STARTING_BALANCE = 100

redemption_semaphore = BoundedSemaphore(value=30)

def get_db():
    db = getattr(g, "_db", None)
    if db is None:
        db = g._db = sqlite3.connect(DB_PATH, timeout=15.0, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL;")
    return db

@app.teardown_appcontext
def close_db(exc):
    db = getattr(g, "_db", None)
    if db is not None:
        db.close()

def init_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE,
            balance INTEGER,
            giftcard_used INTEGER DEFAULT 0
        )"""
    )
    conn.commit()
    conn.close()

def get_user():
    token = session.get("token")
    db = get_db()
    if token:
        row = db.execute("SELECT * FROM users WHERE token = ?", (token,)).fetchone()
        if row:
            return row
    token = secrets.token_hex(16)
    db.execute(
        "INSERT INTO users (token, balance, giftcard_used) VALUES (?, ?, 0)",
        (token, STARTING_BALANCE),
    )
    row = db.execute("SELECT * FROM users WHERE token = ?", (token,)).fetchone()
    session["token"] = token
    return row

@app.route("/")
def index():
    user = get_user()
    return render_template("index.html", balance=user["balance"], flag_price=FLAG_PRICE)

@app.route("/api/balance")
def balance():
    user = get_user()
    return jsonify({"balance": user["balance"]})

@app.route("/api/redeem", methods=["POST"])
def redeem():
    if not redemption_semaphore.acquire(blocking=False):
        return jsonify({"error": "Server busy, please try again."}), 429

    try:
        data = request.get_json(silent=True) or {}
        code = data.get("code", "")
        user = get_user()
        db = get_db()

        if code != GIFTCARD_CODE:
            return jsonify({"error": "invalid code"}), 400

        row = db.execute(
            "SELECT giftcard_used FROM users WHERE token = ?",
            (user["token"],),
        ).fetchone()

        if row["giftcard_used"]:
            return jsonify({"error": "gift card already used"}), 400

        time.sleep(0.4)

        db.execute(
            "UPDATE users SET balance = balance + ?, giftcard_used = 1 WHERE token = ?",
            (GIFTCARD_BONUS, user["token"]),
        )

        updated_row = db.execute(
            "SELECT balance FROM users WHERE token = ?",
            (user["token"],),
        ).fetchone()

        return jsonify({"balance": updated_row["balance"], "message": "gift card redeemed successfully!"})
    
    finally:
        redemption_semaphore.release()

@app.route("/api/buy_flag", methods=["POST"])
def buy_flag():
    user = get_user()
    db = get_db()
    
    row = db.execute(
        "SELECT balance FROM users WHERE token = ?", 
        (user["token"],)
    ).fetchone()

    if row["balance"] < FLAG_PRICE:
        return jsonify({"error": f"insufficient balance ({row['balance']}/{FLAG_PRICE})"}), 400
        
    db.execute(
        "UPDATE users SET balance = balance - ? WHERE token = ?",
        (FLAG_PRICE, user["token"]),
    )
    return jsonify({"flag": FLAG})

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, threaded=True, debug=False)
