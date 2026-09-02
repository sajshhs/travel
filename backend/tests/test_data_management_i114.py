"""Iteration 114 — MANAJEMEN DATA (backup/restore/upload/schedule/cron/RBAC)."""
import io
import os
import time
import uuid
import zipfile
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values

fe = dotenv_values("/app/frontend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or fe.get("REACT_APP_BACKEND_URL") or "").rstrip("/")
if not BASE_URL:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BE = dotenv_values("/app/backend/.env")
CRON_SECRET = (BE.get("WEBHOOK_CRON_SECRET") or "").strip('"').strip("'")
BACKUP_DIR = Path("/app/backend/backups")
PW = "demo12345"

STATE = {}


def login(email, password=PW):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=60)
    assert r.status_code == 200, f"login {email} -> {r.status_code} {r.text[:300]}"
    d = r.json()
    tok = d.get("token") or d.get("access_token") or (d.get("session") or {}).get("token")
    assert tok, f"no token in {d}"
    return tok


def H(tok):
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="session")
def owner():
    return login("owner@demo.local")


# ---------------------------------------------------------------- overview
class TestOverview:
    def test_overview_shape(self, owner):
        r = requests.get(f"{BASE_URL}/api/data/overview", headers=H(owner), timeout=120)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        for k in ("backups", "storage", "schedule", "collections", "restores"):
            assert k in d, f"missing key {k}"
        assert "total_label" in d["storage"] and "disk_free_label" in d["storage"]
        for k in ("enabled", "keep_last", "include_media"):
            assert k in d["schedule"]
        assert isinstance(d["collections"], list) and len(d["collections"]) > 10
        assert all("name" in c and "count" in c for c in d["collections"])
        assert isinstance(d["restores"], list)
        assert "_id" not in str(d)[:200000] or '"_id"' not in str(d)

    def test_overview_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/data/overview", timeout=60)
        assert r.status_code in (401, 403), r.status_code


# ---------------------------------------------------------------- create/manifest/download
class TestBackupCreate:
    def test_create_manual_backup(self, owner):
        r = requests.post(f"{BASE_URL}/api/data/backups", headers=H(owner), json={"note": "uji"}, timeout=300)
        assert r.status_code == 200, r.text[:400]
        m = r.json()
        STATE["backup_id"] = m["id"]
        STATE["filename"] = m["filename"]
        assert m["filename"].startswith("backup_") and m["filename"].endswith(".zip")
        assert m["kind"] == "manual"
        assert m["collections"] > 50, f"collections={m['collections']}"
        assert m["documents"] > 0
        assert m["media_files"] > 0, "no media files in archive"
        assert m["size_label"]
        assert (BACKUP_DIR / m["filename"]).exists(), "physical archive missing"

    def test_manifest(self, owner):
        bid = STATE["backup_id"]
        r = requests.get(f"{BASE_URL}/api/data/backups/{bid}/manifest", headers=H(owner), timeout=120)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        man = d["manifest"]
        assert man["format_version"] == 1
        cols = man["collections"]
        assert isinstance(cols, list) and len(cols) > 50
        assert all("name" in c and "count" in c for c in cols)
        STATE["manifest"] = man

    def test_download_zip_content(self, owner):
        bid = STATE["backup_id"]
        r = requests.get(f"{BASE_URL}/api/data/backups/{bid}/download", headers=H(owner), timeout=300)
        assert r.status_code == 200, r.text[:200]
        assert "zip" in r.headers.get("content-type", ""), r.headers.get("content-type")
        zf = zipfile.ZipFile(io.BytesIO(r.content))
        names = zf.namelist()
        assert "manifest.json" in names
        assert any(n.startswith("db/") and n.endswith(".jsonl") for n in names)
        assert any(n.startswith("media/") for n in names)
        STATE["zip_bytes"] = r.content

    def test_unknown_id_404(self, owner):
        for path in ("manifest", "download"):
            r = requests.get(f"{BASE_URL}/api/data/backups/bak_nonexistent/{path}", headers=H(owner), timeout=60)
            assert r.status_code == 404, f"{path} -> {r.status_code}"


