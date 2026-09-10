import base64
import json
import os
import time
import uuid
from functools import wraps

import requests
from cryptography.hazmat.primitives import serialization

with open('keys/public.pem', 'rb') as f:
    public_key = f.read()

def b64u(n):
    data = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def jwk_json(pem_bytes):
    nums = serialization.load_pem_public_key(pem_bytes).public_numbers()
    return json.dumps(
        {
            "kty": "RSA",
            "kid": "server",
            "use": "sig",
            "alg": "RS256",
            "n": b64u(nums.n),
            "e": b64u(nums.e),
        }
    )

pwk_pub_key = jwk_json(public_key)
print(pwk_pub_key)



def make_list(algo, algo_list=[]):
    algo_list.append(algo)
    return algo_list

disallowed_algos = make_list("HS256")
allowed_algos = make_list("RS256")

print(allowed_algos)
