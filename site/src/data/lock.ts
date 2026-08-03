// SHA-256 hash of the one shared password for locked articles.
// The plaintext password is never stored here or anywhere in the repo —
// only its hash, which is safe to ship in the public build (this is a soft
// gate, not real security: anyone who fetches /protected/<slug>.json after
// unlocking, or reads this file, is not meaningfully blocked. It's meant to
// keep casual readers out, not to protect sensitive content).
//
// To set or change the password: run `npm run hash-password`, enter the new
// password when prompted, and paste the printed hash below.

export const LOCK_HASH =
  '189855d591605c3d29fa48c124a7b74f8858da4a1c92ecee3a71b5115e9756b6';
