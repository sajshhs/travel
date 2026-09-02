"""routers/data_management.py — Manajemen Data: backup lengkap (DB + media) ke ZIP, unduh, unggah,
restore penuh / per koleksi (dengan snapshot otomatis), retensi, jadwal harian via cron platform.

Akses: section 'data' (owner, ops_admin). Restore wajib confirm="RESTORE".
"""
import hmac
import os
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from core_utils import now_iso, safe_doc
from db import get_db
from dependencies import require_section
from services import backup as bk
from services import table_export as tx
from services import master_import as mi
from services.audit import record

router = APIRouter(prefix="/api", tags=["data-management"])
DATA = require_section("data")
SCHEDULE_KEY = "backup_schedule"
MAX_UPLOAD = 512 * 1024 * 1024


class BackupCreate(BaseModel):
    note: Optional[str] = Field(default="", max_length=300)
    include_media: bool = True


class RestoreIn(BaseModel):
    backup_id: str = Field(min_length=1)
    collections: Optional[List[str]] = None  # None/[] = seluruh koleksi
    include_media: bool = True
    confirm: str = Field(min_length=1)


class ScheduleIn(BaseModel):
    enabled: Optional[bool] = None
    keep_last: Optional[int] = Field(default=None, ge=1, le=60)
    include_media: Optional[bool] = None


async def _schedule(db) -> dict:
    doc = await db.settings.find_one({"key": SCHEDULE_KEY}, {"_id": 0}) or {}
    val = {"enabled": True, "keep_last": 7, "include_media": True, "hour_label": "02:00 WIB (harian)", "last_run_at": None, "last_status": None}
    val.update(doc.get("value") or {})
    return val


@router.get("/data/overview")
async def overview(user=Depends(DATA)):
    db = get_db()
    backups = await bk.list_backups(db)
    return {"backups": safe_doc(backups), "storage": bk.storage_info(), "schedule": await _schedule(db),
            "collections": await bk.collection_counts(db),
            "restores": safe_doc(await db.restore_logs.find({}, {"_id": 0}).sort("finished_at", -1).to_list(30))}


@router.post("/data/backups")
async def create_backup(body: BackupCreate, user=Depends(DATA)):
    db = get_db()
    meta = await bk.create_backup(db, kind="manual", actor=user, note=body.note, include_media=body.include_media)
    await record(db, actor=user, action="create", entity_type="backup", entity_id=meta["id"],
                 summary=f"Backup manual {meta['filename']} ({meta['size_label']}, {meta['documents']} dokumen, {meta['media_files']} media)")
    return safe_doc(meta)


