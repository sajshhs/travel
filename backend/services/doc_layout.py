"""services/doc_layout.py — konfigurasi tampilan & naskah dokumen (kop, footer, tanda tangan,
rekening bank, pajak, naskah per jenis dokumen, caption WhatsApp). Meniru sipro doc_layout.

Koleksi: `document_layouts` (satu per kode; `__default__` = identitas & gaya bawaan seluruh
dokumen, kode lain hanya menyimpan yang berbeda), `document_config` (rekening, pajak, WA),
`document_scripts` (naskah per kode dengan placeholder yang divalidasi).
"""
import logging
import re

from core_utils import new_id, now_iso

logger = logging.getLogger("travel_fleet.doc_layout")

DEFAULT_CODE = "__default__"
TARGETS = {
    DEFAULT_CODE: "Bawaan seluruh dokumen (identitas & gaya)",
    "INVOICE_DP": "Invoice DP (uang muka)",
    "INVOICE_SETTLEMENT": "Invoice Pelunasan",
    "INVOICE_FULL": "Invoice Penuh (tanpa DP)",
    "RECEIPT": "Kwitansi penerimaan pembayaran",
    "CONFIRMATION": "Konfirmasi pemesanan (untuk pelanggan)",
    "SPJ": "Surat Perintah Jalan (untuk driver)",
    "REFUND_NOTE": "Nota Refund (bukti pengembalian dana)",
}
INVOICE_CODE = {"dp": "INVOICE_DP", "settlement": "INVOICE_SETTLEMENT", "full": "INVOICE_FULL"}
KIND_LABEL = {"dp": "Invoice DP", "settlement": "Invoice Pelunasan", "full": "Invoice"}
KIND_DOC_TYPE = {"dp": "DP", "settlement": "PEL", "full": "FULL"}

SECTIONS = [
    ("identitas", "Data pelanggan & booking"), ("perjalanan", "Detail perjalanan"),
    ("rincian", "Rincian biaya"), ("pembayaran", "Ringkasan pembayaran"),
    ("rekening", "Rekening pembayaran"), ("ketentuan", "Syarat & ketentuan"),
]

COMMON_TOKENS = ["doc_number", "doc_date", "company_name", "customer_name", "customer_phone",
                 "booking_code", "vehicle_name", "driver_name", "origin", "destination",
                 "start_datetime", "end_datetime", "pax", "total_amount", "paid_amount",
                 "remaining_amount", "amount", "amount_words", "due_date", "issuer_name",
                 "cancellation_reason", "cancellation_fee", "refund_amount", "cancelled_date"]
TOKEN_LABELS = {
    "doc_number": "Nomor dokumen", "doc_date": "Tanggal dokumen", "company_name": "Nama perusahaan",
    "customer_name": "Nama pelanggan", "customer_phone": "Telepon pelanggan", "booking_code": "Kode booking",
    "vehicle_name": "Armada", "driver_name": "Nama driver", "origin": "Titik jemput / asal",
    "destination": "Tujuan", "start_datetime": "Jadwal mulai", "end_datetime": "Jadwal selesai",
    "pax": "Jumlah penumpang", "total_amount": "Total booking", "paid_amount": "Sudah dibayar",
    "remaining_amount": "Sisa tagihan", "amount": "Nominal dokumen ini", "amount_words": "Terbilang",
    "due_date": "Jatuh tempo", "issuer_name": "Nama penerbit",
    "cancellation_reason": "Alasan pembatalan", "cancellation_fee": "Denda pembatalan",
    "refund_amount": "Nominal refund", "cancelled_date": "Tanggal pembatalan",
}
TOKEN_SAMPLES = {
    "doc_number": "INV/DP/2026/06/0001", "doc_date": "15 Juni 2026", "company_name": "RahazaTrans",
    "customer_name": "PT Maju Jaya", "customer_phone": "0812-3456-7890", "booking_code": "BK-0001",
    "vehicle_name": "Hiace Premio 01", "driver_name": "Budi Santoso", "origin": "Bandung",
    "destination": "Gunung Bromo", "start_datetime": "20 Jun 2026 06:00", "end_datetime": "22 Jun 2026 20:00",
    "pax": "12", "total_amount": "Rp 3.500.000", "paid_amount": "Rp 1.000.000",
    "remaining_amount": "Rp 2.500.000", "amount": "Rp 1.050.000", "amount_words": "satu juta lima puluh ribu rupiah",
    "due_date": "18 Juni 2026", "issuer_name": "Admin Ops",
    "cancellation_reason": "Pelanggan mengundurkan jadwal", "cancellation_fee": "Rp 250.000",
    "refund_amount": "Rp 750.000", "cancelled_date": "16 Juni 2026",
}
TOKEN_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")

