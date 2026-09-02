"""Iterasi 113 — NOTA REFUND: cancel booking dgn refund → nota otomatis (+WA mock),
endpoint /api/documents/refund-notes (list/create/pdf/send-wa), layout REFUND_NOTE,
naskah, penomoran key `refund`, config wa_caption_refund."""
import os
import random
import re
from datetime import datetime, timedelta, timezone

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE = base_url.rstrip("/")
OWNER = ("owner@demo.local", "demo12345")


def _login(email, password):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": password}, timeout=60)
    if r.status_code != 200:
        pytest.fail(f"Login {email} gagal {r.status_code}: {r.text[:300]}")
    tok = r.json().get("token") or r.json().get("access_token")
    if not tok:
        pytest.fail(f"Token tidak ada: {r.text[:300]}")
    return tok


@pytest.fixture(scope="session")
def owner():
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {_login(*OWNER)}", "Content-Type": "application/json"})
    return s


def _rows(data):
    return data.get("data") if isinstance(data, dict) else data


_offset = {"n": 0}


def make_booking(owner, *, price=1000000, pay=None):
    """Buat booking confirmed baru (+pembayaran opsional). Return booking dict fresh."""
    cust = _rows(owner.get(f"{BASE}/api/customers?limit=20", timeout=60).json())
    veh = _rows(owner.get(f"{BASE}/api/vehicles?limit=20", timeout=60).json())
    assert cust and veh, "Seed customers/vehicles kosong"
    _offset["n"] += 1
    start = datetime.now(timezone.utc) + timedelta(days=200 + random.randint(0, 400) + _offset["n"] * 3)
    body = {"customer_id": cust[0]["id"], "vehicle_id": veh[0]["id"],
            "origin": "Jakarta", "destination": "Bandung",
            "start_datetime": start.isoformat(), "end_datetime": (start + timedelta(days=1)).isoformat(),
            "base_price": price, "notes": "TEST_i113 refund"}
    r = owner.post(f"{BASE}/api/bookings", json=body, timeout=90)
    assert r.status_code in (200, 201), f"create booking gagal {r.status_code}: {r.text[:400]}"
    bk = r.json()
    bid = bk.get("id") or bk.get("booking", {}).get("id")
    assert bid, bk
    if pay:
        p = owner.post(f"{BASE}/api/payments", json={"booking_id": bid, "amount": pay, "type": "dp", "method": "transfer"}, timeout=90)
        assert p.status_code in (200, 201), f"payment gagal {p.status_code}: {p.text[:400]}"
    g = owner.get(f"{BASE}/api/bookings/{bid}", timeout=60)
    assert g.status_code == 200, g.text[:300]
    return g.json()


# ------------------------------------------------------------------ cancel + nota otomatis
class TestCancelWithRefund:
    def test_cancel_with_refund_creates_note_and_wa(self, owner):
        bk = make_booking(owner, price=1000000, pay=400000)
        assert float(bk.get("paid_amount") or 0) >= 400000, bk
        r = owner.post(f"{BASE}/api/bookings/{bk['id']}/cancel", json={
            "reason": "Uji refund", "cancellation_fee": 100000, "refund_amount": 200000, "send_refund_wa": True}, timeout=120)
        assert r.status_code == 200, r.text[:500]
        out = r.json()
        note = out.get("refund_note")
        assert note, f"refund_note kosong: {out}"
        assert re.match(r"^RFD/\d{4}/\d{2}/\d{4}$", note["number"]), note["number"]
        assert note["refund_amount"] == 200000, note
        assert note["cancellation_fee"] == 100000, note
        assert "dua ratus ribu rupiah" in note["amount_words"], note["amount_words"]
        assert note["reason"] == "Uji refund"
        assert "_id" not in note
        assert (out.get("refund_wa") or {}).get("status") == "sent", out.get("refund_wa")
        pytest.i113_note = note
        pytest.i113_booking = bk["id"]

    def test_cancel_idempotent_no_second_note(self, owner):
        bid = getattr(pytest, "i113_booking", None)
        assert bid, "test sebelumnya gagal"
        r = owner.post(f"{BASE}/api/bookings/{bid}/cancel", json={
            "reason": "Uji refund", "cancellation_fee": 100000, "refund_amount": 200000, "send_refund_wa": True}, timeout=120)
        assert r.status_code == 200, r.text[:400]
        lst = owner.get(f"{BASE}/api/documents/refund-notes?booking_id={bid}", timeout=60)
        assert lst.status_code == 200
        notes = lst.json()
        assert len(notes) == 1, f"nota ganda: {[n['number'] for n in notes]}"
        assert notes[0]["number"] == pytest.i113_note["number"]

    def test_cancel_zero_refund_no_note(self, owner):
        bk = make_booking(owner, price=800000, pay=300000)
        r = owner.post(f"{BASE}/api/bookings/{bk['id']}/cancel", json={
            "reason": "Tanpa refund", "cancellation_fee": 50000, "refund_amount": 0}, timeout=120)
        assert r.status_code == 200, r.text[:400]
        assert r.json().get("refund_note") is None, r.json().get("refund_note")
        pytest.i113_norefund = bk["id"]

    def test_create_note_for_zero_refund_booking_400(self, owner):
        r = owner.post(f"{BASE}/api/documents/refund-notes", json={"booking_id": pytest.i113_norefund}, timeout=60)
        assert r.status_code == 400, f"{r.status_code} {r.text[:300]}"

    def test_create_note_for_active_booking_400(self, owner):
        bk = make_booking(owner, price=500000)
        r = owner.post(f"{BASE}/api/documents/refund-notes", json={"booking_id": bk["id"]}, timeout=60)
        assert r.status_code == 400, f"{r.status_code} {r.text[:300]}"

    def test_create_note_unknown_booking_404(self, owner):
        r = owner.post(f"{BASE}/api/documents/refund-notes", json={"booking_id": "bk_doesnotexist_113"}, timeout=60)
        assert r.status_code == 404, f"{r.status_code} {r.text[:300]}"


