# Progress So Far

## HACK-1 — Break the Sandbox ✅ MAJOR PROGRESS

**What works:**
- ✅ Checkin for `arena-hack1` → gets `qr_sess` JWT cookie
- ✅ Can read order #9001 (Hashir's, table UUID `a0000001-...`)
- ✅ Can ADD items to existing order via `POST /api/qr/order/{id}/items`
- ✅ Order shows our additions (customer name chain: "Hashir + Attacker + CTF Proof + Codex CTF Proof + TRST + test + xtra")

**Customer name now includes:** `xtra`

**What we've tested that doesn't work yet:**
- ❌ PATCH/PUT on order or item status → 404
- ❌ Cancelling items via POST to items endpoint with `action: "cancel"` → "No valid items found"
- ❌ Accessing other tables' orders via UUID swapping → `[]` (scoped by JWT)

**Remaining attack angles for HACK-1:**
1. **Staff portal creds** — `/kitchen`, `/waiter`, `/pos` have Basic auth "SROS staff" — try default credentials
2. **Cancel/settle via staff endpoints** — if we get staff access, we can flip order status
3. **Modifying order item status** — check if status updates are possible through another method

## HACK-2 — Bypass the Geofence 🚧 IN PROGRESS

**Flow understood:**
1. `POST /api/qr/checkin?outlet=DEMOB` with `{name: "arena-hack2"}`
2. Returns `{geofenceMode: "hard", needLocation: true}`
3. Send GPS → returns `{error: "Please come to the cafe to order.", geofence: "blocked"}`
4. No `qr_sess` cookie set when geofence blocks

**What we've tried that fails:**
- ❌ Bavdhan, Pune GPS coords → out_of_range
- ❌ lat:0, lng:0 → accuracy_too_low
- ❌ Geofence bypass params in body → ignored
- ❌ Admin/override params → ignored
- ❌ Direct order (no cookie) → "duplicate" then "re-scan"
- ❌ HACK-1 cookie on HACK-2 → "re-scan" (token scoped to table)

**Key insight from "duplicate" response:**
Without any auth cookie, the order endpoint returned `{"duplicate": true}` — meaning it **accepted the request at the processing level** (not rejected by auth middleware). Someone IS placing orders on HACK-2. The geofence is only at CHECKIN, not at ORDER time — but you still need a valid cookie.

**"Break the handshake" theory:**
The handshake = checkin flow (GPS validation → JWT issuance). Need to either:
1. Find HACK-2's table UUID and forge a JWT
2. Find the HMAC secret key
3. Find another endpoint that sets a valid cookie without geofence
4. Find a way to replay/modify the checkin response