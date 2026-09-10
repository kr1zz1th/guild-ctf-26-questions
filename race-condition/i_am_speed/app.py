import os
import time
import secrets
import threading
from flask import Flask, request, session, jsonify, render_template

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

FLAG = os.environ.get("FLAG", "exploiitm{fake_flag_for_testing}")
GIFTCARD_CODE = "WELCOME50"
GIFTCARD_BONUS = 50
FLAG_PRICE = 1000
STARTING_BALANCE = 100

redemption_semaphore = threading.BoundedSemaphore(value=30)

users = {}
users_lock = threading.Lock()

def get_user():
    token = session.get("token")
    if token:
        with users_lock:
            user = users.get(token)
        if user is not None:
            return token, user

    token = secrets.token_hex(16)
    with users_lock:
        users[token] = {"balance": STARTING_BALANCE, "giftcard_used": False}
    session["token"] = token
    return token, users[token]

@app.route("/")
def index():
    _, user = get_user()
    return render_template("index.html", balance=user["balance"], flag_price=FLAG_PRICE)

@app.route("/api/balance")
def balance():
    _, user = get_user()
    return jsonify({"balance": user["balance"]})

@app.route("/api/redeem", methods=["POST"])
def redeem():
    if not redemption_semaphore.acquire(blocking=False):
        return jsonify({"error": "Server busy, please try again."}), 429

    try:
        data = request.get_json(silent=True) or {}
        code = data.get("code", "")
        token, user = get_user()

        if code != GIFTCARD_CODE:
            return jsonify({"error": "invalid code"}), 400

        if user["giftcard_used"]:
            return jsonify({"error": "gift card already used"}), 400

        time.sleep(0.4)

        user["balance"] += GIFTCARD_BONUS
        user["giftcard_used"] = True

        return jsonify({"balance": user["balance"], "message": "gift card redeemed successfully!"})

    finally:
        redemption_semaphore.release()

@app.route("/api/buy_ramen", methods=["POST"])
def buy_ramen():
    _, user = get_user()

    if user["balance"] < FLAG_PRICE:
        return jsonify({"error": f"insufficient balance ({user['balance']}/{FLAG_PRICE})"}), 400

    user["balance"] -= FLAG_PRICE
    return jsonify({"flag": FLAG})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, threaded=True, debug=False)