# ---------------------------------------------------------------- restore partial
class TestRestorePartial:
    def test_partial_restore_customers(self, owner):
        h = H(owner)
        lst = requests.get(f"{BASE_URL}/api/customers", headers=h, timeout=120)
        assert lst.status_code == 200, lst.text[:200]
        data = lst.json()
        items = data if isinstance(data, list) else (data.get("items") or data.get("data") or [])
        assert items, "no customers seeded"
        before = len(items)
        cid = items[0].get("id")
        d = requests.delete(f"{BASE_URL}/api/customers/{cid}", headers=h, timeout=120)
        if d.status_code not in (200, 204):
            # Customer with bookings can't be deleted via API -> remove directly in Mongo
            from pymongo import MongoClient
            cl = MongoClient(BE["MONGO_URL"])
            res = cl[BE["DB_NAME"]]["customers"].delete_one({"id": cid})
            cl.close()
            assert res.deleted_count == 1, f"could not delete customer {cid} in Mongo"
        chk = requests.get(f"{BASE_URL}/api/customers", headers=h, timeout=120).json()
        chk_items = chk if isinstance(chk, list) else (chk.get("items") or chk.get("data") or [])
        assert len(chk_items) == before - 1, f"pre-restore count {len(chk_items)} expected {before - 1}"
        r = requests.post(f"{BASE_URL}/api/data/restore", headers=h, timeout=600, json={
            "backup_id": STATE["backup_id"], "collections": ["customers"], "include_media": False, "confirm": "RESTORE"})
        assert r.status_code == 200, r.text[:400]
        log = r.json()
        assert log["mode"] == "partial"
        assert [c["name"] for c in log["collections"]] == ["customers"]
        assert log["collections"][0]["count"] >= before
        assert log.get("snapshot_id"), "snapshot_id empty"
        STATE["snapshot_id"] = log["snapshot_id"]
        after = requests.get(f"{BASE_URL}/api/customers", headers=h, timeout=120).json()
        after_items = after if isinstance(after, list) else (after.get("items") or after.get("data") or [])
        assert len(after_items) == before, f"customers {len(after_items)} != {before}"

    def test_pre_restore_entry_exists(self, owner):
        r = requests.get(f"{BASE_URL}/api/data/overview", headers=H(owner), timeout=120)
        kinds = [b["kind"] for b in r.json()["backups"]]
        assert "pre_restore" in kinds
        ids = [b["id"] for b in r.json()["backups"]]
        assert STATE["snapshot_id"] in ids

    def test_wrong_confirm_400(self, owner):
        r = requests.post(f"{BASE_URL}/api/data/restore", headers=H(owner), timeout=120, json={
            "backup_id": STATE["backup_id"], "collections": ["customers"], "include_media": False, "confirm": "nope"})
        assert r.status_code == 400, r.status_code

    def test_unknown_collection_400(self, owner):
        r = requests.post(f"{BASE_URL}/api/data/restore", headers=H(owner), timeout=120, json={
            "backup_id": STATE["backup_id"], "collections": ["zzz_not_a_collection"], "include_media": False, "confirm": "RESTORE"})
        assert r.status_code == 400, r.status_code

    def test_unknown_backup_id_400_404(self, owner):
        r = requests.post(f"{BASE_URL}/api/data/restore", headers=H(owner), timeout=120, json={
            "backup_id": "bak_unknown_xyz", "collections": ["customers"], "include_media": False, "confirm": "RESTORE"})
        assert r.status_code in (400, 404), r.status_code


