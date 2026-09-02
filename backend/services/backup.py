"""services/backup.py — backup & restore data LENGKAP (semua koleksi Mongo + berkas media) ke arsip ZIP.

Arsip: manifest.json + db/<koleksi>.jsonl (bson json_util → ObjectId/datetime utuh) + media/<path>
(isi backend/uploads: media, pod, cms, spin360…). Registri arsip di koleksi `backups` (tidak ikut
di-restore). Sebelum restore SELALU dibuat snapshot `pre_restore` supaya bisa dibatalkan.
"""
import asyncio
import io
import json
import logging
import os
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from bson import json_util

from core_utils import new_id, now_iso

logger = logging.getLogger("travel_fleet.backup")
BACKEND_DIR = Path(__file__).resolve().parent.parent
BACKUP_DIR = Path(os.environ.get("BACKUP_DIR") or (BACKEND_DIR / "backups"))
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR") or (BACKEND_DIR / "uploads"))
MEDIA_LOCAL_DIR = Path(os.environ.get("MEDIA_LOCAL_DIR") or (UPLOAD_DIR / "media"))
FORMAT_VERSION = 1
SKIP_COLLECTIONS = {"backups", "restore_logs", "backup_jobs"}  # registri lokal — tidak ikut dump/restore
KIND_LABEL = {"manual": "Manual", "auto": "Otomatis (harian)", "pre_restore": "Snapshot sebelum restore", "uploaded": "Diunggah",
              "pre_import": "Snapshot sebelum impor"}
_lock = asyncio.Lock()


def _ensure_dir():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def _media_roots():
    roots = [UPLOAD_DIR]
    if not str(MEDIA_LOCAL_DIR.resolve()).startswith(str(UPLOAD_DIR.resolve())):
        roots.append(MEDIA_LOCAL_DIR)
    return [r for r in roots if r.exists()]


def _media_files():
    """[(arcname, abs_path)] semua berkas media lokal."""
    out = []
    for root in _media_roots():
        prefix = "uploads" if root == UPLOAD_DIR else "media_local"
        for p in root.rglob("*"):
            if p.is_file():
                out.append((f"media/{prefix}/{p.relative_to(root).as_posix()}", p))
    return out


async def collection_counts(db) -> list:
    names = sorted(n for n in await db.list_collection_names() if not n.startswith("system.") and n not in SKIP_COLLECTIONS)
    out = []
    for n in names:
        out.append({"name": n, "count": await db[n].estimated_document_count()})
    return out


def _fmt_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


# ------------------------------------------------------------------ BACKUP
async def create_backup(db, *, kind: str = "manual", actor: dict = None, note: str = "", include_media: bool = True) -> dict:
    async with _lock:
        _ensure_dir()
        bid = new_id("bak")
        ts = datetime.now(timezone.utc)
        filename = f"backup_{ts.strftime('%Y%m%d_%H%M%S')}_{kind}_{bid[-6:]}.zip"
        path = BACKUP_DIR / filename
        tmp = path.with_suffix(".part")
        manifest = {"format_version": FORMAT_VERSION, "id": bid, "kind": kind, "created_at": ts.isoformat(),
                    "db_name": db.name, "app": "RahazaTrans", "collections": [], "media_files": 0, "note": note or ""}
        total_docs = 0
        with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for col in await collection_counts(db):
                name = col["name"]
                buf = io.StringIO()
                n = 0
                async for doc in db[name].find({}):
                    buf.write(json_util.dumps(doc))
                    buf.write("\n")
                    n += 1
                zf.writestr(f"db/{name}.jsonl", buf.getvalue())
                manifest["collections"].append({"name": name, "count": n})
                total_docs += n
            if include_media:
                for arc, p in _media_files():
                    try:
                        zf.write(p, arc)
                        manifest["media_files"] += 1
                    except OSError as exc:  # noqa: PERF203
                        logger.warning("Lewati media %s: %s", p, exc)
            zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=1))
        tmp.replace(path)
        size = path.stat().st_size
        meta = {"id": bid, "filename": filename, "size": size, "size_label": _fmt_size(size), "kind": kind,
                "kind_label": KIND_LABEL.get(kind, kind), "note": note or "", "collections": len(manifest["collections"]),
                "documents": total_docs, "media_files": manifest["media_files"], "include_media": include_media,
                "created_at": ts.isoformat(), "created_by": (actor or {}).get("id"), "created_by_name": (actor or {}).get("name") or ("Sistem" if kind == "auto" else None)}
        await db.backups.insert_one(dict(meta))
        return meta


