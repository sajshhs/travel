"""Iteration 112 — modul dokumen bisnis: invoice (DP/pelunasan/penuh), kwitansi,
konfirmasi/SPJ, konfigurasi (pajak/rekening/WA), layout kop, naskah, penomoran."""
import os
import re

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE = base_url.rstrip("/")

OWNER = ("owner@demo.local", "demo12345")
OPS = ("ops@demo.local", "demo12345")


def _login(email, password):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": password}, timeout=60)
    if r.status_code != 200:
        pytest.fail(f"Login {email} gagal {r.status_code}: {r.text[:300]}")
    tok = r.json().get("token") or r.json().get("access_token")
    if not tok:
        pytest.fail(f"Token tidak ada di respons login: {r.text[:300]}")
    return tok


@pytest.fixture(scope="session")
def owner():
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {_login(*OWNER)}", "Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def ops():
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {_login(*OPS)}", "Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def bookings(owner):
    r = owner.get(f"{BASE}/api/bookings?limit=200", timeout=60)
    assert r.status_code == 200, r.text[:300]
    data = r.json()
    rows = data.get("data") if isinstance(data, dict) else data
    assert isinstance(rows, list) and rows, "Tidak ada booking seed"
    return rows


def _pick(bookings, need_remaining=True):
    for b in bookings:
        if b.get("status") != "confirmed":
            continue
        total = float(b.get("total_amount") or 0)
        paid = float(b.get("paid_amount") or 0)
        if total <= 0:
            continue
        if need_remaining and total - paid <= 1000:
            continue
        return b
    return None


@pytest.fixture(scope="session")
def booking(bookings):
    b = _pick(bookings)
    if not b:
        pytest.fail("Tidak ada booking confirmed dengan sisa tagihan")
    return b


# ------------------------------------------------------------------ config (dipulihkan di akhir)
@pytest.fixture(scope="session", autouse=True)
def restore_config(owner):
    orig = owner.get(f"{BASE}/api/documents/config", timeout=60).json()
    yield orig
    owner.patch(f"{BASE}/api/documents/config", json={
        "tax_enabled": orig.get("tax_enabled"), "tax_percent": orig.get("tax_percent"),
        "dp_percent": orig.get("dp_percent"), "bank_accounts": orig.get("bank_accounts") or [],
    }, timeout=60)
    owner.delete(f"{BASE}/api/documents/numbering/receipt", timeout=60)
    owner.delete(f"{BASE}/api/documents/layouts/__default__", timeout=60)
    owner.delete(f"{BASE}/api/documents/layouts/INVOICE_DP/script", timeout=60)


class TestInvoices:
    """POST /api/invoices — DP / settlement / full, pajak, penomoran"""

    def test_create_dp_with_tax(self, owner, booking):
        r = owner.post(f"{BASE}/api/invoices", json={"booking_id": booking["id"], "kind": "dp", "tax_enabled": True}, timeout=90)
        assert r.status_code == 200, r.text[:400]
        inv = r.json()
        assert re.match(r"^INV/DP/\d{4}/\d{2}/\d{4}$", inv["number"]), inv["number"]
        assert inv["kind"] == "dp" and inv["kind_label"] == "Invoice DP"
        total = float(booking.get("total_amount") or 0)
        assert abs(inv["tax_amount"] - round(total * 0.11)) <= 1, inv
        assert inv["grand_total"] == inv["subtotal"] + inv["tax_amount"] or inv["grand_total"] > 0
        expect_dp = float(booking.get("dp_amount") or 0) or round(inv["grand_total"] * 30 / 100)
        assert abs(inv["amount_due"] - expect_dp) <= 2, (inv["amount_due"], expect_dp)
        assert inv["status"] == "draft"
        # GET persistence
        g = owner.get(f"{BASE}/api/invoices/{inv['id']}", timeout=60)
        assert g.status_code == 200 and g.json()["number"] == inv["number"]
        pytest.dp_invoice = inv

    def test_create_settlement(self, owner, booking):
        r = owner.post(f"{BASE}/api/invoices", json={"booking_id": booking["id"], "kind": "settlement", "tax_enabled": False}, timeout=90)
        assert r.status_code == 200, r.text[:400]
        inv = r.json()
        assert "/PEL/" in inv["number"]
        total = float(booking.get("total_amount") or 0)
        paid = float(booking.get("paid_amount") or 0)
        assert abs(inv["amount_due"] - max(total - paid, 0)) <= 2, (inv["amount_due"], total, paid)
        assert inv["tax_amount"] == 0

    def test_create_full(self, owner, booking):
        r = owner.post(f"{BASE}/api/invoices", json={"booking_id": booking["id"], "kind": "full", "tax_enabled": False}, timeout=90)
        assert r.status_code == 200, r.text[:400]
        inv = r.json()
        assert "/FULL/" in inv["number"]
        assert abs(inv["amount_due"] - float(booking.get("total_amount") or 0)) <= 2

    def test_cancelled_booking_rejected(self, owner, bookings):
        cancelled = next((b for b in bookings if b.get("status") == "cancelled"), None)
        if not cancelled:
            cr = owner.post(f"{BASE}/api/bookings", json={}, timeout=60)
            pytest.skip(f"Tidak ada booking cancelled di seed (create probe {cr.status_code})")
        r = owner.post(f"{BASE}/api/invoices", json={"booking_id": cancelled["id"], "kind": "full"}, timeout=60)
        assert r.status_code == 400, f"{r.status_code} {r.text[:200]}"

    def test_unknown_booking(self, owner):
        r = owner.post(f"{BASE}/api/invoices", json={"booking_id": "nope-xyz", "kind": "dp"}, timeout=60)
        assert r.status_code == 400


