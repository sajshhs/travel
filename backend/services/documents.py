"""services/documents.py — penerbit dokumen bisnis: Invoice (DP / Pelunasan / Penuh), Kwitansi,
Konfirmasi Pemesanan, Surat Perintah Jalan. Satu tempat untuk: hitung angka, nomor otomatis,
render PDF (pdf_engine), caption + kirim WhatsApp.

Koleksi: `invoices` (kanonik, dipertahankan), `receipts`, `booking_documents` (konfirmasi/SPJ).
"""
import base64
from datetime import datetime, timedelta, timezone

from core_utils import money, new_id, now_iso
from services import doc_layout as dl, doc_numbering as dn, pdf_engine as pe

BULAN = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus",
         "September", "Oktober", "November", "Desember"]
INVOICE_STATUS_LABEL = {"draft": "DRAFT", "sent": "TERKIRIM", "partial": "DIBAYAR SEBAGIAN", "paid": "LUNAS", "void": "DIBATALKAN"}


# ------------------------------------------------------------------ util format
def fdate(value) -> str:
    if not value:
        return "-"
    try:
        d = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return f"{d.day} {BULAN[d.month]} {d.year}"
    except ValueError:
        return str(value)[:10]


def fdatetime(value) -> str:
    if not value:
        return "-"
    try:
        d = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return f"{d.day} {BULAN[d.month][:3]} {d.year} {d.strftime('%H:%M')}"
    except ValueError:
        return str(value)[:16].replace("T", " ")


_SATUAN = ["", "satu", "dua", "tiga", "empat", "lima", "enam", "tujuh", "delapan", "sembilan", "sepuluh", "sebelas"]