@router.post("/data/backups/upload")
async def upload_backup(file: UploadFile = File(...), user=Depends(DATA)):
    if not (file.filename or "").lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Unggah berkas .zip hasil backup RahazaTrans")
    data = await file.read()
    if len(data) > MAX_UPLOAD:
        raise HTTPException(status_code=413, detail="Berkas backup terlalu besar (maks 512 MB)")
    db = get_db()
    try:
        meta = await bk.register_uploaded(db, data, file.filename, user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await record(db, actor=user, action="create", entity_type="backup", entity_id=meta["id"], summary=f"Unggah arsip backup {file.filename}")
    return safe_doc(meta)


@router.get("/data/backups/{backup_id}/manifest")
async def backup_manifest(backup_id: str, user=Depends(DATA)):
    meta, path = await bk.get_backup(get_db(), backup_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Backup tidak ditemukan")
    if not path:
        raise HTTPException(status_code=410, detail="Berkas arsip sudah tidak ada di server")
    return {"backup": safe_doc(meta), "manifest": bk.read_manifest(path)}


@router.get("/data/backups/{backup_id}/download")
async def download_backup(backup_id: str, user=Depends(DATA)):
    meta, path = await bk.get_backup(get_db(), backup_id)
    if not meta or not path:
        raise HTTPException(status_code=404, detail="Berkas backup tidak ditemukan")
    return FileResponse(str(path), media_type="application/zip", filename=meta["filename"])


@router.delete("/data/backups/{backup_id}")
async def delete_backup(backup_id: str, user=Depends(DATA)):
    db = get_db()
    ok = await bk.delete_backup(db, backup_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Backup tidak ditemukan")
    await record(db, actor=user, action="delete", entity_type="backup", entity_id=backup_id, summary="Hapus arsip backup")
    return {"ok": True}


@router.post("/data/restore")
async def restore(body: RestoreIn, user=Depends(DATA)):
    if body.confirm.strip().upper() != "RESTORE":
        raise HTTPException(status_code=400, detail='Ketik "RESTORE" untuk mengonfirmasi')
    db = get_db()
    try:
        log = await bk.restore_backup(db, body.backup_id, collections=body.collections or None, include_media=body.include_media, actor=user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await record(db, actor=user, action="restore", entity_type="backup", entity_id=body.backup_id,
                 summary=f"Restore {'penuh' if log['mode'] == 'full' else 'sebagian (' + str(len(log['collections'])) + ' koleksi)'} dari {log['backup_filename']} — snapshot {log.get('snapshot_id')}")
    return safe_doc(log)


@router.get("/data/exports")
async def list_exports(user=Depends(DATA)):
    db = get_db()
    out = []
    for t in tx.table_catalog():
        out.append({**t, "count": await db[t["collection"]].estimated_document_count()})
    return out


@router.get("/data/exports/{table}.xlsx")
async def export_table(table: str, request: Request, date_from: Optional[str] = None, date_to: Optional[str] = None, user=Depends(DATA)):
    """Filter opsional: ?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&status=a&status=b&type=dp&method=cash (multi-nilai)."""
    if table not in tx.TABLES:
        raise HTTPException(status_code=404, detail="Tabel ekspor tidak dikenal")
    if date_from and date_to and date_from[:10] > date_to[:10]:
        raise HTTPException(status_code=400, detail="Tanggal awal harus sebelum tanggal akhir")
    qp = request.query_params
    filters = {k: qp.getlist(k) for k in set(qp.keys()) - {"date_from", "date_to"}}
    query = tx.build_query(table, date_from, date_to, filters)
    db = get_db()
    data, fname, n = await tx.export_table(db, table, query)
    await record(db, actor=user, action="export", entity_type="table_export", entity_id=table,
                 summary=f"Ekspor Excel {tx.TABLES[table]['label']} ({n} baris{', terfilter' if query else ''})")
    return Response(content=data, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="{fname}"', "X-Row-Count": str(n)})


@router.get("/data/import/template.xlsx")
async def import_template(user=Depends(DATA)):
    return Response(content=mi.build_template(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": 'attachment; filename="template_master_data_rahazatrans.xlsx"'})


@router.get("/data/import/sheets")
async def import_sheets(user=Depends(DATA)):
    return [{"key": k, "title": v["title"], "columns": [{"header": h, "field": f, "required": r} for h, f, r, *_ in v["columns"]]} for k, v in mi.SHEETS.items()]


async def _read_xlsx(file: UploadFile) -> bytes:
    if not (file.filename or "").lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=400, detail="Unggah berkas Excel .xlsx (pakai template)")
    data = await file.read()
    if len(data) > 40 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Berkas terlalu besar (maks 40 MB)")
    return data


@router.post("/data/import/preview")
async def import_preview(file: UploadFile = File(...), user=Depends(DATA)):
    data = await _read_xlsx(file)
    try:
        parsed = mi.parse_workbook(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"sheets": await mi.plan(get_db(), parsed)}


@router.post("/data/import/commit")
async def import_commit(file: UploadFile = File(...), mode: str = Form(default="upsert"), sheets: str = Form(default=""),
                        snapshot: bool = Form(default=True), user=Depends(DATA)):
    if mode not in ("upsert", "insert_only"):
        raise HTTPException(status_code=400, detail="Mode impor tidak dikenal")
    data = await _read_xlsx(file)
    try:
        parsed = mi.parse_workbook(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    db = get_db()
    snap = None
    if snapshot:
        snap = await bk.create_backup(db, kind="pre_import", actor=user, note=f"Snapshot otomatis sebelum impor master data ({file.filename})", include_media=False)
    wanted = [s for s in sheets.split(",") if s] or None
    log = await mi.commit(db, parsed, mode=mode, sheets=wanted, actor=user)
    log["snapshot_id"] = (snap or {}).get("id")
    tot = {k: sum(v.get(k, 0) for v in log["summary"].values()) for k in ("inserted", "updated", "skipped", "errors")}
    await record(db, actor=user, action="import", entity_type="master_import", entity_id=log["id"],
                 summary=f"Impor master data ({mode}): +{tot['inserted']} baru, {tot['updated']} diperbarui, {tot['skipped']} dilewati, {tot['errors']} error")
    return {**safe_doc(log), "totals": tot}


@router.get("/data/import/history")
async def import_history(user=Depends(DATA)):
    return safe_doc(await get_db().import_logs.find({}, {"_id": 0}).sort("finished_at", -1).to_list(20))


@router.get("/data/schedule")
async def get_schedule(user=Depends(DATA)):
    return await _schedule(get_db())


@router.patch("/data/schedule")
async def patch_schedule(body: ScheduleIn, user=Depends(DATA)):
    db = get_db()
    cur = await _schedule(db)
    cur.update(body.model_dump(exclude_none=True))
    await db.settings.update_one({"key": SCHEDULE_KEY}, {"$set": {"key": SCHEDULE_KEY, "value": cur, "updated_at": now_iso()}}, upsert=True)
    await record(db, actor=user, action="update", entity_type="backup_schedule", entity_id=SCHEDULE_KEY, summary=f"Jadwal backup: {'aktif' if cur['enabled'] else 'nonaktif'}, simpan {cur['keep_last']} terakhir")
    return cur


async def _run_auto_backup(run_id: str):
    db = get_db()
    sched = await _schedule(db)
    status = "skipped"
    try:
        if sched.get("enabled", True):
            meta = await bk.create_backup(db, kind="auto", actor=None, note=f"Backup harian otomatis (run {run_id})", include_media=bool(sched.get("include_media", True)))
            removed = await bk.apply_retention(db, int(sched.get("keep_last") or 7))
            status = f"ok: {meta['filename']} ({meta['size_label']}), hapus {removed} arsip lama"
    except Exception as exc:  # noqa: BLE001
        status = f"gagal: {str(exc)[:160]}"
    sched.update({"last_run_at": now_iso(), "last_status": status})
    await db.settings.update_one({"key": SCHEDULE_KEY}, {"$set": {"key": SCHEDULE_KEY, "value": sched}}, upsert=True)


@router.post("/cron/backup-daily")
async def cron_backup_daily(request: Request, background: BackgroundTasks, authorization: str = Header(default=""),
                            x_webhook_id: str = Header(default="")):
    # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
    secret = os.environ.get("WEBHOOK_CRON_SECRET") or ""
    token = authorization[7:] if authorization.startswith("Bearer ") else ""
    if not secret or not token or not hmac.compare_digest(token, secret):
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        body = await request.json() if (await request.body()) else {}
    except ValueError:
        raise HTTPException(status_code=400, detail="Body tidak valid")
    run_id = x_webhook_id or (body or {}).get("run_id") or now_iso()
    db = get_db()
    dup = await db.backup_jobs.find_one({"run_id": run_id})
    if dup:
        return {"ok": True, "duplicate": True}
    await db.backup_jobs.insert_one({"run_id": run_id, "received_at": now_iso()})
    background.add_task(_run_auto_backup, run_id)
    return {"ok": True, "queued": True}
