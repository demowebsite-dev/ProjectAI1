#!/usr/bin/env python3
"""Fallback C - Deep JS source inspection for hardcoded keys"""
import re, os, glob, json

js_dir = "/workspaces/cafe/js_dumps"
files = sorted(glob.glob(f"{js_dir}/*.js"))

# 1. Find potential secrets in string literals
print("=== Looking for potential secret/keys in string literals ===")
for f in files:
    with open(f, 'r', errors='ignore') as fh:
        content = fh.read()
    # Find quoted strings that look like secrets (alphanumeric, 8-60 chars)
    matches = re.findall(r'"([a-zA-Z0-9_\-=+/]{8,60})"', content)
    for m in matches:
        # Skip URLs, UUIDs with dashes, dates
        if m.startswith('http') or m.startswith('/'):
            continue
        if re.match(r'^[a-f0-9\-]{30,}$', m):
            continue  # UUID
        print(f"  {os.path.basename(f)}: {m}")

print()

# 2. Look for QR page token logic - search for checkin/qr_sess/createToken
print("=== Searching for token generation / QR logic ===")
for f in files:
    with open(f, 'r', errors='ignore') as fh:
        content = fh.read()
    # Look for QR-related function names
    if 'checkin' in content.lower() or 'qr_sess' in content:
        print(f"  Found checkin/qr_sess in: {os.path.basename(f)}")
    # Look for token creation
    if 'createToken' in content or 'signToken' in content or 'generateToken' in content:
        print(f"  Found token creation in: {os.path.basename(f)}")
    # Look for HMAC creation
    if 'createHmac' in content or 'Hmac' in content:
        idx = content.find('createHmac') if 'createHmac' in content else content.find('Hmac')
        print(f"  Found HMAC ref in: {os.path.basename(f)} at {idx}")

print()

# 3. Extract the QR page HTML to find the actual JS chunks it loads
print("=== Checking watch page for additional JS chunks ===")
qr_page = "/workspaces/cafe/js_dumps/qr-page-detailed.js"
if os.path.exists(qr_page):
    with open(qr_page, 'r', errors='ignore') as f:
        content = f.read()
    chunks = re.findall(r'src="([^"]+\.js)"', content)
    for c in chunks:
        print(f"  JS chunk: {c}")

print()

# 4. Search for any hardcoded word that looks like a key in the main fd9d chunk
print("=== Looking for 'secret', 'key', 'hmac', 'jwt' in JS ===")
patterns = ['secret', ' jwts', 'jwt_', 'hmac', 'signing', 'privateKey']
for f in files:
    with open(f, 'r', errors='ignore') as fh:
        content = fh.read().lower()
    for p in patterns:
        if p in content:
            print(f"  '{p}' in {os.path.basename(f)}")