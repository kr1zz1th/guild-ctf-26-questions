import base64
import json
import os
import sqlite3
import time
import uuid
from functools import wraps

import jwt
import markdown2

import requests
from cryptography.hazmat.primitives import serialization
from flask import Flask, g, redirect, request, url_for
from markupsafe import Markup, escape
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, "app.db")

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", os.urandom(16).hex())
BOT_SECRET = os.environ.get("BOT_SECRET", os.urandom(16).hex())
BOT_URL = os.environ.get("BOT_URL", "http://bot:6000")
REPORT_TTL_SECONDS = 600

app = Flask(__name__)


#my keys
with open(os.path.join(BASE_DIR, "keys", "private.pem"), "rb") as f:
    PRIVATE_KEY = f.read()
with open(os.path.join(BASE_DIR, "keys", "public.pem"), "rb") as f:
    PUBLIC_KEY = f.read()


def _b64url_uint(n):
    data = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _pubkey_jwk_json(pem_bytes):
    numbers = serialization.load_pem_public_key(pem_bytes).public_numbers()
    return json.dumps(
        {
            "kty": "RSA",
            "kid": "server",
            "use": "sig",
            "alg": "RS256",
            "n": _b64url_uint(numbers.n),
            "e": _b64url_uint(numbers.e),
        }
    )


PUBLIC_KEY_JWK_JSON = _pubkey_jwk_json(PUBLIC_KEY)


# --- Database ---------------------------------------------------------------

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def cleanup_old_reports(db):
    db.execute("DELETE FROM reports WHERE created_at < ?", (time.time() - REPORT_TTL_SECONDS,))
    db.commit()


def init_db():
    first_run = not os.path.exists(DB_PATH)
    db = sqlite3.connect(DB_PATH)
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
        );
        CREATE TABLE IF NOT EXISTS reports (
            id TEXT PRIMARY KEY,
            author TEXT NOT NULL,
            content TEXT NOT NULL,
            rendered TEXT NOT NULL,
            created_at REAL NOT NULL
        );
        """
    )
    if first_run:
        db.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (ADMIN_USERNAME, generate_password_hash(ADMIN_PASSWORD), "admin"),
        )
        db.commit()
    db.close()


def issue_token(username, role):
    payload = {"username": username, "role": role, "iat": int(time.time())}
    token = jwt.encode(payload, PRIVATE_KEY, algorithm="RS256")
    return token.decode() if isinstance(token, bytes) else token


def decode_token(token):
    #oooh what is this HS256 and JWK jSON keys
    header = jwt.get_unverified_header(token)
    key = PUBLIC_KEY if header.get("alg") == "RS256" else PUBLIC_KEY_JWK_JSON
    return jwt.decode(token, key, algorithms=["HS256", "RS256"], options={"verify_exp": False})


def current_user():
    token = request.cookies.get("token")
    if not token:
        return None
    try:
        return decode_token(token)
    except jwt.InvalidTokenError:
        return None


def login_required(role=None):
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            user = current_user()
            if user is None:
                return redirect(url_for("login_page"))
            if role and user.get("role") != role:
                return "Forbidden", 403
            g.user = user
            return fn(*a, **kw)

        return wrapper

    return deco


def render_report_html(markdown_src):
    #is safe_mode actually safe tho??
    return markdown2.markdown(markdown_src, safe_mode="escape")


def notify_bot(report_id):
    try:
        requests.post(
            f"{BOT_URL}/visit",
            json={"report_id": report_id},
            headers={"X-Bot-Secret": BOT_SECRET},
            timeout=2,
        )
    except requests.RequestException:
        pass


LAYOUT = """<!doctype html><html><head><title>{title}</title>
<style>body{{font-family:sans-serif;max-width:640px;margin:40px auto;padding:0 16px}}
textarea{{width:100%;height:160px}} input{{width:100%;padding:6px;margin:4px 0}}
.report{{border:1px solid #ccc;padding:8px;margin:8px 0}}</style></head>
<body><h2>{title}</h2>{body}</body></html>"""

REGISTER_FORM = """
<form method="post">
<input name="username" placeholder="username" required>
<input name="password" type="password" placeholder="password" required>
<button>Register</button></form>
<p><a href="/login">Already have an account?</a></p>"""

LOGIN_FORM = """
<form method="post">
<input name="username" placeholder="username" required>
<input name="password" type="password" placeholder="password" required>
<button>Login</button></form>
<p><a href="/register">Need an account?</a></p>
<p><a href="/pubkey.jwk">API/webhook verification public key</a></p>"""

ADMIN_REPORT_FORM = """
<form method="post" action="/admin/report">
<p>Write a markdown report. An admin reviewer bot will open it shortly.</p>
<textarea name="content" placeholder="# My report"></textarea>
<button>Submit report</button></form>"""


@app.route("/")
def index():
    return redirect(url_for("login_page"))


@app.route("/register", methods=["GET", "POST"])
def register_page():
    if request.method == "GET":
        return LAYOUT.format(title="Register", body=REGISTER_FORM)

    username = request.form.get("username", "")
    password = request.form.get("password", "")
    if not username or not password:
        return "username and password required", 400
    db = get_db()
    try:
        db.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'user')",
            (username, generate_password_hash(password)),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return "username taken", 400
    return redirect(url_for("login_page"))


@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "GET":
        return LAYOUT.format(title="Login", body=LOGIN_FORM)

    username = request.form.get("username", "")
    password = request.form.get("password", "")
    db = get_db()
    row = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if row is None or not check_password_hash(row["password_hash"], password):
        return "invalid credentials", 401

    token = issue_token(row["username"], row["role"])
    resp = redirect(url_for("dashboard"))
    resp.set_cookie("token", token, httponly=True, samesite="Lax")
    return resp


@app.route("/pubkey.jwk")
def pubkey():
    return PUBLIC_KEY_JWK_JSON, 200, {"Content-Type": "application/json"}


@app.route("/dashboard")
@login_required()
def dashboard():
    body = f"<p>Welcome, {escape(g.user['username'])} (role: {escape(g.user['role'])}).</p>"
    if g.user["role"] == "admin":
        body += '<p><a href="/admin">Go to admin panel</a></p>'
    return LAYOUT.format(title="Dashboard", body=body)


@app.route("/admin", methods=["GET"])
@login_required(role="admin")
def admin_panel():
    return LAYOUT.format(title="Admin panel", body=ADMIN_REPORT_FORM)


@app.route("/admin/report", methods=["POST"])
@login_required(role="admin")
def submit_report():
    content = request.form.get("content", "")
    rendered = render_report_html(content)

    db = get_db()
    cleanup_old_reports(db)
    report_id = uuid.uuid4().hex
    db.execute(
        "INSERT INTO reports (id, author, content, rendered, created_at) VALUES (?, ?, ?, ?, ?)",
        (report_id, g.user["username"], content, rendered, time.time()),
    )
    db.commit()

    notify_bot(report_id)

    body = """
    <p>Submitted. The admin reviewer bot has been notified and will open it shortly.</p>
    <p><a href="/admin">Back</a></p>"""
    return LAYOUT.format(title="Report submitted", body=body)


@app.route("/report/<report_id>/view")
def view_report(report_id):
    db = get_db()
    row = db.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
    if row is None:
        return "not found", 404
    body = Markup(row["rendered"])
    return LAYOUT.format(title="Report", body=body)


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