# ---------------------------------------------------------------- upload
class TestUpload:
    def test_upload_valid_zip(self, owner):
        content = STATE.get("zip_bytes")
        assert content, "download test must run first"
        r = requests.post(f"{BASE_URL}/api/data/backups/upload", headers=H(owner), timeout=600,
                          files={"file": ("backup_test.zip", content, "application/zip")})
        assert r.status_code == 200, r.text[:400]
        m = r.json()
        assert m["kind"] == "uploaded"
        man = STATE["manifest"]
        assert m["collections"] == len(man["collections"]), f"{m['collections']} vs {len(man['collections'])}"
        assert m["documents"] == sum(int(c.get("count") or 0) for c in man["collections"])
        STATE["uploaded_id"] = m["id"]
        STATE["uploaded_file"] = m["filename"]

    def test_upload_non_zip_400(self, owner):
        r = requests.post(f"{BASE_URL}/api/data/backups/upload", headers=H(owner), timeout=120,
                          files={"file": ("notes.txt", b"hello", "text/plain")})
        assert r.status_code == 400, r.status_code

    def test_upload_zip_without_manifest_400(self, owner):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("db/customers.jsonl", "{}\n")
        r = requests.post(f"{BASE_URL}/api/data/backups/upload", headers=H(owner), timeout=120,
                          files={"file": ("bad.zip", buf.getvalue(), "application/zip")})
        assert r.status_code == 400, r.status_code

    def test_delete_uploaded(self, owner):
        bid = STATE["uploaded_id"]
        fn = STATE["uploaded_file"]
        r = requests.delete(f"{BASE_URL}/api/data/backups/{bid}", headers=H(owner), timeout=120)
        assert r.status_code == 200, r.text[:200]
        assert not (BACKUP_DIR / fn).exists(), "physical file still present"
        r2 = requests.get(f"{BASE_URL}/api/data/backups/{bid}/manifest", headers=H(owner), timeout=60)
        assert r2.status_code == 404
        r3 = requests.delete(f"{BASE_URL}/api/data/backups/bak_nope/", headers=H(owner), timeout=60)
        r3 = requests.delete(f"{BASE_URL}/api/data/backups/bak_nope", headers=H(owner), timeout=60)
        assert r3.status_code == 404, r3.status_code


# ---------------------------------------------------------------- schedule + cron
class TestScheduleCron:
    def test_get_and_patch_schedule(self, owner):
        h = H(owner)
        r = requests.get(f"{BASE_URL}/api/data/schedule", headers=h, timeout=60)
        assert r.status_code == 200
        p = requests.patch(f"{BASE_URL}/api/data/schedule", headers=h, json={"enabled": False, "keep_last": 3}, timeout=60)
        assert p.status_code == 200, p.text[:200]
        assert p.json()["enabled"] is False and p.json()["keep_last"] == 3
        g = requests.get(f"{BASE_URL}/api/data/schedule", headers=h, timeout=60).json()
        assert g["enabled"] is False and g["keep_last"] == 3

    def test_patch_keep_last_zero_422(self, owner):
        r = requests.patch(f"{BASE_URL}/api/data/schedule", headers=H(owner), json={"keep_last": 0}, timeout=60)
        assert r.status_code == 422, r.status_code

    def test_cron_unauthorized(self):
        r = requests.post(f"{BASE_URL}/api/cron/backup-daily", json={"event": "schedule.triggered", "run_id": "x"}, timeout=60)
        assert r.status_code == 401, r.status_code

    def test_cron_disabled_skipped(self, owner):
        assert CRON_SECRET, "WEBHOOK_CRON_SECRET missing"
        rid = f"t114-skip-{uuid.uuid4().hex[:8]}"
        hdr = {"Authorization": f"Bearer {CRON_SECRET}", "X-Webhook-Id": rid}
        r = requests.post(f"{BASE_URL}/api/cron/backup-daily", headers=hdr,
                          json={"event": "schedule.triggered", "run_id": rid}, timeout=60)
        assert r.status_code == 200 and r.json().get("queued") is True, r.text[:200]
        d = requests.post(f"{BASE_URL}/api/cron/backup-daily", headers=hdr,
                          json={"event": "schedule.triggered", "run_id": rid}, timeout=60)
        assert d.status_code == 200 and d.json().get("duplicate") is True, d.text[:200]
        time.sleep(6)
        s = requests.get(f"{BASE_URL}/api/data/schedule", headers=H(owner), timeout=60).json()
        assert s.get("last_status") == "skipped", s.get("last_status")

    def test_cron_enabled_creates_auto_and_retention(self, owner):
        h = H(owner)
        p = requests.patch(f"{BASE_URL}/api/data/schedule", headers=h, json={"enabled": True, "keep_last": 1}, timeout=60)
        assert p.status_code == 200
        for i in range(2):
            rid = f"t114-auto-{uuid.uuid4().hex[:8]}"
            r = requests.post(f"{BASE_URL}/api/cron/backup-daily", timeout=120,
                              headers={"Authorization": f"Bearer {CRON_SECRET}", "X-Webhook-Id": rid},
                              json={"event": "schedule.triggered", "run_id": rid})
            assert r.status_code == 200, r.text[:200]
            time.sleep(25)
        s = requests.get(f"{BASE_URL}/api/data/schedule", headers=h, timeout=60).json()
        assert (s.get("last_status") or "").startswith("ok: backup_"), s.get("last_status")
        ov = requests.get(f"{BASE_URL}/api/data/overview", headers=h, timeout=120).json()
        autos = [b for b in ov["backups"] if b["kind"] == "auto"]
        assert len(autos) <= 1, f"retention failed, {len(autos)} auto archives"
        # restore schedule defaults
        requests.patch(f"{BASE_URL}/api/data/schedule", headers=h, json={"enabled": True, "keep_last": 7}, timeout=60)


