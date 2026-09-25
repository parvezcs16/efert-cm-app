# Authentication

## Self Registration

1. Employee enters P-Number and company email.
2. Server verifies allowed email domain.
3. Server validates P-Number according to configured employee registration rules.
4. Registration is created as PENDING.
5. Verification/approval process determines activation eligibility.

## First Activation

P-Number + default password
-> OTP
-> OTP verification
-> force password change
-> normal application access

A user whose password state requires change cannot access protected business routes.

## Normal Login

P-Number + password
-> authenticated session/token

If policy requires step-up authentication, OTP can be applied without changing
the first-activation state.

## Password Reset

Forgot/reset password
-> OTP to registered email
-> set new password

## OTP
- 6 digits.
- Cryptographically secure generation.
- Store only a hash/value suitable for verification.
- Short industry-standard expiry.
- Attempt limit.
- Resend cooldown.
- Rate limiting.
- Audit security events.
