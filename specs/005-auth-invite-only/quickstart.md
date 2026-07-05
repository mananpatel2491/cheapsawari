# Quickstart: Invite-Only Access

## 1. Dev-mode gate walkthrough (what Bruno does)

Start the API on port 8050 (spec 001 quickstart); `AUTH_MODE` defaults to `dev`.

```bash
# no session → 401
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8050/api/v1/watches       # 401

# admin dev-login (ADMIN_EMAIL default mpatel.mi24@gmail.com; always allowed)
curl -s -c admin.txt -X POST http://127.0.0.1:8050/api/v1/auth/dev \
  -H "content-type: application/json" -d '{"email":"mpatel.mi24@gmail.com"}'
curl -s -b admin.txt http://127.0.0.1:8050/api/v1/auth/me    # {"email":…,"is_admin":true}

# stranger → 403 (not on the allowlist)
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://127.0.0.1:8050/api/v1/auth/dev \
  -H "content-type: application/json" -d '{"email":"stranger@example.com"}'          # 403

# invite, then the invitee can log in
curl -s -b admin.txt -X POST http://127.0.0.1:8050/api/v1/admin/users \
  -H "content-type: application/json" -d '{"email":"invitee@example.com"}'
curl -s -c inv.txt -X POST http://127.0.0.1:8050/api/v1/auth/dev \
  -H "content-type: application/json" -d '{"email":"invitee@example.com"}'

# ownership: invitee sees only their own watches; another user's id → 404
curl -s -b inv.txt http://127.0.0.1:8050/api/v1/watches

# revoke → next request is 401 immediately
curl -s -b admin.txt -X DELETE http://127.0.0.1:8050/api/v1/admin/users/invitee@example.com
curl -s -o /dev/null -w "%{http_code}\n" -b inv.txt http://127.0.0.1:8050/api/v1/watches  # 401
```

UI path: `http://127.0.0.1:8050/login` shows the "DEV MODE" pill + email form;
`/admin` (as admin) manages the allowlist.

## 2. Bruno gates

```bash
cd bruno/cheapsawari
bru run auth ownership --env local
```

## 3. Prod (google) posture

Cloud Run env: `AUTH_MODE=google`, `GOOGLE_CLIENT_ID=<OAuth Web client>`,
`SESSION_SECRET=<stable random>`, `ADMIN_EMAIL=…` (`docs/DEPLOYMENT.md:27-39`).
Checklist when sign-in "doesn't render" on a new domain: add the domain to the OAuth
client's Authorized JavaScript origins — the failure is upstream at Google and leaves
no `auth.login` event in app logs (`docs/DEPLOYMENT.md:50-60`). Verify hardening:
`view-source:/login` has no dev form; `POST /api/v1/auth/dev` → 404.