# ------------------------------------------------------------------ endpoint nota refund
class TestRefundNoteEndpoints:
    def test_list_contains_note(self, owner):
        r = owner.get(f"{BASE}/api/documents/refund-notes", timeout=60)
        assert r.status_code == 200, r.text[:300]
        rows = r.json()
        assert isinstance(rows, list) and rows
        assert any(n["number"] == pytest.i113_note["number"] for n in rows)

    def test_pdf_attachment_and_inline(self, owner):
        nid = pytest.i113_note["id"]
        r = owner.get(f"{BASE}/api/documents/refund-notes/{nid}/pdf", timeout=120)
        assert r.status_code == 200, r.text[:300]
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert len(r.content) > 1024 and r.content[:4] == b"%PDF", (len(r.content), r.content[:8])
        assert "attachment" in r.headers.get("content-disposition", "")
        r2 = owner.get(f"{BASE}/api/documents/refund-notes/{nid}/pdf?inline=true", timeout=120)
        assert r2.status_code == 200 and "inline" in r2.headers.get("content-disposition", "")

    def test_pdf_404(self, owner):
        r = owner.get(f"{BASE}/api/documents/refund-notes/rfn_nope/pdf", timeout=60)
        assert r.status_code == 404

    def test_send_wa_increments_sent_count(self, owner):
        nid = pytest.i113_note["id"]
        before = [n for n in owner.get(f"{BASE}/api/documents/refund-notes?booking_id={pytest.i113_booking}", timeout=60).json()][0]
        r = owner.post(f"{BASE}/api/documents/refund-notes/{nid}/send-wa", timeout=120)
        assert r.status_code == 200, r.text[:400]
        body = r.json()
        assert body.get("status") == "sent", body
        assert body.get("number") == pytest.i113_note["number"]
        after = [n for n in owner.get(f"{BASE}/api/documents/refund-notes?booking_id={pytest.i113_booking}", timeout=60).json()][0]
        assert int(after.get("sent_count") or 0) == int(before.get("sent_count") or 0) + 1, (before.get("sent_count"), after.get("sent_count"))
        assert after.get("sent_at")

    def test_post_existing_booking_returns_same_note(self, owner):
        r = owner.post(f"{BASE}/api/documents/refund-notes", json={"booking_id": pytest.i113_booking}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["id"] == pytest.i113_note["id"]
        assert r.json()["number"] == pytest.i113_note["number"]

    def test_booking_documents_bundle_has_refund_note(self, owner):
        r = owner.get(f"{BASE}/api/documents/booking/{pytest.i113_booking}", timeout=60)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert data.get("refund_note"), data.keys()
        assert data["refund_note"]["number"] == pytest.i113_note["number"]


# ------------------------------------------------------------------ layout / naskah / penomoran / config
class TestLayoutScriptNumbering:
    def test_layout_codes_include_refund(self, owner):
        r = owner.get(f"{BASE}/api/documents/layouts", timeout=60)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        codes = data.get("data") if isinstance(data, dict) else data
        keys = [c.get("code") if isinstance(c, dict) else c for c in codes]
        assert "REFUND_NOTE" in keys, keys
        assert len(keys) == 8, keys

    def test_script_placeholders(self, owner):
        r = owner.get(f"{BASE}/api/documents/layouts/REFUND_NOTE/script", timeout=60)
        assert r.status_code == 200, r.text[:300]
        sc = r.json()
        intro = (sc.get("script") or sc).get("intro") if isinstance(sc.get("script"), dict) else sc.get("intro")
        assert "{{refund_amount}}" in intro or "{refund_amount}" in intro, intro
        ph = str(sc)
        assert "cancellation_reason" in ph, "placeholder cancellation_reason tidak terdaftar"

    def test_put_script_valid(self, owner):
        cur = owner.get(f"{BASE}/api/documents/layouts/REFUND_NOTE/script", timeout=60).json()
        src = cur.get("script") if isinstance(cur.get("script"), dict) else cur
        r = owner.put(f"{BASE}/api/documents/layouts/REFUND_NOTE/script", json={
            "intro": "Refund {{refund_amount}} atas pembatalan ({{cancellation_reason}}) booking {{booking_code}}.",
            "closing": src.get("closing") or "", "terms": src.get("terms") or ""}, timeout=60)
        assert r.status_code == 200, r.text[:400]
        owner.delete(f"{BASE}/api/documents/layouts/REFUND_NOTE/script", timeout=60)

    def test_put_script_unknown_placeholder_400(self, owner):
        r = owner.put(f"{BASE}/api/documents/layouts/REFUND_NOTE/script", json={
            "intro": "Refund {{tidak_dikenal}}", "closing": "", "terms": ""}, timeout=60)
        assert r.status_code == 400, f"{r.status_code} {r.text[:300]}"

    def test_layout_preview_pdf(self, owner):
        r = owner.post(f"{BASE}/api/documents/layouts/REFUND_NOTE/preview", json={}, timeout=120)
        assert r.status_code == 200, r.text[:300]
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert len(r.content) > 1024

    def test_numbering_has_refund_rule(self, owner):
        r = owner.get(f"{BASE}/api/documents/numbering", timeout=60)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        rules = data.get("data") if isinstance(data, dict) else data
        keys = [x["key"] for x in rules]
        assert "refund" in keys and len(rules) == 5, keys
        rr = next(x for x in rules if x["key"] == "refund")
        assert rr["preview"].startswith("RFD/"), rr["preview"]

    def test_numbering_override_applies_to_next_note(self, owner):
        r = owner.put(f"{BASE}/api/documents/numbering/refund", json={
            "pattern": "{PREFIX}-{YYYY}-{SEQ}", "prefix": "RF", "width": 4, "reset": "yearly"}, timeout=60)
        assert r.status_code == 200, r.text[:400]
        try:
            bk = make_booking(owner, price=900000, pay=500000)
            c = owner.post(f"{BASE}/api/bookings/{bk['id']}/cancel", json={
                "reason": "Uji pola nomor", "cancellation_fee": 0, "refund_amount": 150000}, timeout=120)
            assert c.status_code == 200, c.text[:400]
            note = c.json().get("refund_note")
            assert note, c.json()
            assert re.match(r"^RF-\d{4}-\d{4}$", note["number"]), note["number"]
        finally:
            d = owner.delete(f"{BASE}/api/documents/numbering/refund", timeout=60)
            assert d.status_code == 200, d.text[:300]
        rules = owner.get(f"{BASE}/api/documents/numbering", timeout=60).json()["data"]
        rr = next(x for x in rules if x["key"] == "refund")
        assert rr["pattern"] == "{PREFIX}/{YYYY}/{MM}/{SEQ}", rr["pattern"]

    def test_config_wa_caption_refund(self, owner):
        r = owner.get(f"{BASE}/api/documents/config", timeout=60)
        assert r.status_code == 200
        cfg = r.json()
        assert "wa_caption_refund" in cfg, list(cfg.keys())
        orig = cfg["wa_caption_refund"]
        assert "{{refund_amount}}" in orig
        ok = owner.patch(f"{BASE}/api/documents/config", json={
            "wa_caption_refund": "Refund {{refund_amount}} untuk {{booking_code}} — nota {{doc_number}}."}, timeout=60)
        assert ok.status_code == 200, ok.text[:300]
        assert owner.get(f"{BASE}/api/documents/config", timeout=60).json()["wa_caption_refund"].startswith("Refund ")
        bad = owner.patch(f"{BASE}/api/documents/config", json={"wa_caption_refund": "Refund {{token_asing}}"}, timeout=60)
        assert bad.status_code == 400, f"{bad.status_code} {bad.text[:300]}"
        owner.patch(f"{BASE}/api/documents/config", json={"wa_caption_refund": orig}, timeout=60)


# ------------------------------------------------------------------ regresi: kwitansi utk payment refund (negatif)
class TestReceiptForRefundPayment:
    """BUG i113: tombol 'Terbitkan Kwitansi' pada baris pembayaran refund (nominal negatif)
    memanggil POST /api/documents/receipts → 500 (terbilang() IndexError utk angka negatif)."""

    def test_receipt_for_negative_refund_payment_not_500(self, owner):
        bk = make_booking(owner, price=1200000, pay=600000)
        c = owner.post(f"{BASE}/api/bookings/{bk['id']}/cancel", json={
            "reason": "Uji kwitansi refund", "cancellation_fee": 0, "refund_amount": 200000}, timeout=120)
        assert c.status_code == 200, c.text[:300]
        pays = owner.get(f"{BASE}/api/payments?booking_id={bk['id']}", timeout=60).json()
        pays = pays.get("data") if isinstance(pays, dict) else pays
        ref = [p for p in pays if p.get("type") == "refund"]
        assert ref, pays
        r = owner.post(f"{BASE}/api/documents/receipts", json={"payment_id": ref[0]["id"]}, timeout=90)
        assert r.status_code != 500, f"500 dari terbilang() angka negatif: {r.text[:200]}"
        assert r.status_code in (200, 400, 422), r.status_code
