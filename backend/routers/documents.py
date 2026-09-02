"""routers/documents.py — pusat dokumen bisnis: kwitansi, dokumen booking (konfirmasi/SPJ),
konfigurasi tampilan (kop/ttd), naskah, rekening & pajak, aturan penomoran, pratinjau PDF.

Baca = section 'finance' (owner/ops_admin). Ubah konfigurasi = section 'settings' (owner).
"""
from io import BytesIO
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from core_utils import money, now_iso, safe_doc
from db import get_db
from dependencies import require_section
from services import doc_layout as dl, doc_numbering as dn, documents as docs, pdf_engine as pe
from services.audit import record

router = APIRouter(prefix="/api/documents", tags=["documents"])
FIN = require_section("finance")
SET = require_section("settings")


class LayoutSave(BaseModel):
    brand: Optional[dict] = None
    table: Optional[dict] = None
    sections: Optional[List[dict]] = None
    signatures: Optional[List[dict]] = None
    options: Optional[dict] = None


class ScriptSave(BaseModel):
    intro: Optional[str] = Field(default=None, max_length=4000)
    closing: Optional[str] = Field(default=None, max_length=4000)
    terms: Optional[str] = Field(default=None, max_length=6000)


class ConfigSave(BaseModel):
    tax_enabled: Optional[bool] = None
    tax_label: Optional[str] = Field(default=None, max_length=40)
    tax_percent: Optional[float] = None
    dp_percent: Optional[float] = None
    due_days_dp: Optional[int] = Field(default=None, ge=0, le=90)
    due_days_settlement: Optional[int] = Field(default=None, ge=0, le=90)
    auto_receipt: Optional[bool] = None
    auto_invoice_status: Optional[bool] = None
    bank_accounts: Optional[List[dict]] = None
    wa_caption_invoice: Optional[str] = Field(default=None, max_length=1500)
    wa_caption_receipt: Optional[str] = Field(default=None, max_length=1500)
    wa_caption_confirmation: Optional[str] = Field(default=None, max_length=1500)
    wa_caption_spj: Optional[str] = Field(default=None, max_length=1500)
    wa_caption_refund: Optional[str] = Field(default=None, max_length=1500)


class RuleSave(BaseModel):
    pattern: Optional[str] = None
    prefix: Optional[str] = None
    width: Optional[int] = Field(default=None, ge=1, le=8)
    reset: Optional[str] = None
    start: Optional[int] = Field(default=None, ge=1)


class ReceiptCreate(BaseModel):
    payment_id: str = Field(min_length=1)


def _pdf_response(pdf: bytes, filename: str, inline: bool):
    return StreamingResponse(BytesIO(pdf), media_type="application/pdf",
                             headers={"Content-Disposition": f'{"inline" if inline else "attachment"}; filename="{filename}"'})


def _code_or_404(code: str) -> str:
    if code not in dl.TARGETS:
        raise HTTPException(status_code=404, detail=f"Jenis dokumen '{code}' tidak dikenal")
    return code


# ------------------------------------------------------------------ ringkasan per booking
@router.get("/booking/{booking_id}")
async def booking_documents(booking_id: str, user=Depends(FIN)):
    db = get_db()
    booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking tidak ditemukan")
    cfg = await dl.get_config(db)
    total = money(booking.get("total_amount"))
    tax = money(total * float(cfg["tax_percent"]) / 100) if cfg["tax_enabled"] else 0
    return {
        "booking": safe_doc(booking),
        "invoices": safe_doc(await db.invoices.find({"booking_id": booking_id}, {"_id": 0}).sort("created_at", -1).to_list(50)),
        "receipts": safe_doc(await db.receipts.find({"booking_id": booking_id}, {"_id": 0}).sort("created_at", -1).to_list(50)),
        "refund_note": safe_doc(await db.refund_notes.find_one({"booking_id": booking_id}, {"_id": 0})),
        "payments": safe_doc(await db.payments.find({"booking_id": booking_id}, {"_id": 0}).sort("paid_at", -1).to_list(50)),
        "booking_docs": safe_doc(await db.booking_documents.find({"booking_id": booking_id}, {"_id": 0}).to_list(10)),
        "suggest": {"dp_percent": booking.get("dp_percent") or cfg["dp_percent"],
                    "dp_amount": money(booking.get("dp_amount")) or money((total + tax) * float(booking.get("dp_percent") or cfg["dp_percent"]) / 100),
                    "remaining": max(total + tax - money(booking.get("paid_amount")), 0),
                    "tax_enabled": cfg["tax_enabled"], "tax_percent": cfg["tax_percent"], "tax_label": cfg["tax_label"]},
    }


