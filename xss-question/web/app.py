import base64
import json
import os
import time
import uuid
from functools import wraps

import jwt
import markdown2

import requests
from cryptography.hazmat.primitives import serialization
from flask import Flask, g, redirect, request, url_for
from markupsafe import Markup, escape


BOT_SECRET = os.environ["BOT_SECRET"]
BOT_URL = os.environ["BOT_URL"]

app = Flask(__name__)

with open('keys/private.pem', 'rb') as f:
    private_key = f.read()

with open('keys/public.pem', 'rb') as f:
    public_key = f.read().strip()

with open('keys/public2.pem', 'r') as f:
    public_key2 = f.read().strip()

def b64u(n):
    data = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

users = {}
reports = {}

def make_list(algo, algo_list=[]):
    algo_list.append(algo)
    return algo_list

blocked_algos = make_list("HS256")
allowed_algos = make_list("RS256")

def issue_token(username, role):
    payload = {"username": username, "role": role, "iat": int(time.time())}
    token = jwt.encode(payload, private_key, algorithm="RS256")

    return token

def decode_token(token):
    header = jwt.get_unverified_header(token)

    if header.get("algo") in blocked_algos:
        return "invalid signature"

    try:
        decoded_token = jwt.decode(token, public_key, algorithms=allowed_algos)
    except jwt.exceptions.InvalidKeyError:
        decoded_token = jwt.decode(token, public_key2, algorithms=allowed_algos)
    
    return decoded_token

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

LAYOUT = """
<!doctype html>
    <html>
        <head>
            <title>{title}</title>
            <style>body{{font-family:sans-serif;max-width:640px;margin:40px auto;padding:0 16px}}
textarea{{width:100%;height:160px}} input{{width:100%;padding:6px;margin:4px 0}}
.report{{border:1px solid #ccc;padding:8px;margin:8px 0}}</style>
        </head>
        <body>
            <h2>{title}</h2>
            {body}
        </body>
</html>"""

REGISTER_FORM = """
<form method="post">
    <input name="username" placeholder="username" required>
    <input name="password" type="password" placeholder="password" required>
    <button>Register</button>
</form>
<p><a href="/login">Already have an account?</a></p>"""

LOGIN_FORM = """
<form method="post">
    <input name="username" placeholder="username" required>
    <input name="password" type="password" placeholder="password" required>
    <button>Login</button>
</form>
<p><a href="/register">Need an account?</a></p>
"""

ADMIN_REPORT_FORM = """
<form method="post" action="/admin/report">
    <p>Write a markdown report. An admin reviewer bot will open it shortly.</p>
    <textarea name="content" placeholder="# My report"></textarea>
    <button>Submit report</button>
</form>"""



@app.route("/")
def indec():
    return redirect(url_for("login_page"))

@app.route("/register", methods=["GET", "POST"])
def register_page():
    if request.method == "GET":
        return LAYOUT.format(title="Register", body=REGISTER_FORM)

    username = request.form.get("username", "")
    password = request.form.get("password", "")

    if not username or not password:
        return "username and password required", 400
    
    if username in users.keys():
        return "username taken", 400
    
    #mehh it's 2 in the morning, im gonna store the password as plaintext
    users[username] = password

    return redirect(url_for("login_page"))

@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "GET":
        return LAYOUT.format(title="Login", body=LOGIN_FORM)
    
    username = request.form.get("username", "")
    password = request.form.get("password", "")

    #ooh handling the passwords as plaintext maybe smth could be done here?
    correct_pass = users.get(username)
    
    if (correct_pass is None) or correct_pass != password:
        return "invalid credentials", 401

    token = issue_token(username, "user")
    resp = redirect(url_for("dashboard"))
    resp.set_cookie("token", token, httponly=True, samesite="Lax")
    
    return resp

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

#Bot stuff
def render_report_html(markdown_src):
    return markdown2.markdown(markdown_src, safe_mode="escape")

def notify_bot(report_id):
    try:
        requests.post(
            f"{BOT_URL}/visit",
            json={"report_id": report_id},
            headers={"X-Bot-Secret": BOT_SECRET},
            timeout=2
        )
    except requests.RequestException:
        pass

@app.route("/admin/report", methods=["POST"])
@login_required(role="admin")
def submit_report():
    content = request.form.get("content", "")
    rendered = render_report_html(content)
   
    report_id = uuid.uuid4().hex

    reports[report_id] = [g.user["username"], content, rendered, time.time()]

    notify_bot(report_id)

    body = f"""
    <p>Submitted. The admin reviewer bot has been notified and will open it shortly.</p>
    <p><a href="/report/{report_id}/view">View your report</a></p>
    <p><a href="/admin">Back</a></p>
    """
    return LAYOUT.format(title="Report submitted", body=body)

@app.route("/report/<report_id>/view")
#No auth check??
def view_report(report_id):
    rep = reports.get(report_id)

    if rep is None:
        return "incorrect id", 404
    
    body = Markup(rep[2])
    
    return LAYOUT.format(title="Report", body=body)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