def _terbilang(n: int) -> str:
    if n < 12:
        return _SATUAN[n]
    if n < 20:
        return _SATUAN[n - 10] + " belas"
    if n < 100:
        return _SATUAN[n // 10] + " puluh" + (" " + _terbilang(n % 10) if n % 10 else "")
    if n < 200:
        return "seratus" + (" " + _terbilang(n - 100) if n > 100 else "")
    if n < 1000:
        return _SATUAN[n // 100] + " ratus" + (" " + _terbilang(n % 100) if n % 100 else "")
    if n < 2000:
        return "seribu" + (" " + _terbilang(n - 1000) if n > 1000 else "")
    for div, nama in ((10 ** 12, "triliun"), (10 ** 9, "miliar"), (10 ** 6, "juta"), (1000, "ribu")):
        if n >= div:
            return _terbilang(n // div) + f" {nama}" + (" " + _terbilang(n % div) if n % div else "")
    return str(n)


def terbilang(value) -> str:
    n = money(value)
    if n == 0:
        return "nol rupiah"
    if n < 0:
        return "minus " + _terbilang(-n) + " rupiah"
    return _terbilang(n) + " rupiah"


def today_label() -> str:
    return fdate(now_iso())


# ------------------------------------------------------------------ konteks bersama
async def booking_context(db, booking: dict, user: dict = None) -> dict:
    cust = await db.customers.find_one({"id": booking.get("customer_id")}, {"_id": 0, "phone": 1, "name": 1}) or {}
    total = money(booking.get("total_amount"))
    paid = money(booking.get("paid_amount"))
    company = await db.settings.find_one({"key": "company_info"}, {"_id": 0}) or {}
    return {
        "company_name": (company.get("value") or {}).get("name") or "RahazaTrans",
        "customer_name": booking.get("customer_name") or cust.get("name") or "-",
        "customer_phone": booking.get("customer_phone") or cust.get("phone") or "-",
        "_phone": booking.get("customer_phone") or cust.get("phone") or "",
        "booking_code": booking.get("code") or "-",
        "vehicle_name": booking.get("vehicle_name") or "-",
        "driver_name": booking.get("driver_name") or "-",
        "origin": booking.get("origin") or booking.get("pickup_address") or "-",
        "destination": booking.get("destination") or booking.get("route_name") or "-",
        "start_datetime": fdatetime(booking.get("start_datetime")),
        "end_datetime": fdatetime(booking.get("end_datetime")),
        "pax": str(booking.get("pax") or "-"),
        "total_amount": pe.rp(total), "paid_amount": pe.rp(paid), "remaining_amount": pe.rp(max(total - paid, 0)),
        "doc_date": today_label(), "issuer_name": (user or {}).get("name") or "-",
    }


def booking_items(booking: dict) -> list:
    items = [{"label": f"Sewa armada {booking.get('vehicle_name') or ''}".strip()
              + (f" — {booking.get('origin')} → {booking.get('destination')}" if booking.get("destination") else ""),
              "qty": 1, "unit_price": money(booking.get("base_price") or booking.get("total_amount")),
              "amount": money(booking.get("base_price") or booking.get("total_amount"))}]
    for a in booking.get("add_ons") or []:
        items.append({"label": a.get("label") or "Tambahan", "qty": 1, "unit_price": money(a.get("amount")), "amount": money(a.get("amount"))})
    return items


# ------------------------------------------------------------------ INVOICE
async def build_invoice(db, booking: dict, body, user: dict) -> dict:
    """Bangun dokumen invoice dari booking. kind: dp | settlement | full."""
    cfg = await dl.get_config(db)
    kind = body.kind if body.kind in ("dp", "settlement", "full") else "full"
    items = [{"label": i.label, "qty": i.qty or 1, "unit_price": money(i.unit_price if i.unit_price is not None else i.amount),
              "amount": money(i.amount)} for i in (body.items or [])] or booking_items(booking)
    subtotal = sum(money(i["amount"]) for i in items)
    booking_total = money(booking.get("total_amount")) or subtotal
    tax_enabled = cfg["tax_enabled"] if body.tax_enabled is None else bool(body.tax_enabled)
    tax_percent = float(body.tax_percent if body.tax_percent is not None else cfg["tax_percent"])
    tax_amount = money(booking_total * tax_percent / 100) if tax_enabled else 0
    grand_total = booking_total + tax_amount
    paid_before = money(booking.get("paid_amount"))
    if kind == "dp":
        dp_percent = float(body.dp_percent if body.dp_percent is not None else (booking.get("dp_percent") or cfg["dp_percent"]))
        amount_due = money(body.amount) if body.amount else (money(booking.get("dp_amount")) or money(grand_total * dp_percent / 100))
        due_days = cfg["due_days_dp"]
    elif kind == "settlement":
        dp_percent = None
        amount_due = money(body.amount) if body.amount else max(grand_total - paid_before, 0)
        due_days = cfg["due_days_settlement"]
    else:
        dp_percent = None
        amount_due = money(body.amount) if body.amount else grand_total
        due_days = cfg["due_days_settlement"]
    if amount_due <= 0:
        raise ValueError("Nominal tagihan harus lebih dari 0 (booking mungkin sudah lunas).")
    number = await dn.generate(db, "invoice", {"booking_code": booking.get("code"), "customer_name": booking.get("customer_name"),
                                               "doc_type": dl.KIND_DOC_TYPE[kind]})
    ts = now_iso()
    due = body.due_at or (datetime.now(timezone.utc) + timedelta(days=int(due_days or 3))).isoformat()
    return {
        "id": new_id("inv"), "number": number, "kind": kind, "kind_label": dl.KIND_LABEL[kind],
        "booking_id": booking["id"], "booking_code": booking.get("code"),
        "customer_id": booking.get("customer_id"), "customer_name": booking.get("customer_name"),
        "items": items, "subtotal": subtotal, "booking_total": booking_total,
        "tax_enabled": tax_enabled, "tax_label": cfg["tax_label"], "tax_percent": tax_percent if tax_enabled else 0,
        "tax_amount": tax_amount, "grand_total": grand_total, "dp_percent": dp_percent,
        "paid_before": paid_before, "amount": amount_due, "amount_due": amount_due,
        "status": "draft", "issued_at": ts, "due_at": due, "notes": body.notes or "",
        "created_by": user.get("id"), "created_by_name": user.get("name"), "created_at": ts,
    }


async def invoice_context(db, inv: dict, booking: dict, user: dict = None) -> dict:
    ctx = await booking_context(db, booking, user)
    ctx.update({"doc_number": inv["number"], "doc_date": fdate(inv.get("issued_at")), "amount": pe.rp(inv["amount_due"]),
                "amount_words": terbilang(inv["amount_due"]), "due_date": fdate(inv.get("due_at")),
                "issuer_name": inv.get("created_by_name") or ctx["issuer_name"], "doc_title": inv.get("kind_label") or "Invoice"})
    return ctx


async def invoice_pdf(db, inv: dict, user: dict = None) -> bytes:
    booking = await db.bookings.find_one({"id": inv["booking_id"]}, {"_id": 0}) or {}
    code = dl.INVOICE_CODE.get(inv.get("kind"), "INVOICE_FULL")
    layout, script, cfg = await dl.get_layout(db, code), await dl.get_script(db, code), await dl.get_config(db)
    ctx = await invoice_context(db, inv, booking, user)
    meta = [("Ditagihkan kepada", ctx["customer_name"]), ("Booking", ctx["booking_code"]),
            ("Telepon", ctx["customer_phone"]), ("Jatuh tempo", ctx["due_date"])]
    if dl.section_visible(layout, "perjalanan"):
        meta += [("Armada", ctx["vehicle_name"]), ("Rute", f"{ctx['origin']} → {ctx['destination']}"),
                 ("Jadwal", f"{ctx['start_datetime']} s/d {ctx['end_datetime']}"), ("Penumpang", f"{ctx['pax']} pax" if ctx['pax'] != "-" else "-")]
    totals = [("Subtotal", inv["subtotal"], False)]
    if inv.get("tax_enabled"):
        totals.append((f"{inv.get('tax_label') or 'PPN'} {inv.get('tax_percent'):g}%", inv["tax_amount"], False))
    totals.append(("Total booking", inv["grand_total"], False))
    if inv["kind"] == "dp":
        totals.append((f"DP {inv.get('dp_percent'):g}%" if inv.get("dp_percent") else "Uang muka (DP)", inv["amount_due"], True))
    elif inv["kind"] == "settlement":
        totals += [("Sudah dibayar", -inv["paid_before"], False), ("Sisa yang ditagihkan", inv["amount_due"], True)]
    else:
        totals.append(("Total tagihan", inv["amount_due"], True))
    return pe.render_document(
        layout, await dl.logo_bytes(db, layout), title=inv.get("kind_label", "INVOICE").upper(), doc_number=inv["number"],
        doc_date=ctx["doc_date"], meta_pairs=meta if dl.section_visible(layout, "identitas") else [],
        intro=dl.render_text(script["intro"], ctx),
        items=inv["items"] if dl.section_visible(layout, "rincian") else None, totals=totals,
        banks=cfg["bank_accounts"] if dl.section_visible(layout, "rekening") else None,
        closing=dl.render_text(script["closing"], ctx),
        terms=script["terms"].split("\n") if dl.section_visible(layout, "ketentuan") and script["terms"] else None,
        signatures=dl.signatures_for(layout, issuer_name=ctx["issuer_name"]),
        status_label=INVOICE_STATUS_LABEL.get(inv.get("status")), big_amount=inv["amount_due"], big_label="Jumlah tagihan",
        note=inv.get("notes") or "")


# ------------------------------------------------------------------ KWITANSI
async def build_receipt(db, payment: dict, booking: dict, user: dict) -> dict:
    number = await dn.generate(db, "receipt", {"booking_code": booking.get("code"), "customer_name": booking.get("customer_name")})
    ts = now_iso()
    total = money(booking.get("total_amount"))
    paid = money(booking.get("paid_amount"))
    label = {"dp": "Pembayaran DP / uang muka", "settlement": "Pembayaran pelunasan"}.get(payment.get("type"), "Pembayaran")
    return {
        "id": new_id("rcp"), "number": number, "payment_id": payment["id"], "booking_id": booking["id"],
        "booking_code": booking.get("code"), "customer_id": booking.get("customer_id"),
        "customer_name": booking.get("customer_name"), "amount": money(payment.get("amount")),
        "amount_words": terbilang(payment.get("amount")), "method": payment.get("method"),
        "payment_type": payment.get("type"), "purpose": f"{label} pemesanan {booking.get('code')}",
        "total_amount": total, "paid_after": paid, "remaining_after": max(total - paid, 0),
        "paid_at": payment.get("paid_at"), "issued_at": ts, "created_by": user.get("id"),
        "created_by_name": user.get("name"), "created_at": ts,
    }


async def receipt_context(db, rcp: dict, booking: dict, user: dict = None) -> dict:
    ctx = await booking_context(db, booking, user)
    ctx.update({"doc_number": rcp["number"], "doc_date": fdate(rcp.get("issued_at")), "amount": pe.rp(rcp["amount"]),
                "amount_words": rcp.get("amount_words") or terbilang(rcp["amount"]), "due_date": "-",
                "paid_amount": pe.rp(rcp.get("paid_after")), "remaining_amount": pe.rp(rcp.get("remaining_after")),
                "issuer_name": rcp.get("created_by_name") or ctx["issuer_name"], "doc_title": "Kwitansi"})
    return ctx


async def receipt_pdf(db, rcp: dict, user: dict = None) -> bytes:
    booking = await db.bookings.find_one({"id": rcp["booking_id"]}, {"_id": 0}) or {}
    layout, script = await dl.get_layout(db, "RECEIPT"), await dl.get_script(db, "RECEIPT")
    ctx = await receipt_context(db, rcp, booking, user)
    method = {"transfer": "Transfer bank", "cash": "Tunai", "qris": "QRIS"}.get(rcp.get("method"), rcp.get("method") or "-")
    meta = [("Telah diterima dari", ctx["customer_name"]), ("Booking", ctx["booking_code"]),
            ("Untuk pembayaran", rcp.get("purpose") or "-"), ("Metode", method),
            ("Tanggal bayar", fdatetime(rcp.get("paid_at"))), ("Terbilang", ctx["amount_words"].capitalize())]
    summary = [("Total booking", rcp.get("total_amount")), ("Total dibayar s/d kwitansi ini", rcp.get("paid_after")),
               ("Sisa tagihan", rcp.get("remaining_after"))]
    return pe.render_document(
        layout, await dl.logo_bytes(db, layout), title="KWITANSI", doc_number=rcp["number"], doc_date=ctx["doc_date"],
        meta_pairs=meta, intro=dl.render_text(script["intro"], ctx),
        summary_pairs=summary if dl.section_visible(layout, "pembayaran") else None,
        closing=dl.render_text(script["closing"], ctx),
        terms=script["terms"].split("\n") if script["terms"] else None,
        signatures=dl.signatures_for(layout, issuer_name=ctx["issuer_name"]),
        status_label="LUNAS" if rcp.get("remaining_after", 1) <= 0 else None, big_amount=rcp["amount"], big_label="Jumlah diterima")


# ------------------------------------------------------------------ KONFIRMASI & SPJ (dokumen booking)
BOOKING_DOC_KINDS = {"confirmation": ("CONFIRMATION", "KONFIRMASI PEMESANAN", "Konfirmasi Pemesanan"),
                     "spj": ("SPJ", "SURAT PERINTAH JALAN", "Surat Perintah Jalan")}


async def ensure_booking_doc(db, booking: dict, kind: str, user: dict) -> dict:
    """Satu nomor per (booking, jenis) — dibuat saat pertama diminta, dipakai ulang berikutnya."""
    cur = await db.booking_documents.find_one({"booking_id": booking["id"], "kind": kind}, {"_id": 0})
    if cur:
        return cur
    veh = await db.vehicles.find_one({"id": booking.get("vehicle_id")}, {"_id": 0, "plate": 1, "plate_number": 1}) or {}
    number = await dn.generate(db, kind, {"booking_code": booking.get("code"), "customer_name": booking.get("customer_name"),
                                          "vehicle_code": veh.get("plate") or veh.get("plate_number") or ""})
    ts = now_iso()
    doc = {"id": new_id("bdoc"), "kind": kind, "number": number, "booking_id": booking["id"], "booking_code": booking.get("code"),
           "customer_name": booking.get("customer_name"), "issued_at": ts, "created_by": user.get("id"),
           "created_by_name": user.get("name"), "created_at": ts, "sent_count": 0}
    await db.booking_documents.insert_one(dict(doc))
    return doc


async def booking_doc_pdf(db, booking: dict, bdoc: dict, user: dict = None) -> bytes:
    code, title, _ = BOOKING_DOC_KINDS[bdoc["kind"]]
    layout, script = await dl.get_layout(db, code), await dl.get_script(db, code)
    ctx = await booking_context(db, booking, user)
    ctx.update({"doc_number": bdoc["number"], "doc_date": fdate(bdoc.get("issued_at")), "amount": ctx["total_amount"],
                "amount_words": terbilang(booking.get("total_amount")), "due_date": "-",
                "issuer_name": bdoc.get("created_by_name") or ctx["issuer_name"], "doc_title": title.title()})
    veh = await db.vehicles.find_one({"id": booking.get("vehicle_id")}, {"_id": 0}) or {}
    drv = await db.drivers.find_one({"id": booking.get("driver_id")}, {"_id": 0, "phone": 1, "name": 1}) or {}
    plate = veh.get("plate") or veh.get("plate_number") or ""
    if bdoc["kind"] == "spj":
        meta = [("Driver", ctx["driver_name"]), ("Telepon driver", drv.get("phone") or "-"),
                ("Armada", f"{ctx['vehicle_name']}" + (f" ({plate})" if plate else "")), ("Booking", ctx["booking_code"]),
                ("Pelanggan", ctx["customer_name"]), ("Telepon pelanggan", ctx["customer_phone"]),
                ("Titik jemput", ctx["origin"]), ("Tujuan", ctx["destination"]),
                ("Berangkat", ctx["start_datetime"]), ("Selesai", ctx["end_datetime"]), ("Penumpang", f"{ctx['pax']} pax" if ctx['pax'] != "-" else "-"),
                ("Catatan", booking.get("notes") or "-")]
        summary = None
        sigs = dl.signatures_for(layout, issuer_name=ctx["issuer_name"], second_name=ctx["driver_name"])
    else:
        meta = [("Pelanggan", ctx["customer_name"]), ("Telepon", ctx["customer_phone"]), ("Booking", ctx["booking_code"]),
                ("Status", (booking.get("status") or "-").upper()),
                ("Armada", f"{ctx['vehicle_name']}" + (f" ({plate})" if plate else "")), ("Driver", ctx["driver_name"]),
                ("Titik jemput", ctx["origin"]), ("Tujuan", ctx["destination"]),
                ("Mulai", ctx["start_datetime"]), ("Selesai", ctx["end_datetime"]), ("Penumpang", f"{ctx['pax']} pax" if ctx['pax'] != "-" else "-"),
                ("Catatan", booking.get("notes") or "-")]
        total, paid = money(booking.get("total_amount")), money(booking.get("paid_amount"))
        summary = [("Total biaya", total), ("Sudah dibayar", paid), ("Sisa tagihan", max(total - paid, 0))]
        sigs = dl.signatures_for(layout, issuer_name=ctx["issuer_name"])
    cfg = await dl.get_config(db)
    return pe.render_document(
        layout, await dl.logo_bytes(db, layout), title=title, doc_number=bdoc["number"], doc_date=ctx["doc_date"],
        meta_pairs=meta, intro=dl.render_text(script["intro"], ctx),
        items=booking_items(booking) if bdoc["kind"] == "confirmation" and dl.section_visible(layout, "rincian") else None,
        totals=[("Total", money(booking.get("total_amount")), True)] if bdoc["kind"] == "confirmation" else None,
        summary_pairs=summary if dl.section_visible(layout, "pembayaran") else None,
        banks=cfg["bank_accounts"] if bdoc["kind"] == "confirmation" and dl.section_visible(layout, "rekening") and summary and summary[2][1] > 0 else None,
        closing=dl.render_text(script["closing"], ctx),
        terms=script["terms"].split("\n") if dl.section_visible(layout, "ketentuan") and script["terms"] else None,
        signatures=sigs)


# ------------------------------------------------------------------ NOTA REFUND
async def build_refund_note(db, booking: dict, user: dict) -> dict:
    """Nota refund dari booking yang DIBATALKAN dengan refund_amount > 0 (payment type=refund)."""
    if booking.get("status") != "cancelled":
        raise ValueError("Nota refund hanya untuk booking yang dibatalkan.")
    refund = money(booking.get("refund_amount"))
    if refund <= 0:
        raise ValueError("Booking ini dibatalkan tanpa refund — tidak ada nota refund.")
    pay = await db.payments.find_one({"booking_id": booking["id"], "type": "refund"}, {"_id": 0})
    number = await dn.generate(db, "refund", {"booking_code": booking.get("code"), "customer_name": booking.get("customer_name")})
    ts = now_iso()
    paid_after = money(booking.get("paid_amount"))
    return {
        "id": new_id("rfn"), "number": number, "booking_id": booking["id"], "booking_code": booking.get("code"),
        "customer_id": booking.get("customer_id"), "customer_name": booking.get("customer_name"),
        "payment_id": (pay or {}).get("id"), "refund_amount": refund, "amount_words": terbilang(refund),
        "cancellation_fee": money(booking.get("cancellation_fee")), "received_total": paid_after + refund,
        "retained_total": paid_after, "total_amount": money(booking.get("total_amount")),
        "reason": booking.get("cancellation_reason") or "", "cancelled_at": booking.get("cancelled_at") or ts,
        "refunded_at": (pay or {}).get("paid_at") or ts, "issued_at": ts,
        "created_by": user.get("id"), "created_by_name": user.get("name"), "created_at": ts, "sent_count": 0,
    }


async def ensure_refund_note(db, booking: dict, user: dict) -> dict:
    cur = await db.refund_notes.find_one({"booking_id": booking["id"]}, {"_id": 0})
    if cur:
        return cur
    doc = await build_refund_note(db, booking, user)
    await db.refund_notes.insert_one(dict(doc))
    doc.pop("_id", None)
    return doc


async def refund_context(db, note: dict, booking: dict, user: dict = None) -> dict:
    ctx = await booking_context(db, booking, user)
    ctx.update({"doc_number": note["number"], "doc_date": fdate(note.get("issued_at")), "amount": pe.rp(note["refund_amount"]),
                "amount_words": note.get("amount_words") or terbilang(note["refund_amount"]), "due_date": "-",
                "refund_amount": pe.rp(note["refund_amount"]), "cancellation_fee": pe.rp(note.get("cancellation_fee")),
                "cancellation_reason": note.get("reason") or "-", "cancelled_date": fdate(note.get("cancelled_at")),
                "paid_amount": pe.rp(note.get("received_total")), "remaining_amount": pe.rp(0),
                "issuer_name": note.get("created_by_name") or ctx["issuer_name"], "doc_title": "Nota Refund"})
    return ctx


async def refund_note_pdf(db, note: dict, user: dict = None) -> bytes:
    booking = await db.bookings.find_one({"id": note["booking_id"]}, {"_id": 0}) or {}
    layout, script = await dl.get_layout(db, "REFUND_NOTE"), await dl.get_script(db, "REFUND_NOTE")
    ctx = await refund_context(db, note, booking, user)
    meta = [("Dikembalikan kepada", ctx["customer_name"]), ("Booking", ctx["booking_code"]),
            ("Telepon", ctx["customer_phone"]), ("Tanggal pembatalan", ctx["cancelled_date"]),
            ("Alasan pembatalan", ctx["cancellation_reason"]), ("Tanggal refund", fdatetime(note.get("refunded_at"))),
            ("Terbilang", ctx["amount_words"].capitalize()), ("Armada / rute", f"{ctx['vehicle_name']} · {ctx['origin']} → {ctx['destination']}")]
    summary = [("Total booking", note.get("total_amount")), ("Total dana diterima", note.get("received_total")),
               ("Denda pembatalan (ditahan)", note.get("cancellation_fee")), ("Dana dikembalikan (refund)", note.get("refund_amount"))]
    return pe.render_document(
        layout, await dl.logo_bytes(db, layout), title="NOTA REFUND", doc_number=note["number"], doc_date=ctx["doc_date"],
        meta_pairs=meta if dl.section_visible(layout, "identitas") else [], intro=dl.render_text(script["intro"], ctx),
        summary_pairs=summary if dl.section_visible(layout, "pembayaran") else None, closing=dl.render_text(script["closing"], ctx),
        terms=script["terms"].split("\n") if dl.section_visible(layout, "ketentuan") and script["terms"] else None,
        signatures=dl.signatures_for(layout, issuer_name=ctx["issuer_name"], second_name=ctx["customer_name"]),
        status_label="DIKEMBALIKAN", big_amount=note["refund_amount"], big_label="Jumlah dikembalikan")


async def on_booking_cancelled(db, booking_id: str, user: dict, *, send_wa=False) -> dict:
    """Setelah cancel dgn refund: terbitkan nota refund (+ WA opsional). Tidak pernah raise."""
    out = {"refund_note": None, "wa": None}
    try:
        booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0}) or {}
        if money(booking.get("refund_amount")) <= 0:
            return out
        note = await ensure_refund_note(db, booking, user)
        out["refund_note"] = note
        if send_wa:
            cfg = await dl.get_config(db)
            ctx = await refund_context(db, note, booking, user)
            try:
                res = await send_pdf_wa(db, phone=ctx["_phone"], pdf=await refund_note_pdf(db, note, user), filename=safe_filename(note["number"], "nota-refund"),
                                        caption=dl.render_text(cfg["wa_caption_refund"], ctx), user=user, source="refund_note",
                                        customer_id=note.get("customer_id"), contact_name=note.get("customer_name"))
                await db.refund_notes.update_one({"id": note["id"]}, {"$set": {"sent_at": now_iso()}, "$inc": {"sent_count": 1}})
                out["wa"] = {"status": res.get("status")}
            except ValueError as exc:
                out["wa"] = {"status": "failed", "error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        out["error"] = str(exc)[:160]
    return out


# ------------------------------------------------------------------ WhatsApp
async def send_pdf_wa(db, *, phone: str, pdf: bytes, filename: str, caption: str, user: dict, source: str,
                      customer_id=None, contact_name=None) -> dict:
    from services.whatsapp import send_wa
    if not (phone or "").strip():
        raise ValueError("Nomor WhatsApp tujuan tidak ditemukan")
    data_url = "data:application/pdf;base64," + base64.b64encode(pdf).decode()
    res = await send_wa(db, phone, text=caption, customer_id=customer_id, contact_name=contact_name, source=source,
                        author_id=user.get("id"), media_data=data_url, media_filename=filename)
    if res.get("status") == "skipped":
        raise ValueError("Kontak telah opt-out WhatsApp")
    if res.get("status") not in ("sent", "delivered", "read"):
        raise ValueError(res.get("error") or "Gagal mengirim via WhatsApp")
    return res


def safe_filename(number: str, fallback: str) -> str:
    return (number or fallback).replace("/", "-").replace(" ", "_") + ".pdf"


# ------------------------------------------------------------------ hook pembayaran
async def on_payment_recorded(db, booking: dict, payment: dict, user: dict, *, send_receipt_wa=False) -> dict:
    """Setelah pembayaran tercatat: sinkron status invoice + terbitkan kwitansi otomatis (+ WA opsional)."""
    cfg = await dl.get_config(db)
    out = {"receipt": None, "invoices_updated": 0, "wa": None}
    fresh = await db.bookings.find_one({"id": booking["id"]}, {"_id": 0}) or booking
    paid = money(fresh.get("paid_amount"))
    if cfg["auto_invoice_status"]:
        async for inv in db.invoices.find({"booking_id": booking["id"], "status": {"$in": ["draft", "sent", "partial"]}}, {"_id": 0}):
            covered = paid - money(inv.get("paid_before")) if inv.get("kind") == "settlement" else paid
            new_status = "paid" if covered >= money(inv.get("amount_due", inv.get("amount"))) else ("partial" if covered > 0 else None)
            if new_status and new_status != inv.get("status"):
                await db.invoices.update_one({"id": inv["id"]}, {"$set": {"status": new_status, "paid_at": now_iso() if new_status == "paid" else None}})
                out["invoices_updated"] += 1
    if cfg["auto_receipt"] or send_receipt_wa:
        rcp = await build_receipt(db, payment, fresh, user)
        await db.receipts.insert_one(dict(rcp))
        rcp.pop("_id", None)
        out["receipt"] = rcp
        if send_receipt_wa:
            try:
                ctx = await receipt_context(db, rcp, fresh, user)
                pdf = await receipt_pdf(db, rcp, user)
                res = await send_pdf_wa(db, phone=ctx["_phone"], pdf=pdf, filename=safe_filename(rcp["number"], "kwitansi"),
                                        caption=dl.render_text(cfg["wa_caption_receipt"], ctx), user=user, source="receipt",
                                        customer_id=rcp.get("customer_id"), contact_name=rcp.get("customer_name"))
                await db.receipts.update_one({"id": rcp["id"]}, {"$set": {"sent_at": now_iso()}, "$inc": {"sent_count": 1}})
                out["wa"] = {"status": res.get("status")}
            except ValueError as exc:
                out["wa"] = {"status": "failed", "error": str(exc)}
    return out
