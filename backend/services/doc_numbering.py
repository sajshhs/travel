"""services/doc_numbering.py — penomoran dokumen terkonfigurasi (pola + token), meniru sipro.

Aturan per kunci disimpan di `numbering_rules` (override atas REGISTRY). Counter atomik via
services.counters.next_seq dengan scope `docnum:<key>[:<periode>]` sesuai kebijakan reset.
Nomor yang sudah terbit tidak pernah berubah — aturan hanya untuk nomor berikutnya.
"""
import re
from datetime import datetime, timezone

from core_utils import now_iso
from services.counters import next_seq

ROMAN = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]
_TOKEN_RE = re.compile(r"\{([A-Z_]+)(?::(\d+))?\}")

GLOBAL_TOKENS = [
    ("PREFIX", "Awalan aturan (kolom Awalan)", "INV"),
    ("SEQ", "Nomor urut; {SEQ:6} memaksa 6 digit", "0001"),
    ("YYYY", "Tahun 4 digit", "2026"),
    ("YY", "Tahun 2 digit", "26"),
    ("MM", "Bulan 2 digit", "06"),
    ("MM_ROMAN", "Bulan romawi", "VI"),
    ("DD", "Tanggal 2 digit", "15"),
    ("ORG_INITIALS", "Inisial nama perusahaan", "RT"),
]
CONTEXT_TOKENS = {
    "BOOKING_CODE": ("Kode booking", "BK-0001"),
    "CUSTOMER_INITIALS": ("Inisial nama pelanggan", "MJ"),
    "DOC_TYPE": ("Jenis invoice (DP / PEL / FULL)", "DP"),
    "VEHICLE_CODE": ("Kode/plat armada", "B1234XX"),
}
RESET_OPTIONS = {"never": "Tidak pernah", "yearly": "Tahunan", "monthly": "Bulanan", "daily": "Harian"}
EDITABLE = ("pattern", "prefix", "width", "reset", "start")

_BK = ["BOOKING_CODE", "CUSTOMER_INITIALS"]
REGISTRY = [
    {"key": "invoice", "label": "Invoice (DP / Pelunasan / Penuh)", "prefix": "INV",
     "pattern": "{PREFIX}/{DOC_TYPE}/{YYYY}/{MM}/{SEQ}", "width": 4, "reset": "yearly",
     "tokens": _BK + ["DOC_TYPE"], "desc": "Satu urutan untuk semua jenis invoice; {DOC_TYPE} membedakan DP/PEL/FULL."},
    {"key": "receipt", "label": "Kwitansi penerimaan pembayaran", "prefix": "KWT",
     "pattern": "{PREFIX}/{YYYY}/{MM}/{SEQ}", "width": 4, "reset": "yearly", "tokens": _BK, "desc": ""},
    {"key": "confirmation", "label": "Konfirmasi pemesanan", "prefix": "KONF",
     "pattern": "{PREFIX}/{YYYY}/{SEQ}", "width": 4, "reset": "yearly", "tokens": _BK + ["VEHICLE_CODE"], "desc": ""},
    {"key": "spj", "label": "Surat Perintah Jalan (driver)", "prefix": "SPJ",
     "pattern": "{PREFIX}/{YYYY}/{MM}/{SEQ}", "width": 4, "reset": "monthly", "tokens": _BK + ["VEHICLE_CODE"], "desc": ""},
    {"key": "refund", "label": "Nota Refund (pengembalian dana)", "prefix": "RFD",
     "pattern": "{PREFIX}/{YYYY}/{MM}/{SEQ}", "width": 4, "reset": "yearly", "tokens": _BK, "desc": ""},
]
REGISTRY_BY_KEY = {r["key"]: r for r in REGISTRY}


def initials(name: str, n: int = 3) -> str:
    words = [w for w in re.split(r"[^A-Za-z0-9]+", name or "") if w]
    if not words:
        return ""
    if len(words) == 1:
        return words[0][:n].upper()
    return "".join(w[0] for w in words[:n]).upper()


def tokens_in(pattern: str) -> list:
    return [m.group(1) for m in _TOKEN_RE.finditer(pattern or "")]


def validate_pattern(pattern: str, allowed_context: list) -> list:
    errs = []
    if not (pattern or "").strip():
        return ["Pola tidak boleh kosong."]
    known = {t for t, _, _ in GLOBAL_TOKENS} | set(allowed_context)
    for t in tokens_in(pattern):
        if t not in known:
            errs.append(f"Token {{{t}}} tidak tersedia untuk aturan ini.")
    if pattern.count("{") != pattern.count("}"):
        errs.append("Kurung kurawal tidak seimbang.")
    if "SEQ" not in tokens_in(pattern):
        errs.append("Pola harus memuat {SEQ} agar nomor unik.")
    return errs


def _period(reset: str, dt: datetime):
    if reset == "never":
        return None
    if reset == "monthly":
        return dt.strftime("%Y%m")
    if reset == "daily":
        return dt.strftime("%Y%m%d")
    return dt.strftime("%Y")


