"""End-to-end smoke test using dev login (no real Apple token needed).

Run:  ALLOW_DEV_LOGIN=true python smoke_test.py
Exits non-zero on failure.
"""
import os

os.environ.setdefault("ALLOW_DEV_LOGIN", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:///./smoke.db")

# Import after env is set so Settings picks it up.
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def main() -> None:
    with TestClient(app) as client:
        assert client.get("/").json()["status"] == "ok"

        # Two different "users" via the dev shortcut.
        a = client.post("/auth/apple", json={"dev_apple_sub": "u-aina", "full_name": "Aina"})
        assert a.status_code == 200, a.text
        token_a = a.json()["access_token"]
        auth_a = {"Authorization": f"Bearer {token_a}"}

        b = client.post("/auth/apple", json={"dev_apple_sub": "u-mei", "full_name": "Mei"})
        token_b = b.json()["access_token"]
        auth_b = {"Authorization": f"Bearer {token_b}"}

        # /me reflects the token.
        assert client.get("/auth/me", headers=auth_a).json()["display_name"] == "Aina"

        # Aina creates a thread.
        created = client.post(
            "/threads",
            headers=auth_a,
            json={"topic": "Nights", "title": "3am again", "body": "Hi village"},
        )
        assert created.status_code == 201, created.text
        thread = created.json()
        assert thread["author"] == "Aina" and thread["is_mine"] is True
        tid = thread["id"]

        # Mei sees it and it's not hers.
        listing = client.get("/threads", headers=auth_b).json()
        assert any(t["id"] == tid and t["is_mine"] is False for t in listing)

        # Mei replies + hugs.
        r = client.post(f"/threads/{tid}/replies", headers=auth_b, json={"body": "We've got this"})
        assert r.status_code == 201, r.text
        hugged = client.post(f"/threads/{tid}/hug", headers=auth_b).json()
        assert hugged["hug_count"] == 1 and hugged["hugged"] is True

        # Detail shows the reply and correct counts.
        detail = client.get(f"/threads/{tid}", headers=auth_a).json()
        assert detail["reply_count"] == 1 and len(detail["replies"]) == 1
        assert detail["hug_count"] == 1
        assert detail["hugged"] is False  # Aina didn't hug her own thread

        # Topic filter works.
        assert all(t["topic"] == "Nights" for t in client.get("/threads?topic=Nights").json())

        # Mei can't delete Aina's thread.
        assert client.delete(f"/threads/{tid}", headers=auth_b).status_code == 403
        # Aina can.
        assert client.delete(f"/threads/{tid}", headers=auth_a).status_code == 204

    print("SMOKE TEST PASSED ✅")


if __name__ == "__main__":
    main()