async def register_uploaded(db, data: bytes, original_name: str, actor: dict) -> dict:
    """Validasi ZIP unggahan (harus ada manifest.json + db/*.jsonl) lalu simpan ke registri."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
        manifest = json.loads(zf.read("manifest.json"))
    except (zipfile.BadZipFile, KeyError, ValueError) as exc:
        raise ValueError(f"Berkas bukan arsip backup RahazaTrans yang sah ({exc}).")
    if int(manifest.get("format_version") or 0) != FORMAT_VERSION:
        raise ValueError("Versi format backup tidak didukung.")
    names = zf.namelist()
    cols = [c for c in manifest.get("collections", []) if f"db/{c['name']}.jsonl" in names]
    _ensure_dir()
    bid = new_id("bak")
    filename = f"upload_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{bid[-6:]}.zip"
    (BACKUP_DIR / filename).write_bytes(data)
    meta = {"id": bid, "filename": filename, "size": len(data), "size_label": _fmt_size(len(data)), "kind": "uploaded",
            "kind_label": KIND_LABEL["uploaded"], "note": f"Diunggah: {original_name} (asal {manifest.get('created_at', '')[:19]})",
            "collections": len(cols), "documents": sum(int(c.get("count") or 0) for c in cols),
            "media_files": sum(1 for n in names if n.startswith("media/")), "include_media": any(n.startswith("media/") for n in names),
            "source_created_at": manifest.get("created_at"), "created_at": now_iso(),
            "created_by": actor.get("id"), "created_by_name": actor.get("name")}
    await db.backups.insert_one(dict(meta))
    return meta


async def list_backups(db) -> list:
    rows = await db.backups.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    for r in rows:
        r["available"] = (BACKUP_DIR / r["filename"]).exists()
    return rows


async def get_backup(db, bid: str):
    meta = await db.backups.find_one({"id": bid}, {"_id": 0})
    if not meta:
        return None, None
    path = BACKUP_DIR / meta["filename"]
    return meta, (path if path.exists() else None)


def read_manifest(path: Path) -> dict:
    with zipfile.ZipFile(path) as zf:
        m = json.loads(zf.read("manifest.json"))
        names = zf.namelist()
        m["media_files"] = sum(1 for n in names if n.startswith("media/"))
        return m


async def delete_backup(db, bid: str) -> bool:
    meta, path = await get_backup(db, bid)
    if not meta:
        return False
    if path:
        path.unlink(missing_ok=True)
    await db.backups.delete_one({"id": bid})
    return True


async def apply_retention(db, keep_auto: int = 7) -> int:
    autos = await db.backups.find({"kind": "auto"}, {"_id": 0}).sort("created_at", -1).to_list(500)
    removed = 0
    for r in autos[max(int(keep_auto or 0), 1):]:
        await delete_backup(db, r["id"])
        removed += 1
    return removed


def storage_info() -> dict:
    _ensure_dir()
    files = [p for p in BACKUP_DIR.glob("*.zip")]
    total = sum(p.stat().st_size for p in files)
    du = shutil.disk_usage(str(BACKUP_DIR))
    return {"dir": str(BACKUP_DIR), "files": len(files), "total_bytes": total, "total_label": _fmt_size(total),
            "disk_free_label": _fmt_size(du.free)}


# ------------------------------------------------------------------ RESTORE
async def restore_backup(db, bid: str, *, collections=None, include_media: bool = True, actor: dict, snapshot: bool = True) -> dict:
    """Restore penuh atau per koleksi (mode ganti: drop → insert). Snapshot pre_restore dibuat dulu."""
    meta, path = await get_backup(db, bid)
    if not meta or not path:
        raise ValueError("Arsip backup tidak ditemukan di server.")
    manifest = read_manifest(path)
    available = {c["name"] for c in manifest.get("collections", [])}
    targets = sorted(available if not collections else (set(collections) & available))
    if collections and not targets:
        raise ValueError("Koleksi yang dipilih tidak ada di dalam arsip.")
    targets = [t for t in targets if t not in SKIP_COLLECTIONS]
    started = now_iso()
    snap = None
    if snapshot:
        snap = await create_backup(db, kind="pre_restore", actor=actor, note=f"Snapshot otomatis sebelum restore {meta['filename']}")
    async with _lock:
        restored = []
        with zipfile.ZipFile(path) as zf:
            for name in targets:
                raw = zf.read(f"db/{name}.jsonl").decode("utf-8")
                docs = [json_util.loads(line) for line in raw.splitlines() if line.strip()]
                await db[name].drop()
                if docs:
                    for i in range(0, len(docs), 500):
                        await db[name].insert_many(docs[i:i + 500], ordered=False)
                restored.append({"name": name, "count": len(docs)})
            media_written = 0
            if include_media:
                for info in zf.infolist():
                    if not info.filename.startswith("media/") or info.is_dir():
                        continue
                    rel = info.filename[len("media/"):]
                    if rel.startswith("uploads/"):
                        dest = UPLOAD_DIR / rel[len("uploads/"):]
                    elif rel.startswith("media_local/"):
                        dest = MEDIA_LOCAL_DIR / rel[len("media_local/"):]
                    else:
                        continue
                    if ".." in Path(rel).parts:
                        continue
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(zf.read(info))
                    media_written += 1
    log = {"id": new_id("rst"), "backup_id": bid, "backup_filename": meta["filename"], "mode": "full" if not collections else "partial",
           "collections": restored, "documents": sum(r["count"] for r in restored), "media_files": media_written,
           "snapshot_id": (snap or {}).get("id"), "started_at": started, "finished_at": now_iso(),
           "actor_id": actor.get("id"), "actor_name": actor.get("name")}
    await db.restore_logs.insert_one(dict(log))
    log.pop("_id", None)
    return log