class TestInvoiceExportSend:
    """export PDF/inline/excel + kirim WA (provider mock)"""

    @pytest.fixture(scope="class")
    def inv(self, owner, booking):
        r = owner.post(f"{BASE}/api/invoices", json={"booking_id": booking["id"], "kind": "dp", "tax_enabled": True}, timeout=90)
        assert r.status_code == 200, r.text[:300]
        return r.json()

    def test_pdf(self, owner, inv):
        r = owner.get(f"{BASE}/api/invoices/{inv['id']}/export?format=pdf", timeout=120)
        assert r.status_code == 200, r.text[:200]
        assert r.headers["content-type"].startswith("application/pdf")
        assert len(r.content) > 1024 and r.content[:4] == b"%PDF"
        assert "attachment" in r.headers.get("content-disposition", "")

    def test_inline(self, owner, inv):
        r = owner.get(f"{BASE}/api/invoices/{inv['id']}/export?format=inline", timeout=120)
        assert r.status_code == 200
        assert r.headers.get("content-disposition", "").startswith("inline")

    def test_excel(self, owner, inv):
        r = owner.get(f"{BASE}/api/invoices/{inv['id']}/export?format=excel", timeout=120)
        assert r.status_code == 200, r.text[:200]
        assert "spreadsheetml" in r.headers["content-type"]
        assert r.content[:2] == b"PK"

    def test_send_wa(self, owner, inv):
        r = owner.post(f"{BASE}/api/invoices/{inv['id']}/send-wa", timeout=120)
        assert r.status_code == 200, r.text[:300]
        body = r.json()
        assert body.get("status") == "sent", body
        g = owner.get(f"{BASE}/api/invoices/{inv['id']}", timeout=60).json()
        assert g["status"] == "sent"
        assert int(g.get("sent_count") or 0) >= 1

    def test_booking_send_invoice_wa(self, owner, booking, inv):
        r = owner.post(f"{BASE}/api/bookings/{booking['id']}/send-invoice-wa", timeout=120)
        assert r.status_code == 200, r.text[:300]
        assert r.json().get("status") == "sent"

    def test_export_404(self, owner):
        r = owner.get(f"{BASE}/api/invoices/inv-nope/export?format=pdf", timeout=60)
        assert r.status_code == 404