# ------------------------------------------------------------------ kwitansi
@router.get("/receipts")
async def list_receipts(booking_id: str = Query(default=None), limit: int = Query(default=300, le=1000), user=Depends(FIN)):
    q = {"booking_id": booking_id} if booking_id else {}
    return safe_doc(await get_db().receipts.find(q, {"_id": 0}).sort("created_at", -1).to_list(limit))


@router.post("/receipts")
async def create_receipt(body: ReceiptCreate, user=Depends(FIN)):
    db = get_db()
    pay = await db.payments.find_one({"id": body.payment_id}, {"_id": 0})
    if not pay:
        raise HTTPException(status_code=404, detail="Pembayaran tidak ditemukan")
    if pay.get("type") == "refund" or money(pay.get("amount")) <= 0:
        raise HTTPException(status_code=400, detail="Kwitansi hanya untuk penerimaan dana — refund memakai Nota Refund")
    exists = await db.receipts.find_one({"payment_id": pay["id"]}, {"_id": 0})
    if exists:
        return safe_doc(exists)
    booking = await db.bookings.find_one({"id": pay["booking_id"]}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking tidak ditemukan")
    rcp = await docs.build_receipt(db, pay, booking, user)
    await db.receipts.insert_one(dict(rcp))
    rcp.pop("_id", None)
    await record(db, actor=user, action="create", entity_type="receipt", entity_id=rcp["id"],
                 summary=f"Terbitkan kwitansi {rcp['number']} (Rp {int(rcp['amount']):,})".replace(",", "."))
    return safe_doc(rcp)


async def _rcp_or_404(db, rid):
    rcp = await db.receipts.find_one({"id": rid}, {"_id": 0})
    if not rcp:
        raise HTTPException(status_code=404, detail="Kwitansi tidak ditemukan")
    return rcp


@router.get("/receipts/{receipt_id}/pdf")
async def receipt_pdf(receipt_id: str, inline: bool = Query(default=False), user=Depends(FIN)):
    db = get_db()
    rcp = await _rcp_or_404(db, receipt_id)
    return _pdf_response(await docs.receipt_pdf(db, rcp, user), docs.safe_filename(rcp["number"], "kwitansi"), inline)


@router.post("/receipts/{receipt_id}/send-wa")
async def receipt_send_wa(receipt_id: str, user=Depends(FIN)):
    db = get_db()
    rcp = await _rcp_or_404(db, receipt_id)
    booking = await db.bookings.find_one({"id": rcp["booking_id"]}, {"_id": 0}) or {}
    cfg = await dl.get_config(db)
    ctx = await docs.receipt_context(db, rcp, booking, user)
    try:
        res = await docs.send_pdf_wa(db, phone=ctx["_phone"], pdf=await docs.receipt_pdf(db, rcp, user),
                                     filename=docs.safe_filename(rcp["number"], "kwitansi"),
                                     caption=dl.render_text(cfg["wa_caption_receipt"], ctx), user=user, source="receipt",
                                     customer_id=rcp.get("customer_id"), contact_name=rcp.get("customer_name"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.receipts.update_one({"id": rcp["id"]}, {"$set": {"sent_at": now_iso()}, "$inc": {"sent_count": 1}})
    await record(db, actor=user, action="send", entity_type="receipt", entity_id=rcp["id"],
                 summary=f"Kirim kwitansi {rcp['number']} via WhatsApp ke {ctx['_phone']}")
    return {"ok": True, "number": rcp["number"], **res}


# ------------------------------------------------------------------ nota refund
class RefundNoteCreate(BaseModel):
    booking_id: str = Field(min_length=1)


@router.get("/refund-notes")
async def list_refund_notes(booking_id: str = Query(default=None), limit: int = Query(default=300, le=1000), user=Depends(FIN)):
    q = {"booking_id": booking_id} if booking_id else {}
    return safe_doc(await get_db().refund_notes.find(q, {"_id": 0}).sort("created_at", -1).to_list(limit))


@router.post("/refund-notes")
async def create_refund_note(body: RefundNoteCreate, user=Depends(FIN)):
    db = get_db()
    booking = await db.bookings.find_one({"id": body.booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking tidak ditemukan")
    try:
        note = await docs.ensure_refund_note(db, booking, user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await record(db, actor=user, action="create", entity_type="refund_note", entity_id=note["id"],
                 summary=f"Terbitkan nota refund {note['number']} (Rp {int(note['refund_amount']):,})".replace(",", "."))
    return safe_doc(note)


async def _note_or_404(db, nid):
    note = await db.refund_notes.find_one({"id": nid}, {"_id": 0})
    if not note:
        raise HTTPException(status_code=404, detail="Nota refund tidak ditemukan")
    return note


@router.get("/refund-notes/{note_id}/pdf")
async def refund_note_pdf(note_id: str, inline: bool = Query(default=False), user=Depends(FIN)):
    db = get_db()
    note = await _note_or_404(db, note_id)
    return _pdf_response(await docs.refund_note_pdf(db, note, user), docs.safe_filename(note["number"], "nota-refund"), inline)


@router.post("/refund-notes/{note_id}/send-wa")
async def refund_note_send_wa(note_id: str, user=Depends(FIN)):
    db = get_db()
    note = await _note_or_404(db, note_id)
    booking = await db.bookings.find_one({"id": note["booking_id"]}, {"_id": 0}) or {}
    cfg = await dl.get_config(db)
    ctx = await docs.refund_context(db, note, booking, user)
    try:
        res = await docs.send_pdf_wa(db, phone=ctx["_phone"], pdf=await docs.refund_note_pdf(db, note, user),
                                     filename=docs.safe_filename(note["number"], "nota-refund"),
                                     caption=dl.render_text(cfg["wa_caption_refund"], ctx), user=user, source="refund_note",
                                     customer_id=note.get("customer_id"), contact_name=note.get("customer_name"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.refund_notes.update_one({"id": note["id"]}, {"$set": {"sent_at": now_iso()}, "$inc": {"sent_count": 1}})
    await record(db, actor=user, action="send", entity_type="refund_note", entity_id=note["id"],
                 summary=f"Kirim nota refund {note['number']} via WhatsApp ke {ctx['_phone']}")
    return {"ok": True, "number": note["number"], **res}


# ------------------------------------------------------------------ dokumen booking (konfirmasi / SPJ)
async def _booking_and_doc(db, booking_id: str, kind: str, user):
    if kind not in docs.BOOKING_DOC_KINDS:
        raise HTTPException(status_code=404, detail="Jenis dokumen booking tidak dikenal")
    booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking tidak ditemukan")
    return booking, await docs.ensure_booking_doc(db, booking, kind, user)


@router.get("/booking/{booking_id}/{kind}/pdf")
async def booking_doc_pdf(booking_id: str, kind: str, inline: bool = Query(default=False), user=Depends(FIN)):
    db = get_db()
    booking, bdoc = await _booking_and_doc(db, booking_id, kind, user)
    return _pdf_response(await docs.booking_doc_pdf(db, booking, bdoc, user), docs.safe_filename(bdoc["number"], kind), inline)


@router.post("/booking/{booking_id}/{kind}/send-wa")
async def booking_doc_send_wa(booking_id: str, kind: str, user=Depends(FIN)):
    db = get_db()
    booking, bdoc = await _booking_and_doc(db, booking_id, kind, user)
    cfg = await dl.get_config(db)
    ctx = await docs.booking_context(db, booking, user)
    ctx.update({"doc_number": bdoc["number"], "doc_title": docs.BOOKING_DOC_KINDS[kind][2]})
    if kind == "spj":
        drv = await db.drivers.find_one({"id": booking.get("driver_id")}, {"_id": 0, "phone": 1, "name": 1}) or {}
        phone, name, caption = drv.get("phone") or "", drv.get("name") or booking.get("driver_name"), cfg["wa_caption_spj"]
        if not phone:
            raise HTTPException(status_code=400, detail="Booking belum punya driver dengan nomor WhatsApp")
    else:
        phone, name, caption = ctx["_phone"], booking.get("customer_name"), cfg["wa_caption_confirmation"]
    try:
        res = await docs.send_pdf_wa(db, phone=phone, pdf=await docs.booking_doc_pdf(db, booking, bdoc, user),
                                     filename=docs.safe_filename(bdoc["number"], kind), caption=dl.render_text(caption, ctx),
                                     user=user, source=kind, customer_id=None if kind == "spj" else booking.get("customer_id"),
                                     contact_name=name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.booking_documents.update_one({"id": bdoc["id"]}, {"$set": {"sent_at": now_iso()}, "$inc": {"sent_count": 1}})
    await record(db, actor=user, action="send", entity_type="booking_document", entity_id=bdoc["id"],
                 summary=f"Kirim {docs.BOOKING_DOC_KINDS[kind][2]} {bdoc['number']} via WhatsApp ke {phone}")
    return {"ok": True, "number": bdoc["number"], **res}


# ------------------------------------------------------------------ konfigurasi keuangan dokumen
@router.get("/config")
async def get_config(user=Depends(FIN)):
    return await dl.get_config(get_db())


@router.patch("/config")
async def patch_config(body: ConfigSave, user=Depends(SET)):
    db = get_db()
    try:
        out = await dl.save_config(db, body.model_dump(exclude_none=True), user.get("id"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await record(db, actor=user, action="update", entity_type="document_config", entity_id="main", summary="Ubah konfigurasi dokumen (pajak/rekening/WA)")
    return out


# ------------------------------------------------------------------ layout (kop, ttd, opsi)
@router.get("/layouts")
async def list_layouts(user=Depends(FIN)):
    return {"data": await dl.list_targets(get_db()), "sections_catalog": [{"key": k, "label": v} for k, v in dl.SECTIONS]}


@router.get("/layouts/{code}")
async def get_layout(code: str, user=Depends(FIN)):
    return safe_doc(await dl.get_layout(get_db(), _code_or_404(code)))


@router.put("/layouts/{code}")
async def save_layout(code: str, body: LayoutSave, user=Depends(SET)):
    db = get_db()
    out = await dl.save_layout(db, _code_or_404(code), body.model_dump(exclude_none=True), user.get("id"))
    await record(db, actor=user, action="update", entity_type="document_layout", entity_id=code, summary=f"Ubah tampilan dokumen {code}")
    return safe_doc(out)


@router.delete("/layouts/{code}")
async def reset_layout(code: str, user=Depends(SET)):
    return safe_doc(await dl.reset_layout(get_db(), _code_or_404(code)))


@router.get("/layouts/{code}/script")
async def get_script(code: str, user=Depends(FIN)):
    return await dl.get_script(get_db(), _code_or_404(code))


@router.put("/layouts/{code}/script")
async def save_script(code: str, body: ScriptSave, user=Depends(SET)):
    try:
        return await dl.save_script(get_db(), _code_or_404(code), body.model_dump(exclude_none=True), user.get("id"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/layouts/{code}/script")
async def reset_script(code: str, user=Depends(SET)):
    return await dl.reset_script(get_db(), _code_or_404(code))


class PreviewIn(LayoutSave):
    script: Optional[dict] = None


@router.post("/layouts/{code}/preview")
async def preview_layout(code: str, body: PreviewIn, user=Depends(FIN)):
    """PDF pratinjau dari rancangan yang BELUM disimpan — mesin cetak yang sama dengan dokumen nyata."""
    db = get_db()
    _code_or_404(code)
    patch = body.model_dump(exclude_none=True)
    script_draft = patch.pop("script", None) or {}
    layout = dl._merge(await dl.get_layout(db, code), patch)
    script = {**(await dl.get_script(db, code)), **{k: v for k, v in script_draft.items() if v is not None}}
    cfg = await dl.get_config(db)
    ctx = dl.sample_context()
    ctx["company_name"] = layout["brand"].get("company_name") or ctx["company_name"]
    ctx["issuer_name"] = user.get("name") or ctx["issuer_name"]
    items = [{"label": "Sewa armada Hiace Premio 01 — Bandung → Gunung Bromo (3 hari)", "qty": 1, "unit_price": 3000000, "amount": 3000000},
             {"label": "Overtime", "qty": 1, "unit_price": 500000, "amount": 500000}]
    title = {"RECEIPT": "KWITANSI", "CONFIRMATION": "KONFIRMASI PEMESANAN", "SPJ": "SURAT PERINTAH JALAN", "REFUND_NOTE": "NOTA REFUND",
             "INVOICE_DP": "INVOICE DP", "INVOICE_SETTLEMENT": "INVOICE PELUNASAN"}.get(code, "INVOICE")
    meta = [("Pelanggan", ctx["customer_name"]), ("Booking", ctx["booking_code"]), ("Telepon", ctx["customer_phone"]),
            ("Armada", ctx["vehicle_name"]), ("Rute", f"{ctx['origin']} → {ctx['destination']}"), ("Jadwal", f"{ctx['start_datetime']} s/d {ctx['end_datetime']}")]
    tax = money(3500000 * float(cfg["tax_percent"]) / 100) if cfg["tax_enabled"] else 0
    totals = [("Subtotal", 3500000, False)] + ([(f"{cfg['tax_label']} {cfg['tax_percent']:g}%", tax, False)] if tax else []) + [("Total tagihan", 3500000 + tax, True)]
    is_invoice = code.startswith("INVOICE") or code == dl.DEFAULT_CODE
    pdf = pe.render_document(
        layout, await dl.logo_bytes(db, layout), title=title, doc_number=ctx["doc_number"], doc_date=ctx["doc_date"],
        meta_pairs=meta if dl.section_visible(layout, "identitas") else [], intro=dl.render_text(script.get("intro"), ctx),
        items=items if (is_invoice or code == "CONFIRMATION") and dl.section_visible(layout, "rincian") else None, totals=totals,
        summary_pairs=([("Total booking", 3500000), ("Total dana diterima", 1000000), ("Denda pembatalan (ditahan)", 250000), ("Dana dikembalikan (refund)", 750000)] if code == "REFUND_NOTE"
                       else [("Total booking", 3500000), ("Sudah dibayar", 1000000), ("Sisa tagihan", 2500000)]) if code in ("RECEIPT", "CONFIRMATION", "REFUND_NOTE") and dl.section_visible(layout, "pembayaran") else None,
        banks=cfg["bank_accounts"] if dl.section_visible(layout, "rekening") and code not in ("SPJ", "REFUND_NOTE") else None,
        closing=dl.render_text(script.get("closing"), ctx),
        terms=(script.get("terms") or "").split("\n") if dl.section_visible(layout, "ketentuan") and script.get("terms") else None,
        signatures=dl.signatures_for(layout, issuer_name=ctx["issuer_name"], second_name=ctx["driver_name"]),
        status_label="PRATINJAU", big_amount=1050000 if is_invoice or code in ("RECEIPT", "REFUND_NOTE") else None,
        big_label="Jumlah dikembalikan" if code == "REFUND_NOTE" else "Jumlah tagihan",
        note="PRATINJAU dengan data contoh — bukan dokumen sah.")
    return _pdf_response(pdf, f"pratinjau-{code}.pdf", True)


# ------------------------------------------------------------------ penomoran
@router.get("/numbering")
async def list_numbering(user=Depends(FIN)):
    return {"data": await dn.list_rules(get_db()),
            "reset_options": [{"value": k, "label": v} for k, v in dn.RESET_OPTIONS.items()],
            "global_tokens": [{"token": t, "desc": d, "example": ex} for t, d, ex in dn.GLOBAL_TOKENS],
            "context_tokens": [{"token": t, "desc": d, "example": ex} for t, (d, ex) in dn.CONTEXT_TOKENS.items()]}


def _rule_key(key: str) -> str:
    if key not in dn.REGISTRY_BY_KEY:
        raise HTTPException(status_code=404, detail="Aturan penomoran tidak dikenal")
    return key


@router.post("/numbering/{key}/preview")
async def preview_numbering(key: str, body: RuleSave, user=Depends(FIN)):
    db = get_db()
    rule = await dn.effective_rule(db, _rule_key(key))
    rule.update({k: v for k, v in body.model_dump(exclude_none=True).items() if k in dn.EDITABLE})
    errs = dn.validate_pattern(rule["pattern"], dn.REGISTRY_BY_KEY[key]["tokens"])
    if errs:
        raise HTTPException(status_code=400, detail=" ".join(errs))
    return {"preview": await dn.preview(db, rule)}


@router.put("/numbering/{key}")
async def save_numbering(key: str, body: RuleSave, user=Depends(SET)):
    db = get_db()
    try:
        out = await dn.save_rule(db, _rule_key(key), body.model_dump(exclude_none=True), user.get("id"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    out["preview"] = await dn.preview(db, out)
    await record(db, actor=user, action="update", entity_type="numbering_rule", entity_id=key, summary=f"Ubah pola nomor {key}: {out['pattern']}")
    return out


@router.delete("/numbering/{key}")
async def reset_numbering(key: str, user=Depends(SET)):
    db = get_db()
    out = await dn.reset_rule(db, _rule_key(key))
    out["preview"] = await dn.preview(db, out)
    return out