# Naskah bawaan per kode: intro (di atas rincian), closing (di bawah), terms (daftar S&K)
DEFAULT_SCRIPTS = {
    "INVOICE_DP": {
        "intro": "Kepada Yth. {{customer_name}}, berikut kami sampaikan tagihan uang muka (DP) untuk pemesanan {{booking_code}} — {{vehicle_name}} tujuan {{destination}} pada {{start_datetime}}.",
        "closing": "Mohon lakukan pembayaran sebelum {{due_date}} agar unit tetap terjaga untuk Anda. Terima kasih atas kepercayaannya kepada {{company_name}}.",
        "terms": "Pembayaran DP mengonfirmasi jadwal & unit armada.\nSisa pembayaran dilunasi paling lambat H-1 sebelum keberangkatan.\nPembatalan setelah DP mengikuti kebijakan pembatalan perusahaan.",
    },
    "INVOICE_SETTLEMENT": {
        "intro": "Kepada Yth. {{customer_name}}, berikut tagihan pelunasan untuk pemesanan {{booking_code}} — {{vehicle_name}} tujuan {{destination}} pada {{start_datetime}}.",
        "closing": "Sisa tagihan sebesar {{amount}} mohon dilunasi sebelum {{due_date}}. Terima kasih.",
        "terms": "Pelunasan wajib diterima sebelum keberangkatan.\nHarga sudah termasuk driver; BBM/tol/parkir sesuai kesepakatan.",
    },
    "INVOICE_FULL": {
        "intro": "Kepada Yth. {{customer_name}}, berikut tagihan pemesanan {{booking_code}} — {{vehicle_name}} tujuan {{destination}} pada {{start_datetime}}.",
        "closing": "Mohon lakukan pembayaran sebelum {{due_date}}. Terima kasih atas kepercayaannya kepada {{company_name}}.",
        "terms": "Pembayaran mengonfirmasi jadwal & unit armada.\nPembatalan mengikuti kebijakan pembatalan perusahaan.",
    },
    "RECEIPT": {
        "intro": "Telah diterima dari {{customer_name}} uang sejumlah {{amount}} ({{amount_words}}) untuk pembayaran pemesanan {{booking_code}} — {{vehicle_name}} tujuan {{destination}}.",
        "closing": "Sisa tagihan setelah pembayaran ini: {{remaining_amount}}.",
        "terms": "",
    },
    "CONFIRMATION": {
        "intro": "Terima kasih {{customer_name}}, pemesanan Anda dengan kode {{booking_code}} telah kami konfirmasi. Berikut detail perjalanan Anda.",
        "closing": "Driver akan menghubungi Anda sebelum keberangkatan. Hubungi kami bila ada perubahan jadwal.",
        "terms": "Harap siap di titik jemput 15 menit sebelum jadwal.\nBarang bawaan menjadi tanggung jawab penumpang.\nPerubahan rute di luar kesepakatan dapat dikenakan biaya tambahan.",
    },
    "SPJ": {
        "intro": "Kepada Sdr. {{driver_name}}, dengan ini ditugaskan untuk melaksanakan perjalanan pemesanan {{booking_code}} menggunakan unit {{vehicle_name}}.",
        "closing": "Laksanakan tugas dengan mengutamakan keselamatan. Catat odometer awal & akhir serta simpan seluruh bukti pengeluaran.",
        "terms": "Periksa kondisi kendaraan sebelum berangkat.\nPatuhi jam kerja & istirahat yang aman.\nLaporkan kendala di perjalanan kepada ops segera.",
    },
    DEFAULT_CODE: {"intro": "", "closing": "", "terms": ""},
    "REFUND_NOTE": {
        "intro": "Sehubungan dengan pembatalan pemesanan {{booking_code}} — {{vehicle_name}} tujuan {{destination}} pada {{start_datetime}} (alasan: {{cancellation_reason}}), {{company_name}} telah mengembalikan dana kepada {{customer_name}} sejumlah {{refund_amount}} ({{amount_words}}).",
        "closing": "Dengan diterbitkannya nota ini, kewajiban {{company_name}} atas pemesanan {{booking_code}} dinyatakan selesai. Terima kasih atas pengertian Anda.",
        "terms": "Denda pembatalan (bila ada) mengikuti kebijakan pembatalan yang disepakati saat pemesanan.\nDana dikembalikan ke rekening/metode pembayaran pelanggan dalam 1–3 hari kerja.",
    },
}