def render(pattern: str, tokens: dict, n: int, width: int, dt: datetime) -> str:
    base = {"YYYY": dt.strftime("%Y"), "YY": dt.strftime("%y"), "MM": dt.strftime("%m"),
            "DD": dt.strftime("%d"), "MM_ROMAN": ROMAN[dt.month]}

    def sub(m):
        tok, w = m.group(1), m.group(2)
        if tok == "SEQ":
            return str(n).zfill(int(w) if w else width)
        return str(tokens.get(tok, base.get(tok, "")) or "")
    return _TOKEN_RE.sub(sub, pattern)


async def effective_rule(db, key: str) -> dict:
    base = REGISTRY_BY_KEY[key]
    ov = await db.numbering_rules.find_one({"key": key}, {"_id": 0}) or {}
    rule = {**base, **{k: ov[k] for k in EDITABLE if k in ov and ov[k] is not None}}
    rule["overridden"] = bool(ov)
    rule["updated_by"], rule["updated_at"] = ov.get("updated_by"), ov.get("updated_at")
    rule.setdefault("start", 1)
    rule["default"] = {k: base.get(k) for k in ("pattern", "prefix", "width", "reset")}
    rule["default"]["start"] = 1
    return rule


async def _org_initials(db) -> str:
    s = await db.settings.find_one({"key": "company_info"}, {"_id": 0}) or {}
    return initials((s.get("value") or {}).get("name") or "RahazaTrans")


def sample_tokens(rule: dict, org_ini: str) -> dict:
    samples = {t: ex for t, (_, ex) in CONTEXT_TOKENS.items()}
    samples["ORG_INITIALS"] = org_ini
    samples["PREFIX"] = rule.get("prefix") or ""
    return samples


async def preview(db, rule: dict) -> str:
    """Contoh nomor tanpa menaikkan counter."""
    dt = datetime.now(timezone.utc)
    period = _period(rule["reset"], dt)
    scope = f"docnum:{rule['key']}" + (f":{period}" if period else "")
    cur = await db.counters.find_one({"id": scope}, {"_id": 0, "seq": 1}) or {}
    n = max(int(cur.get("seq") or 0) + 1, int(rule.get("start") or 1))
    return render(rule["pattern"], sample_tokens(rule, await _org_initials(db)), n, int(rule["width"]), dt)


async def list_rules(db) -> list:
    out = []
    for r in REGISTRY:
        rule = await effective_rule(db, r["key"])
        rule["preview"] = await preview(db, rule)
        out.append(rule)
    return out


async def save_rule(db, key: str, patch: dict, actor: str) -> dict:
    base = REGISTRY_BY_KEY[key]
    pattern = str(patch.get("pattern") or base["pattern"]).strip()
    errs = validate_pattern(pattern, base["tokens"])
    reset = patch.get("reset") or base["reset"]
    if reset not in RESET_OPTIONS:
        errs.append("Kebijakan reset tidak dikenal.")
    width = int(patch.get("width") or base["width"])
    start = int(patch.get("start") or 1)
    if not 1 <= width <= 8 or start < 1:
        errs.append("Lebar digit 1–8 dan nomor awal minimal 1.")
    if errs:
        raise ValueError(" ".join(errs))
    doc = {"key": key, "pattern": pattern,
           "prefix": patch.get("prefix") if patch.get("prefix") is not None else base["prefix"],
           "width": width, "reset": reset, "start": start, "updated_by": actor, "updated_at": now_iso()}
    await db.numbering_rules.update_one({"key": key}, {"$set": doc}, upsert=True)
    return await effective_rule(db, key)


async def reset_rule(db, key: str) -> dict:
    await db.numbering_rules.delete_one({"key": key})
    return await effective_rule(db, key)


async def generate(db, key: str, context: dict = None) -> str:
    """Nomor berikutnya (counter naik). context: booking_code, customer_name, doc_type, vehicle_code."""
    rule = await effective_rule(db, key)
    ctx = context or {}
    dt = datetime.now(timezone.utc)
    tokens = {
        "PREFIX": rule.get("prefix") or "",
        "ORG_INITIALS": await _org_initials(db),
        "BOOKING_CODE": (ctx.get("booking_code") or "").upper(),
        "CUSTOMER_INITIALS": initials(ctx.get("customer_name") or "", 2),
        "DOC_TYPE": (ctx.get("doc_type") or "").upper(),
        "VEHICLE_CODE": re.sub(r"[^A-Za-z0-9]", "", ctx.get("vehicle_code") or "").upper(),
    }
    period = _period(rule["reset"], dt)
    scope = f"docnum:{key}" + (f":{period}" if period else "")
    start = int(rule.get("start") or 1)
    if start > 1:
        await db.counters.update_one({"id": scope, "seq": {"$lt": start - 1}}, {"$set": {"seq": start - 1}})
        await db.counters.update_one({"id": scope}, {"$setOnInsert": {"seq": start - 1}}, upsert=True)
    n = await next_seq(db, scope)
    return render(rule["pattern"], tokens, n, int(rule["width"]), dt)
