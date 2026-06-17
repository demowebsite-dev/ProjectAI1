# XENIOS HackMe Recon

## Stack
- Next.js SPA (client-side rendered)
- Express backend (X-Powered-By: Express)
- nginx 1.24.0 reverse proxy
- PostgreSQL (from /api/health)
- WebSocket at wss://hackme.xenios.in/ws

## Build ID: BRB1jRSEl2734dd3Ww9KP

## Auth System
**sros_token** stored in localStorage → sent as `Authorization: Bearer <token>` header

### QR Entry Flow
1. Page loads with `?table=X&outlet=Y` from URL params
2. JS calls `POST /api/qr/checkin` with `{name: "arena-hack1"}`
3. If `needLocation: true` in response → gets GPS → re-calls with `{located: true, lat, lng, accuracy}`
4. Checkin returns table/outlet data + creates session → sets `sros_token` in localStorage
5. For HACK-2 (Vault): geofence check at checkin returns `403` with `{geofence: "blocked"}`

## API Surface (Public)
| Endpoint | Method | Auth | Notes |
|---|---|---|---|
| /api/health | GET | No | Server info, version 1.0.0 |
| /api/menu | GET | No | 4 menu items with UUIDs |
| /api/white-label/config | GET | No | Brand config (null) |

## API Surface (Customer - needs sros_token)
| Endpoint | Method | Notes |
|---|---|---|
| /api/qr/checkin | POST | Creates session, returns token |
| /api/qr/order?tableId=X | GET | Get orders for table |
| /api/qr/order | POST | Place order: tableId, items[], customerName, customerPhone |
| /api/qr/order/{id}/items | POST | Add items to existing order |
| /api/qr/assist | POST | Call waiter/bill/etc |
| /api/qr/mood | POST | Set mood |
| /api/qr/social?tableId=X | GET | Social feed |
| /api/qr/customer-history?phone=X | GET | Customer history |
| /api/qr/quiz | GET | Get quiz |
| /api/qr/quiz/answer | POST | Answer quiz |
| /api/feedback | POST | Feedback |
| /api/settings/tax | GET | Tax rate |
| /api/pricing/evaluate | GET | Pricing adjustments |
| /api/entitlements | GET | Feature flags |
| /api/loyalty/me?phone=X | GET | Loyalty info |
| /api/loyalty/record | POST | Record points |
| /api/loyalty/spin | POST | Spin wheel |
| /api/upi/generate/{orderId} | GET | UPI QR |
| /api/upi/claim/{orderId} | POST | Claim payment |

## Staff Portals (401 Basic Auth "SROS staff")
- /kitchen
- /waiter
- /pos
- /api/orders, /api/tables, /api/floor, /api/staff, /api/config

## Menu Items (from /api/menu)
| Item ID | Name | Price | Category |
|---|---|---|---|
| b7f23b0c-b894-4cfe-8805-d90be44043d3 | Deja Vu Special Pizza | ₹420 | continental |
| e9a85915-00c8-4860-a7b6-ecaf78c4b2a0 | Deja Vu Lasagna | ₹380 | continental |
| 6b29e004-3d1b-43ed-8410-6920a5664a97 | Deja Vu Signature Hot Chocolate | ₹180 | bev |
| (4th item - total 4) | | | |

## Orders Known
- A-T2: Order #1002, Vaibhav Srivastava, ₹630, preparing
- HACK-1: Order #9001, Hashir, ₹1,029, preparing

## Outlet IDs
- DEMOA: arena-hack1, arena-a-t1, arena-a-t2, etc.
- DEMOB: arena-hack2 (Vault, geofenced)