def _brand_default() -> dict:
    return {
        "company_name": "", "tagline": "Fleet & Travel Management", "address": "", "phone": "",
        "email": "", "website": "", "npwp": "", "logo_media_id": None, "logo_url": None,
        "header_mode": "system", "footer_mode": "system",
        "accent_color": "#0F6E56", "text_color": "#1C1C1E", "footer_text": "",
        "show_page_numbers": True, "paper": "A4", "margin_top_mm": 34, "margin_bottom_mm": 24,
        "margin_left_mm": 18, "margin_right_mm": 18, "watermark_text": "", "watermark_opacity": 8,
    }


def _table_default() -> dict:
    return {"grid": "horizontal", "show_header": True, "header_fill": True, "zebra": True,
            "total_highlight": True, "font_size": 9, "grid_color": "#E2E3E7"}


def default_layout(code: str = DEFAULT_CODE) -> dict:
    sigs = [{"title": "Hormat kami", "name": "", "position": "Admin", "auto_from_issuer": True}]
    if code == "SPJ":
        sigs = [{"title": "Dikeluarkan oleh", "name": "", "position": "Ops Admin", "auto_from_issuer": True},
                {"title": "Driver", "name": "", "position": "", "auto_from_issuer": False}]
    if code == "RECEIPT":
        sigs = [{"title": "Penerima", "name": "", "position": "Kasir / Admin", "auto_from_issuer": True}]
    if code == "REFUND_NOTE":
        sigs = [{"title": "Dikembalikan oleh", "name": "", "position": "Kasir / Admin", "auto_from_issuer": True},
                {"title": "Diterima oleh (pelanggan)", "name": "", "position": "", "auto_from_issuer": False}]
    return {
        "code": code, "brand": _brand_default(), "table": _table_default(),
        "sections": [{"key": k, "label": lbl, "visible": True, "order": i * 10} for i, (k, lbl) in enumerate(SECTIONS)],
        "signatures": sigs,
        "options": {"show_place_date": True, "place": "", "show_doc_number": True, "show_title": True,
                    "show_materai": False, "materai_note": "Bermeterai cukup", "show_generated_note": True,
                    "show_qr_note": False},
    }


def _merge(base: dict, over: dict) -> dict:
    out = {k: (dict(v) if isinstance(v, dict) else list(v) if isinstance(v, list) else v) for k, v in base.items()}
    for key, val in (over or {}).items():
        if key in ("brand", "options", "table") and isinstance(val, dict):
            out[key] = {**out.get(key, {}), **val}
        elif key in ("sections", "signatures") and isinstance(val, list) and val:
            out[key] = val
        elif key not in ("code", "id", "_id"):
            out[key] = val
    return out


async def _company_brand(db) -> dict:
    s = await db.settings.find_one({"key": "company_info"}, {"_id": 0}) or {}
    ci = s.get("value") or {}
    out = {}
    for src, dst in (("name", "company_name"), ("address", "address"), ("phone", "phone"), ("email", "email")):
        if ci.get(src):
            out[dst] = ci[src]
    return out


