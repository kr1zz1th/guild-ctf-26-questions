import time
import html
import urllib.parse

from flask import Flask, request
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

import os

app = Flask(__name__)

BASE_URL = "http://127.0.0.1:5000"
FLAG = os.getenv("FLAG")

def run_bot(target_url: str) -> str:
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Chrome(options=options)
    try:
        driver.get(f"{BASE_URL}/")
        driver.add_cookie({
            "name": "flag",
            "value": FLAG,
            "domain": "127.0.0.1",
            "path": "/",
            "httpOnly": False,
        })

        driver.get(target_url)
        time.sleep(1)

        return driver.page_source
    except Exception as e:
        return f"Bot error: {e}"
    finally:
        driver.quit()


@app.route('/')
def index():
    return """
    <!DOCTYPE html>
    <html>
    <body style="font-family: sans-serif; padding: 2rem;">
        <h2>Admin Bot Sandbox</h2>
        <p>Only the admin bot can see the flag. Submit a payload for the bot to run.</p>
        <form action="/submit" method="POST">
            <input type="text" name="payload" style="width: 400px; padding: 5px;">
            <button type="submit" style="padding: 5px;">Execute in Bot</button>
        </form>
    </body>
    </html>
    """


@app.route('/reflect')
def reflect():
    payload = request.args.get('payload', '')
    # is this an interesting thing? idk you tell me
    return f"<html><body><div>{payload}</div></body></html>"


@app.route('/submit', methods=['POST'])
def submit():
    payload = request.form.get('payload', '')
    target_url = f"{BASE_URL}/reflect?payload={urllib.parse.quote(payload)}"

    bot_html = run_bot(target_url)

    return f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: sans-serif; padding: 2rem;">
        <h1>Admin bot output</h1>
        <textarea style="width: 100%; height: 300px;" readonly>{html.escape(bot_html)}</textarea>
        <br><br>
        <a href="/">Go back</a>
    </body>
    </html>
    """


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
