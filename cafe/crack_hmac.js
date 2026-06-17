const crypto = require('crypto');
const fs = require('fs');

const token = fs.readFileSync('/tmp/fresh_token.txt', 'utf-8').trim();
console.log('Token:', token.slice(0, 30) + '...' + token.slice(-10));

const [payloadB64, sigB64] = token.split('.');
console.log('Payload B64:', payloadB64.slice(0, 30) + '...');

// Decode payload to verify
const payload = JSON.parse(Buffer.from(payloadB64, 'base64url').toString());
console.log('Payload:', JSON.stringify(payload));

// Build expansive wordlist
const words = [
  // System names
  'sros', 'SROS', 'sros_staff', 'SROS staff',
  'xenios', 'XENIOS', 'Xenios',
  'dejavu', 'DejaVu', 'deja_vu', 'cafedejavu', 'CafeDejaVu',
  'cafe', 'Cafe',
  'hackme', 'hackme.xenios.in', 'hackathon',
  'arena', 'ARENA',
  
  // Outlet IDs
  'DEMOA', 'DEMOB', 'demoa', 'demob',
  '11111111-1111-1111-1111-111111111111',
  '22222222-2222-2222-2222-222222222222',
  
  // Build ID
  'BRB1jRSEl2734dd3Ww9KP',
  
  // Common defaults
  'admin', 'password', 'secret', 'qwerty', 'letmein', 'changeme',
  '123456', '12345678', '1234', '0000', '1111',
  'key', 'token', 'signature', 'hmac',
  'test', 'demo', 'guest',
  
  // Contextual
  'gizmoiot', 'GIZMOIOT',
  'hashir', 'vaibhav', 
  'Bavdhan', 'Pune',
  'BreakTheQR', 'breaktheqr',
  'xtra',
  'pizzA', 'lasagna', 'tiramisu',
  'continental', 'bev', 'dessert',
  'n7k3',
  
  // Alphanumeric combos
  'sros2024', 'sros2025', 'sros2026',
  'xenios2024', 'xenios2025', 'xenios2026',
  'hackme2024', 'hackme2025', 'hackme2026',
  'ctf', 'CTF',
  
  // UUID patterns
  'a0000001-0000-0000-0000-000000000001',
  'a0000001-0000-0000-0000-000000000003',
];

console.log(`\nTrying ${words.length} keys...\n`);

for (const key of words) {
  const hmac = crypto.createHmac('sha256', key);
  hmac.update(payloadB64);
  const computed = hmac.digest('base64url');
  if (computed === sigB64) {
    console.log('✅ FOUND KEY:', key);
    process.exit(0);
  }
}

// Also try all 5-digit and 6-digit numeric PINs
console.log('Trying 5-digit PINs (00000-09999)...');
for (let i = 0; i < 10000; i++) {
  const key = String(i).padStart(5, '0');
  const hmac = crypto.createHmac('sha256', key);
  hmac.update(payloadB64);
  if (hmac.digest('base64url') === sigB64) {
    console.log('✅ FOUND KEY (5-digit):', key);
    process.exit(0);
  }
}

console.log('Trying 6-digit PINs (000000-009999)...');
for (let i = 0; i < 10000; i++) {
  const key = String(i).padStart(6, '0');
  const hmac = crypto.createHmac('sha256', key);
  hmac.update(payloadB64);
  if (hmac.digest('base64url') === sigB64) {
    console.log('✅ FOUND KEY (6-digit):', key);
    process.exit(0);
  }
}

console.log('\n❌ Key not found in list.');
console.log('Signature:', sigB64);