async def get_layout(db, code: str = DEFAULT_CODE) -> dict:
    """Layout efektif: bawaan → profil perusahaan (settings) → `__default__` → override kode."""
    base = default_layout(code)
    base["brand"].update(await _company_brand(db))
    org_doc = await db.document_layouts.find_one({"code": DEFAULT_CODE}, {"_id": 0})
    if org_doc:
        base = _merge(base, org_doc.get("layout") or {})
    if code != DEFAULT_CODE:
        own = await db.document_layouts.find_one({"code": code}, {"_id": 0})
        if own:
            base = _merge(base, own.get("layout") or {})
            base["overridden"] = True
    base["code"] = code
    base["label"] = TARGETS.get(code, code)
    return base


async def save_layout(db, code: str, layout: dict, actor: str) -> dict:
    ts = now_iso()
    cur = await db.document_layouts.find_one({"code": code}, {"_id": 0})
    doc = {"layout": layout, "updated_by": actor, "updated_at": ts, "version": int((cur or {}).get("version") or 0) + 1}
    if cur:
        await db.document_layouts.update_one({"code": code}, {"$set": doc})
    else:
        await db.document_layouts.insert_one({"id": new_id("dl"), "code": code, "created_at": ts, **doc})
    return await get_layout(db, code)


async def reset_layout(db, code: str) -> dict:
    await db.document_layouts.delete_one({"code": code})
    return await get_layout(db, code)


async def list_targets(db) -> list:
    rows = {d["code"]: d for d in await db.document_layouts.find({}, {"_id": 0, "code": 1, "version": 1, "updated_at": 1}).to_list(100)}
    scripts = {d["code"]: d for d in await db.document_scripts.find({}, {"_id": 0, "code": 1, "updated_at": 1}).to_list(100)}
    return [{"code": c, "label": lbl, "customized": c in rows, "script_customized": c in scripts,
             "version": (rows.get(c) or {}).get("version"), "updated_at": (rows.get(c) or {}).get("updated_at")}
            for c, lbl in TARGETS.items()]


def section_visible(layout: dict, key: str) -> bool:
    for s in layout.get("sections") or []:
        if s.get("key") == key:
            return bool(s.get("visible", True))
    return True


def signatures_for(layout: dict, *, issuer_name=None, issuer_position=None, second_name=None) -> list:
    out = []
    for i, s in enumerate(layout.get("signatures") or []):
        name, pos = s.get("name") or "", s.get("position") or ""
        if s.get("auto_from_issuer"):
            name = issuer_name or name
            pos = issuer_position or pos
        if i == 1 and second_name and not s.get("name"):
            name = second_name
        out.append({**s, "name": name, "position": pos})
    return out


async def logo_bytes(db, layout: dict):
    mid = (layout.get("brand") or {}).get("logo_media_id")
    if not mid:
        return None
    try:
        from services import media_lib as ml, media_store as ms
        doc = await ml.asset_or_404(db, mid)
        data, _ = ms.fetch(doc.get("storage_path") or "", backend=doc.get("storage_backend") or "")
        return data
    except Exception as exc:  # noqa: BLE001
        logger.warning("Logo dokumen tidak terbaca (%s) — dilewati.", exc)
        return None


# ------------------------------------------------------------------ konfigurasi keuangan dokumen
def default_config() -> dict:
    return {
        "tax_enabled": False, "tax_label": "PPN", "tax_percent": 11, "tax_inclusive": False,
        "dp_percent": 30, "due_days_dp": 2, "due_days_settlement": 3,
        "auto_receipt": True, "auto_invoice_status": True,
        "bank_accounts": [],
        "wa_caption_invoice": "Halo {{customer_name}}, berikut {{doc_title}} {{doc_number}} sebesar {{amount}} untuk pemesanan {{booking_code}}. Jatuh tempo {{due_date}}. Terima kasih 🙏",
        "wa_caption_receipt": "Halo {{customer_name}}, terima kasih. Pembayaran {{amount}} untuk pemesanan {{booking_code}} telah kami terima. Kwitansi {{doc_number}} terlampir. Sisa tagihan: {{remaining_amount}}.",
        "wa_caption_confirmation": "Halo {{customer_name}}, pemesanan {{booking_code}} telah dikonfirmasi. Detail perjalanan {{vehicle_name}} ke {{destination}} pada {{start_datetime}} terlampir. Terima kasih 🙏",
        "wa_caption_spj": "Halo {{driver_name}}, berikut Surat Perintah Jalan {{doc_number}} untuk pemesanan {{booking_code}} — {{vehicle_name}} ke {{destination}}, berangkat {{start_datetime}}. Hati-hati di jalan.",
        "wa_caption_refund": "Halo {{customer_name}}, pemesanan {{booking_code}} telah dibatalkan. Dana sebesar {{refund_amount}} telah kami kembalikan — Nota Refund {{doc_number}} terlampir. Terima kasih atas pengertiannya 🙏",
    }