# ---------------------------------------------------------------- RBAC
class TestRBAC:
    def test_ops_admin_allowed(self):
        tok = login("ops@demo.local")
        r = requests.get(f"{BASE_URL}/api/data/overview", headers=H(tok), timeout=120)
        assert r.status_code == 200, r.status_code
        c = requests.post(f"{BASE_URL}/api/data/backups", headers=H(tok), json={"note": "TEST_ops"}, timeout=300)
        assert c.status_code == 200, c.text[:300]
        STATE["ops_backup_id"] = c.json()["id"]

    @pytest.mark.parametrize("email", ["marketing@demo.local", "driver@demo.local"])
    def test_denied_roles(self, email):
        tok = login(email)
        r = requests.get(f"{BASE_URL}/api/data/overview", headers=H(tok), timeout=60)
        assert r.status_code == 403, f"{email} overview -> {r.status_code}"
        c = requests.post(f"{BASE_URL}/api/data/backups", headers=H(tok), json={"note": "x"}, timeout=60)
        assert c.status_code == 403, f"{email} create -> {c.status_code}"


# ---------------------------------------------------------------- full restore (last)
class TestZFullRestore:
    def test_full_restore(self, owner):
        h = H(owner)
        fresh = requests.post(f"{BASE_URL}/api/data/backups", headers=h, json={"note": "TEST_full_src"}, timeout=300)
        assert fresh.status_code == 200, fresh.text[:300]
        bid = fresh.json()["id"]
        r = requests.post(f"{BASE_URL}/api/data/restore", headers=h, timeout=900, json={
            "backup_id": bid, "collections": None, "include_media": True, "confirm": "RESTORE"})
        assert r.status_code == 200, r.text[:400]
        log = r.json()
        assert log["mode"] == "full"
        assert log["documents"] > 0
        assert log["media_files"] > 0
        tok2 = login("owner@demo.local")
        b = requests.get(f"{BASE_URL}/api/bookings", headers=H(tok2), timeout=120)
        assert b.status_code == 200, b.status_code
        STATE["full_src_id"] = bid


# ---------------------------------------------------------------- cleanup
def test_zz_cleanup():
    tok = login("owner@demo.local")
    h = H(tok)
    ov = requests.get(f"{BASE_URL}/api/data/overview", headers=h, timeout=120).json()
    keep = 2
    rows = ov["backups"]
    for b in rows[keep:]:
        requests.delete(f"{BASE_URL}/api/data/backups/{b['id']}", headers=h, timeout=120)
    left = requests.get(f"{BASE_URL}/api/data/overview", headers=h, timeout=120).json()["backups"]
    assert len(left) <= keep
