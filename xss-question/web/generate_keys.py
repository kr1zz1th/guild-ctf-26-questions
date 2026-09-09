import os
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

KEY_DIR = os.path.join(os.path.dirname(__file__), "keys")
PRIV_PATH = os.path.join(KEY_DIR, "private.pem")
PUB_PATH = os.path.join(KEY_DIR, "public.pem")

if not (os.path.exists(PRIV_PATH) and os.path.exists(PUB_PATH)):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv_bytes = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_bytes = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    os.makedirs(KEY_DIR, exist_ok=True)
    with open(PRIV_PATH, "wb") as f:
        f.write(priv_bytes)
    with open(PUB_PATH, "wb") as f:
        f.write(pub_bytes)
    print("Generated new RSA keypair for JWT signing.")
