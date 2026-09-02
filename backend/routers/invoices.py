"""routers/invoices.py — Invoice DP / Pelunasan / Penuh dari booking (mesin dokumen terkonfigurasi).

Koleksi kanonik: `invoices`. Endpoint lama dipertahankan (list/create/export/send-wa/patch/get)
dengan isi baru: jenis invoice, pajak on/off, nomor dari aturan penomoran, PDF berkop.
"""
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from core_utils import now_iso, safe_doc
from db import get_db
from dependencies import require_section
from schemas import InvoiceCreate, InvoiceStatusUpdate
from services import doc_layout as dl, documents as docs
from services.audit import record

router = APIRouter(prefix="/api", tags=["invoices"])
FIN = require_section("finance")
VALID_STATUS = {"draft", "sent", "partial", "paid", "void"}


async def _inv_or_404(db, invoice_id: str) -> dict:
    inv = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice tidak ditemukan")
    inv.setdefault("amount_due", inv.get("amount"))
    inv.setdefault("kind", "full")
    inv.setdefault("kind_label", dl.KIND_LABEL.get(inv.get("kind", "full"), "Invoice"))
    inv.setdefault("items", [{"label": f"Sewa armada — {inv.get('booking_code') or ''}", "qty": 1,
                              "unit_price": inv.get("amount"), "amount": inv.get("amount")}])
    inv.setdefault("subtotal", inv.get("amount"))
    inv.setdefault("grand_total", inv.get("amount"))
    inv.setdefault("paid_before", 0)
    return inv


@router.get("/invoices")
async def list_invoices(status: str = Query(default=None), booking_id: str = Query(default=None),
                        kind: str = Query(default=None), limit: int = Query(default=300, le=1000),
                        skip: int = Query(default=0, ge=0), user=Depends(FIN)):
    query = {}
    if status:
        query["status"] = status
    if booking_id:
        query["booking_id"] = booking_id
    if kind:
        query["kind"] = kind
    rows = await get_db().invoices.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).to_list(limit)
    return safe_doc(rows)


@router.post("/invoices")
async def create_invoice(body: InvoiceCreate, user=Depends(FIN)):
    db = get_db()
    booking = await db.bookings.find_one({"id": body.booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=400, detail="Booking tidak ditemukan")
    if booking.get("status") == "cancelled":
        raise HTTPException(status_code=400, detail="Booking dibatalkan — invoice tidak bisa diterbitkan")
    try:
        doc = await docs.build_invoice(db, booking, body, user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.invoices.insert_one(dict(doc))
    doc.pop("_id", None)
    await record(db, actor=user, action="create", entity_type="invoice", entity_id=doc["id"], after=doc,
                 summary=f"Terbitkan {doc['kind_label']} {doc['number']} (Rp {int(doc['amount_due']):,})".replace(",", "."))
    return safe_doc(doc)


@router.get("/invoices/{invoice_id}/export")
async def export_invoice(invoice_id: str, format: str = Query(default="pdf"), user=Depends(FIN)):
    db = get_db()
    inv = await _inv_or_404(db, invoice_id)
    number = inv.get("number", "invoice")
    if format == "excel":
        from services.exporter import invoice_xlsx
        data = invoice_xlsx(inv)
        return StreamingResponse(BytesIO(data), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                 headers={"Content-Disposition": f'attachment; filename="{docs.safe_filename(number, "invoice")[:-4]}.xlsx"'})
    pdf = await docs.invoice_pdf(db, inv, user)
    disposition = "inline" if format == "inline" else "attachment"
    return StreamingResponse(BytesIO(pdf), media_type="application/pdf",
                             headers={"Content-Disposition": f'{disposition}; filename="{docs.safe_filename(number, "invoice")}"'})


async def _send_invoice_wa(db, inv, user):
    booking = await db.bookings.find_one({"id": inv.get("booking_id")}, {"_id": 0}) or {}
    cfg = await dl.get_config(db)
    ctx = await docs.invoice_context(db, inv, booking, user)
    pdf = await docs.invoice_pdf(db, inv, user)
    try:
        res = await docs.send_pdf_wa(db, phone=ctx["_phone"], pdf=pdf, filename=docs.safe_filename(inv.get("number"), "invoice"),
                                     caption=dl.render_text(cfg["wa_caption_invoice"], ctx), user=user, source="invoice",
                                     customer_id=inv.get("customer_id"), contact_name=inv.get("customer_name"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    upd = {"$set": {"sent_at": now_iso()}, "$inc": {"sent_count": 1}}
    if inv.get("status") == "draft":
        upd["$set"]["status"] = "sent"
    await db.invoices.update_one({"id": inv["id"]}, upd)
    await record(db, actor=user, action="send", entity_type="invoice", entity_id=inv["id"],
                 summary=f"Kirim {inv.get('kind_label', 'invoice')} {inv.get('number')} via WhatsApp ke {ctx['_phone']}")
    return {"ok": True, "number": inv.get("number"), **res}


@router.post("/invoices/{invoice_id}/send-wa")
async def send_invoice_wa(invoice_id: str, user=Depends(FIN)):
    db = get_db()
    return await _send_invoice_wa(db, await _inv_or_404(db, invoice_id), user)


@router.post("/bookings/{booking_id}/send-invoice-wa")
async def send_booking_invoice_wa(booking_id: str, user=Depends(FIN)):
    """Kirim invoice TERBARU yang belum lunas milik booking via WhatsApp (tombol di halaman Booking)."""
    db = get_db()
    inv = await db.invoices.find_one({"booking_id": booking_id, "status": {"$nin": ["paid", "void"]}}, {"_id": 0}, sort=[("created_at", -1)])
    if not inv:
        inv = await db.invoices.find_one({"booking_id": booking_id}, {"_id": 0}, sort=[("created_at", -1)])
    if not inv:
        raise HTTPException(status_code=404, detail="Belum ada invoice untuk booking ini — buat dulu lewat tombol Dokumen")
    return await _send_invoice_wa(db, await _inv_or_404(db, inv["id"]), user)


@router.patch("/invoices/{invoice_id}")
async def update_invoice_status(invoice_id: str, body: InvoiceStatusUpdate, user=Depends(FIN)):
    if body.status not in VALID_STATUS:
        raise HTTPException(status_code=400, detail="Status invoice tidak sah")
    db = get_db()
    res = await db.invoices.update_one({"id": invoice_id}, {"$set": {"status": body.status}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Invoice tidak ditemukan")
    inv = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
    await record(db, actor=user, action="update", entity_type="invoice", entity_id=invoice_id, after={"status": body.status},
                 summary=f"Ubah status invoice {inv.get('number')} → {body.status}")
    return safe_doc(inv)


@router.get("/invoices/{invoice_id}")
async def get_invoice(invoice_id: str, user=Depends(FIN)):
    return safe_doc(await _inv_or_404(get_db(), invoice_id))
