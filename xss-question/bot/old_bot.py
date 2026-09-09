import hmac
import os
import threading
import time

from flask import Flask, jsonify, request
from playwright.sync_api import sync_playwright

BASE_URL = os.environ.get("WEB_URL", "http://web:5000")
BOT_SECRET = os.environ["BOT_SECRET"]
FLAG = os.environ.get("FLAG", "flag{set_FLAG_env_var}")
BOT_PORT = int(os.environ.get("BOT_PORT", "6000"))

RENDER_WAIT_SECONDS = 3

app = Flask(__name__)


def visit(report_id):
    """Load the report as if an admin were viewing it, flag cookie in hand."""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
        )
        # base_url lets every page.goto() call use a relative path
        context = browser.new_context(base_url=BASE_URL)
        try:
            page = context.new_page()
            page.goto("/login")
            context.add_cookies([
                {"name": "flag", "value": FLAG, "url": BASE_URL, "path": "/"}
            ])
            page.goto(f"/report/{report_id}/view")
            time.sleep(RENDER_WAIT_SECONDS)
        finally:
            context.close()
            browser.close()


def review(report_id):
    try:
        visit(report_id)
    except Exception as e:
        print(f"[bot] error visiting report {report_id}: {e}")


@app.route("/visit", methods=["POST"])
def handle_visit():
    if not hmac.compare_digest(request.headers.get("X-Bot-Secret", ""), BOT_SECRET):
        return "forbidden", 403
    report_id = (request.get_json(silent=True) or {}).get("report_id")
    if not report_id:
        return "bad request", 400
    threading.Thread(target=review, args=(report_id,), daemon=True).start()
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=BOT_PORT)
