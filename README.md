# Mommy's Time — Community API

A small, fast **FastAPI** backend for the Mommy's Time community ("Village")
feature. Users authenticate with **Sign in with Apple**; every thread, reply and
hug is tied to the Apple account that made it, so we always know who
created/shared a message.

- **Framework:** FastAPI + SQLModel (SQLAlchemy)
- **Auth:** Apple identity-token verification → our own bearer session token
- **DB:** SQLite by default (one file), swap `DATABASE_URL` for Postgres in prod

## Quick start

```bash
cd mommys-time-community-api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # then edit JWT_SECRET (and APPLE_BUNDLE_ID if needed)

uvicorn app.main:app --reload
```

Open the interactive docs at **http://127.0.0.1:8000/docs**.

Optional: seed a couple of sample discussions — `python seed.py`.

## Auth flow (how it links to Apple Sign In)

1. In the iOS app, the user taps **Sign in with Apple**. The credential gives you
   an **`identityToken`** (a JWT), the stable **`user`** id, and — only on the
   first sign-in — the **name** and **email**.
2. The app POSTs the token to this API:

   ```
   POST /auth/apple
   { "identity_token": "<the JWT>", "full_name": "Nur Alia", "email": "..." }
   ```

3. The API **verifies the token** against Apple's public keys (checks signature,
   `aud` == your bundle id, `iss` == `https://appleid.apple.com`, expiry),
   extracts the Apple user id (`sub`), and **creates or looks up** the user.
4. It returns **our** session token:

   ```
   { "access_token": "<jwt>", "token_type": "bearer", "user": {...} }
   ```

5. The app stores `access_token` and sends it on every request:
   `Authorization: Bearer <access_token>`. That's how each post/reply/hug is
   attributed to the right Apple user.

> **Dev shortcut:** set `ALLOW_DEV_LOGIN=true` and POST
> `{ "dev_apple_sub": "any-id", "full_name": "Test" }` to get a token without a
> real Apple token — handy for testing before wiring up the app. Never enable in
> production.

## Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/` | — | Health check |
| `POST` | `/auth/apple` | — | Sign in with Apple → session token |
| `GET` | `/auth/me` | ✅ | Current user |
| `GET` | `/threads` | optional | List discussions (optional `?topic=` filter) |
| `POST` | `/threads` | ✅ | Create a discussion |
| `GET` | `/threads/{id}` | optional | Thread with its replies |
| `POST` | `/threads/{id}/replies` | ✅ | Reply to a thread |
| `POST` | `/threads/{id}/hug` | ✅ | Toggle your hug on a thread |
| `DELETE` | `/threads/{id}` | ✅ | Delete your own thread |
| `DELETE` | `/threads/replies/{id}` | ✅ | Delete your own reply |

Auth "optional" endpoints work without a token, but if you send one they also
tell you whether **you** hugged a thread (`hugged`) and which posts are yours
(`is_mine`).

Topics are free text — whatever the poster types, trimmed and capped at 40
characters (`MAX_TOPIC_LENGTH`). There's no fixed list on either side: the app
builds its filter chips and its "existing topics" suggestions from the topics
already in use.

## Data model

- **User** — `apple_sub` (Apple's id), `display_name`, `email`
- **Thread** — `author_id`, `topic`, `title`, `body`, `created_at`
- **Reply** — `thread_id`, `author_id`, `body`, `created_at`
- **Hug** — (`user_id`, `thread_id`) — one hug per user per thread; the thread's
  hug count is just how many rows point at it

## Testing

```bash
pip install httpx           # TestClient dependency
python smoke_test.py        # runs the full flow with the dev login
```

## Deployment

Live at **http://mommys-time-api.codedancoffee.com** (nginx → uvicorn). The iOS
app points here by default; see `CommunityConfig.swift` in mommys-time-ios.

Verified on the deployed host: `/` health check, `/docs`, all eight routes in
`/openapi.json`, `ALLOW_DEV_LOGIN` off (a `dev_apple_sub` login is rejected),
and 401s on the authed routes for a missing or bad token.

**Still to do: TLS.** Port 443 answers, but with the certificate for another
site on the box (`zakatcalculator.sol.site`), so HTTPS fails the handshake for
this hostname and the app has to talk plain HTTP behind an App Transport
Security exception. DNS already resolves, so issuing a certificate is enough:

```bash
sudo certbot --nginx -d mommys-time-api.codedancoffee.com
```

Then switch `CommunityConfig.deployed` to `https://` and delete the
`NSExceptionDomains` block from the app's `Info.plist`.

## Production notes

- Set a strong **`JWT_SECRET`** and a real **`DATABASE_URL`** (Postgres).
  Rotating the secret invalidates every existing session token.
- Keep **`ALLOW_DEV_LOGIN=false`**.
- Confirm **`APPLE_BUNDLE_ID`** matches the app (`com.codedancoffee.mommys-time`).
- Run behind HTTPS (e.g. `uvicorn`/`gunicorn` behind a reverse proxy).