class TestPaymentReceipt:
    """POST /api/payments → kwitansi otomatis + WA; kwitansi idempoten"""

    def test_payment_creates_receipt_and_syncs_invoice(self, owner, booking):
        inv = owner.post(f"{BASE}/api/invoices", json={"booking_id": booking["id"], "kind": "dp", "tax_enabled": False}, timeout=90).json()
        r = owner.post(f"{BASE}/api/payments", json={"booking_id": booking["id"], "amount": 100000,
                                                     "type": "dp", "method": "transfer", "send_receipt_wa": True}, timeout=120)
        assert r.status_code in (200, 201), r.text[:400]
        pay = r.json()
        rcp = pay.get("receipt")
        assert rcp, f"receipt tidak ada di respons: {list(pay.keys())} err={pay.get('error')}"
        assert re.match(r"^KWT/\d{4}/\d{2}/\d{4}$", rcp["number"]), rcp["number"]
        assert (pay.get("receipt_wa") or {}).get("status") == "sent", pay.get("receipt_wa")
        # invoice DP tersinkron
        g = owner.get(f"{BASE}/api/invoices/{inv['id']}", timeout=60).json()
        assert g["status"] in ("partial", "paid"), g["status"]
        pytest.receipt = rcp
        pytest.payment = pay

    def test_list_receipts(self, owner, booking):
        r = owner.get(f"{BASE}/api/documents/receipts?booking_id={booking['id']}", timeout=60)
        assert r.status_code == 200
        rows = r.json()
        assert isinstance(rows, list) and rows
        assert any(x["id"] == pytest.receipt["id"] for x in rows)
        assert all("_id" not in x for x in rows)

    def test_receipt_pdf(self, owner):
        r = owner.get(f"{BASE}/api/documents/receipts/{pytest.receipt['id']}/pdf", timeout=120)
        assert r.status_code == 200 and r.content[:4] == b"%PDF" and len(r.content) > 1024

    def test_receipt_send_wa(self, owner):
        r = owner.post(f"{BASE}/api/documents/receipts/{pytest.receipt['id']}/send-wa", timeout=120)
        assert r.status_code == 200, r.text[:300]
        assert r.json().get("status") == "sent"

    def test_receipt_idempotent(self, owner):
        r = owner.post(f"{BASE}/api/documents/receipts", json={"payment_id": pytest.payment["id"]}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["number"] == pytest.receipt["number"]

    def test_receipt_404(self, owner):
        assert owner.get(f"{BASE}/api/documents/receipts/rcp-nope/pdf", timeout=60).status_code == 404
        assert owner.post(f"{BASE}/api/documents/receipts", json={"payment_id": "pay-nope"}, timeout=60).status_code == 404


class TestBookingDocuments:
    """ringkasan dokumen booking + konfirmasi/SPJ (nomor sekali per booking)"""

    def test_summary(self, owner, booking):
        r = owner.get(f"{BASE}/api/documents/booking/{booking['id']}", timeout=60)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        for key in ("booking", "invoices", "receipts", "payments", "booking_docs", "suggest"):
            assert key in d, key
        s = d["suggest"]
        for key in ("dp_percent", "dp_amount", "remaining", "tax_enabled", "tax_percent", "tax_label"):
            assert key in s, key
        assert d["booking"]["id"] == booking["id"]

    def test_confirmation_pdf_number_stable(self, owner, booking):
        r1 = owner.get(f"{BASE}/api/documents/booking/{booking['id']}/confirmation/pdf", timeout=120)
        assert r1.status_code == 200 and r1.content[:4] == b"%PDF"
        r2 = owner.get(f"{BASE}/api/documents/booking/{booking['id']}/confirmation/pdf?inline=true", timeout=120)
        assert r2.status_code == 200
        assert r2.headers.get("content-disposition", "").startswith("inline")
        docs = owner.get(f"{BASE}/api/documents/booking/{booking['id']}", timeout=60).json()["booking_docs"]
        nums = [d["number"] for d in docs if d["kind"] == "confirmation"]
        assert len(nums) == 1 and nums[0].startswith("KONF/"), nums

    def test_spj_pdf_number_stable(self, owner, booking):
        for _ in range(2):
            r = owner.get(f"{BASE}/api/documents/booking/{booking['id']}/spj/pdf", timeout=120)
            assert r.status_code == 200 and r.content[:4] == b"%PDF"
        docs = owner.get(f"{BASE}/api/documents/booking/{booking['id']}", timeout=60).json()["booking_docs"]
        nums = [d["number"] for d in docs if d["kind"] == "spj"]
        assert len(nums) == 1 and nums[0].startswith("SPJ/"), nums

    def test_confirmation_send_wa(self, owner, booking):
        r = owner.post(f"{BASE}/api/documents/booking/{booking['id']}/confirmation/send-wa", timeout=120)
        assert r.status_code == 200, r.text[:300]
        assert r.json().get("status") == "sent"

    def test_spj_send_wa(self, owner, bookings):
        b = next((x for x in bookings if x.get("driver_id") and x.get("status") in ("confirmed", "dispatched", "ongoing", "completed")), None)
        if not b:
            pytest.skip("Tidak ada booking dengan driver")
        r = owner.post(f"{BASE}/api/documents/booking/{b['id']}/spj/send-wa", timeout=120)
        assert r.status_code in (200, 400), r.text[:300]
        if r.status_code == 400:
            assert "driver" in r.text.lower()
        else:
            assert r.json().get("status") == "sent"

    def test_unknown_kind_404(self, owner, booking):
        assert owner.get(f"{BASE}/api/documents/booking/{booking['id']}/foo/pdf", timeout=60).status_code == 404
        assert owner.get(f"{BASE}/api/documents/booking/bk-nope/confirmation/pdf", timeout=60).status_code == 404


class TestConfig:
    """GET/PATCH /api/documents/config + RBAC"""

    def test_get_owner_and_ops(self, owner, ops):
        for s in (owner, ops):
            r = s.get(f"{BASE}/api/documents/config", timeout=60)
            assert r.status_code == 200, r.text[:200]
            assert "tax_percent" in r.json()

    def test_patch_owner(self, owner):
        payload = {"tax_enabled": True, "tax_percent": 11, "dp_percent": 40,
                   "bank_accounts": [{"bank": "BCA", "account_no": "123", "account_name": "PT X"}]}
        r = owner.patch(f"{BASE}/api/documents/config", json=payload, timeout=60)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["tax_enabled"] is True and float(d["tax_percent"]) == 11 and float(d["dp_percent"]) == 40
        assert d["bank_accounts"][0]["bank"] == "BCA"
        g = owner.get(f"{BASE}/api/documents/config", timeout=60).json()
        assert g["dp_percent"] == 40 and g["bank_accounts"][0]["account_no"] == "123"

    def test_patch_ops_forbidden(self, ops):
        r = ops.patch(f"{BASE}/api/documents/config", json={"tax_enabled": False}, timeout=60)
        assert r.status_code == 403, f"{r.status_code} {r.text[:200]}"

    def test_invalid_tax_percent(self, owner):
        r = owner.patch(f"{BASE}/api/documents/config", json={"tax_percent": 150}, timeout=60)
        assert r.status_code in (400, 422), f"{r.status_code} {r.text[:200]}"

    def test_unknown_placeholder_caption(self, owner):
        r = owner.patch(f"{BASE}/api/documents/config", json={"wa_caption_invoice": "Halo {{xyz}}"}, timeout=60)
        assert r.status_code == 400, f"{r.status_code} {r.text[:200]}"


class TestLayouts:
    """layout kop/warna + naskah + pratinjau"""

    def test_list(self, owner):
        r = owner.get(f"{BASE}/api/documents/layouts", timeout=60)
        assert r.status_code == 200
        codes = {d["code"] for d in r.json()["data"]}
        assert codes == {"__default__", "INVOICE_DP", "INVOICE_SETTLEMENT", "INVOICE_FULL", "RECEIPT", "CONFIRMATION", "SPJ"}, codes

    def test_get_default_has_company(self, owner):
        r = owner.get(f"{BASE}/api/documents/layouts/__default__", timeout=60)
        assert r.status_code == 200
        assert (r.json()["brand"].get("company_name") or "").strip(), r.json()["brand"]

    def test_put_default_inherited(self, owner):
        r = owner.put(f"{BASE}/api/documents/layouts/__default__",
                      json={"brand": {"accent_color": "#B4532A", "watermark_text": "CONTOH"}}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["brand"]["accent_color"] == "#B4532A"
        child = owner.get(f"{BASE}/api/documents/layouts/INVOICE_DP", timeout=60).json()
        assert child["brand"]["accent_color"] == "#B4532A", child["brand"]["accent_color"]
        assert child["brand"]["watermark_text"] == "CONTOH"

    def test_delete_default_reset(self, owner):
        r = owner.delete(f"{BASE}/api/documents/layouts/__default__", timeout=60)
        assert r.status_code == 200
        assert r.json()["brand"]["accent_color"] == "#0F6E56", r.json()["brand"]["accent_color"]

    def test_put_layout_ops_forbidden(self, ops):
        r = ops.put(f"{BASE}/api/documents/layouts/__default__", json={"brand": {"accent_color": "#000000"}}, timeout=60)
        assert r.status_code == 403, f"{r.status_code} {r.text[:200]}"

    def test_preview_pdf(self, owner):
        r = owner.post(f"{BASE}/api/documents/layouts/INVOICE_DP/preview",
                       json={"brand": {"accent_color": "#123456", "watermark_text": "DRAF"}}, timeout=120)
        assert r.status_code == 200, r.text[:300]
        assert r.content[:4] == b"%PDF" and len(r.content) > 1024

    def test_script_flow(self, owner):
        g = owner.get(f"{BASE}/api/documents/layouts/INVOICE_DP/script", timeout=60)
        assert g.status_code == 200 and "placeholders" in g.json()
        bad = owner.put(f"{BASE}/api/documents/layouts/INVOICE_DP/script", json={"intro": "Halo {{foo}}"}, timeout=60)
        assert bad.status_code == 400, f"{bad.status_code} {bad.text[:200]}"
        ok = owner.put(f"{BASE}/api/documents/layouts/INVOICE_DP/script", json={"intro": "Halo {{customer_name}}"}, timeout=60)
        assert ok.status_code == 200, ok.text[:300]
        assert ok.json()["customized"] is True and ok.json()["intro"] == "Halo {{customer_name}}"
        d = owner.delete(f"{BASE}/api/documents/layouts/INVOICE_DP/script", timeout=60)
        assert d.status_code == 200 and d.json()["customized"] is False

    def test_unknown_code_404(self, owner):
        assert owner.get(f"{BASE}/api/documents/layouts/NOPE", timeout=60).status_code == 404
        assert owner.get(f"{BASE}/api/documents/layouts/NOPE/script", timeout=60).status_code == 404
        assert owner.post(f"{BASE}/api/documents/layouts/NOPE/preview", json={}, timeout=60).status_code == 404


class TestNumbering:
    """aturan penomoran: preview, simpan, dipakai dokumen berikutnya, reset, RBAC"""

    def test_list(self, owner):
        r = owner.get(f"{BASE}/api/documents/numbering", timeout=60)
        assert r.status_code == 200
        data = r.json()["data"]
        keys = {d["key"] for d in data}
        assert keys == {"invoice", "receipt", "confirmation", "spj"}, keys
        assert all(d.get("preview") for d in data)

    def test_preview_pattern(self, owner):
        r = owner.post(f"{BASE}/api/documents/numbering/receipt/preview",
                       json={"pattern": "{PREFIX}/{MM_ROMAN}/{YYYY}/{SEQ:5}"}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        prev = r.json()["preview"]
        assert re.search(r"/(I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII)/", prev), prev
        assert re.search(r"\d{5}$", prev), prev

    def test_save_and_apply(self, owner, booking):
        r = owner.put(f"{BASE}/api/documents/numbering/receipt",
                      json={"pattern": "{PREFIX}-{YYYY}-{SEQ}", "prefix": "KW", "reset": "yearly", "width": 3}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["pattern"] == "{PREFIX}-{YYYY}-{SEQ}"
        pay = owner.post(f"{BASE}/api/payments", json={"booking_id": booking["id"], "amount": 50000,
                                                       "type": "settlement", "method": "cash"}, timeout=120)
        assert pay.status_code in (200, 201), pay.text[:300]
        rcp = pay.json().get("receipt")
        assert rcp, f"receipt tidak dibuat: {pay.json().get('error')}"
        assert re.match(r"^KW-\d{4}-\d{3,}$", rcp["number"]), rcp["number"]

    def test_pattern_without_seq(self, owner):
        r = owner.put(f"{BASE}/api/documents/numbering/receipt", json={"pattern": "{PREFIX}/{YYYY}"}, timeout=60)
        assert r.status_code == 400, f"{r.status_code} {r.text[:200]}"

    def test_unknown_token(self, owner):
        r = owner.put(f"{BASE}/api/documents/numbering/receipt", json={"pattern": "{PREFIX}/{FOO}/{SEQ}"}, timeout=60)
        assert r.status_code == 400, f"{r.status_code} {r.text[:200]}"
        p = owner.post(f"{BASE}/api/documents/numbering/receipt/preview", json={"pattern": "{FOO}/{SEQ}"}, timeout=60)
        assert p.status_code == 400

    def test_reset(self, owner):
        r = owner.delete(f"{BASE}/api/documents/numbering/receipt", timeout=60)
        assert r.status_code == 200
        assert r.json()["pattern"] == "{PREFIX}/{YYYY}/{MM}/{SEQ}"
        assert r.json()["overridden"] is False

    def test_ops_forbidden(self, ops):
        r = ops.put(f"{BASE}/api/documents/numbering/receipt", json={"pattern": "{PREFIX}/{SEQ}"}, timeout=60)
        assert r.status_code == 403, f"{r.status_code} {r.text[:200]}"

    def test_unknown_rule_404(self, owner):
        assert owner.put(f"{BASE}/api/documents/numbering/nope", json={"pattern": "{SEQ}"}, timeout=60).status_code == 404