async def get_config(db) -> dict:
    doc = await db.document_config.find_one({"id": "main"}, {"_id": 0}) or {}
    out = default_config()
    out.update({k: v for k, v in doc.items() if k in out})
    return out


async def save_config(db, patch: dict, actor: str) -> dict:
    allowed = default_config().keys()
    upd = {k: v for k, v in patch.items() if k in allowed}
    if "tax_percent" in upd and not (0 <= float(upd["tax_percent"] or 0) <= 100):
        raise ValueError("Persen pajak harus 0–100.")
    if "dp_percent" in upd and not (0 <= float(upd["dp_percent"] or 0) <= 100):
        raise ValueError("Persen DP harus 0–100.")
    for key in ("wa_caption_invoice", "wa_caption_receipt", "wa_caption_confirmation", "wa_caption_spj", "wa_caption_refund"):
        if key in upd:
            bad = unknown_tokens(upd[key], extra=("doc_title",))
            if bad:
                raise ValueError("Placeholder tidak dikenal di caption WA: " + ", ".join("{{" + t + "}}" for t in bad))
    upd.update({"updated_by": actor, "updated_at": now_iso()})
    await db.document_config.update_one({"id": "main"}, {"$set": upd}, upsert=True)
    return await get_config(db)


# ------------------------------------------------------------------ naskah
def placeholders() -> list:
    return [{"token": t, "label": TOKEN_LABELS[t], "sample": TOKEN_SAMPLES[t]} for t in COMMON_TOKENS]


def unknown_tokens(content: str, extra=()) -> list:
    known = set(COMMON_TOKENS) | set(extra)
    return sorted({t for t in TOKEN_RE.findall(content or "") if t not in known})


def render_text(content: str, ctx: dict) -> str:
    return TOKEN_RE.sub(lambda m: str(ctx.get(m.group(1), "-")), content or "")


async def get_script(db, code: str) -> dict:
    doc = await db.document_scripts.find_one({"code": code}, {"_id": 0}) or {}
    base = DEFAULT_SCRIPTS.get(code, DEFAULT_SCRIPTS[DEFAULT_CODE])
    return {"code": code, "label": TARGETS.get(code, code),
            "intro": doc.get("intro", base["intro"]), "closing": doc.get("closing", base["closing"]),
            "terms": doc.get("terms", base["terms"]), "default": base, "customized": bool(doc),
            "updated_at": doc.get("updated_at"), "placeholders": placeholders()}


async def save_script(db, code: str, patch: dict, actor: str) -> dict:
    upd = {k: patch[k] for k in ("intro", "closing", "terms") if k in patch and patch[k] is not None}
    bad = set()
    for v in upd.values():
        bad |= set(unknown_tokens(v))
    if bad:
        raise ValueError("Placeholder tidak dikenal: " + ", ".join("{{" + t + "}}" for t in sorted(bad))
                         + ". Pakai daftar placeholder yang tersedia.")
    upd.update({"updated_by": actor, "updated_at": now_iso()})
    await db.document_scripts.update_one({"code": code}, {"$set": upd, "$setOnInsert": {"id": new_id("ds"), "code": code}}, upsert=True)
    return await get_script(db, code)


async def reset_script(db, code: str) -> dict:
    await db.document_scripts.delete_one({"code": code})
    return await get_script(db, code)


def sample_context() -> dict:
    return dict(TOKEN_SAMPLES)
