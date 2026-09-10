import hmac
import os
import threading
import time
import traceback

from flask import Flask, jsonify, request
from playwright.sync_api import sync_playwright

BASE_URL = os.environ["WEB_URL"]
BOT_SECRET = os.environ["BOT_SECRET"]
FLAG = os.environ["FLAG"]
BOT_PORT = int(os.environ["BOT_PORT"])

app = Flask(__name__)

def visit(report_id):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
        )

        context = browser.new_context(base_url=BASE_URL)
        page = context.new_page()

        try:
            page.goto("/login")
            context.add_cookies([
                {
                    "name": "flag",
                    "value": FLAG,
                    "url": BASE_URL
                }
            ])

            page.goto(f"/report/{report_id}/view")
            time.sleep(5)

        finally:
            context.close()
            browser.close()


@app.route("/visit", methods=["POST"])
def handle_visit():
    if not hmac.compare_digest(request.headers.get("X-Bot-Secret", ""), BOT_SECRET):
        return "only the bot can visit here", 403

    report_id = (request.get_json(silent=True) or {}).get("report_id")
    
    if not report_id:
        return "bad request", 400
    
    threading.Thread(target=visit, args=(report_id,), daemon=True).start()
    
    return "request received"
    
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=BOT_PORT)
        
    
