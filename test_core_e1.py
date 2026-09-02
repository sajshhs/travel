#!/usr/bin/env python3
"""test_core_e1.py — POC E1 (Event Bus + Automation Engine + WhatsApp mock).

Membuktikan pipeline inti TANPA HTTP/kredensial:
  emit(event) -> automation.process_event(rule cocok) -> aksi (send_wa mock /
  create_notification / assign_agent) -> automation_runs ter-log + pesan WA masuk
  Inbox (cost tracking) + idempotency + WA inbound (handle_inbound).

Jalankan: cd /app && python test_core_e1.py
Membersihkan data uji sendiri (prefix __poc__) di akhir.
"""
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / "backend" / ".env")
except Exception:
    pass

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402
from core_utils import new_id, now_iso  # noqa: E402
from services import events, whatsapp  # noqa: E402
from services.automation import default_rules  # noqa: E402

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ.get("DB_NAME", "app_db")
G, R, Y, X = "\033[92m", "\033[91m", "\033[93m", "\033[0m"
passed, failed = 0, 0


def check(label, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  {G}[PASS]{X} {label}")
    else:
        failed += 1
        print(f"  {R}[FAIL]{X} {label} {Y}{detail}{X}")


async def cleanup(db, tag):
    for col in ("events", "automation_runs", "automation_rules", "messages",
                "conversations", "leads", "lead_activities", "notification_tasks", "users"):
        await db[col].delete_many({"_poc": tag})


async def run():
    db = AsyncIOMotorClient(MONGO_URL)[DB_NAME]
    tag = "__poc_e1__"
    await cleanup(db, tag)
    print(f"\n=== POC E1 — Event Bus + Automation + WhatsApp(mock) (DB: {DB_NAME}) ===\n")

    # Prasyarat: company_info + wa_config(mock) + 1 agen aktif + 1 rule lead.created.
    await db.settings.update_one({"key": "company_info"},
                                 {"$set": {"key": "company_info", "value": {"name": "Rahaza Travel"}}}, upsert=True)
    await db.settings.update_one({"key": "wa_config"},
                                 {"$set": {"key": "wa_config", "value": {"provider": "mock", "price_per_message": 350,
                                                                          "auto_reply_enabled": True}}}, upsert=True)
    agent = {"id": new_id("usr"), "name": "POC Agent", "email": f"{new_id('a')}@poc.local",
             "role": "ops_admin", "status": "active", "created_at": now_iso(), "_poc": tag}
    await db.users.insert_one(agent)

    rules = default_rules()
    rule_lead = next(r for r in rules if r["event_type"] == "lead.created")
    rule_in = next(r for r in rules if r["event_type"] == "wa.inbound")
    for r in (rule_lead, rule_in):
        r["_poc"] = tag
        await db.automation_rules.insert_one(r)

    # Lead nyata (belum di-assign) supaya aksi assign_agent bekerja.
    lead = {"id": new_id("led"), "customer_name": "Budi POC", "phone": "081299990001",
            "phone_normalized": "+6281299990001", "source": "website", "stage": "new",
            "assigned_to": None, "destination": "Bromo", "value": 0.0,
            "created_at": now_iso(), "last_activity_at": now_iso(), "_poc": tag}
    await db.leads.insert_one(lead)

    # --- 1) EMIT lead.created ---
    payload = {"lead_id": lead["id"], "customer_name": lead["customer_name"],
               "phone": lead["phone"], "destination": lead["destination"], "source": "website"}
    ev = await events.emit(db, "lead.created", payload, source="poc",
                           ref_type="lead", ref_id=lead["id"],
                           dedupe_key=f"lead.created:{lead['id']}")
    check("emit lead.created mengembalikan event", ev is not None)
    check("event tersimpan & processed", ev and ev.get("processed") is True)
    check("runs_created >= 1", ev and ev.get("runs_created", 0) >= 1, f"runs={ev.get('runs_created') if ev else None}")

    # --- 2) automation_run tercatat sukses ---
    run_doc = await db.automation_runs.find_one({"rule_id": rule_lead["id"], "event_id": ev["id"]})
    check("automation_run dibuat", run_doc is not None)
    check("run status success", run_doc and run_doc.get("status") == "success",
          str(run_doc.get("status") if run_doc else None))
    types = [a.get("type") for a in (run_doc or {}).get("actions", [])]
    check("aksi mencakup send_wa+assign_agent+create_notification",
          set(types) >= {"send_wa", "assign_agent", "create_notification"}, str(types))

    # --- 3) WA mock terkirim & masuk Inbox dgn cost ---
    conv = await db.conversations.find_one({"channel": "whatsapp", "contact_phone": lead["phone"]})
    check("conversation WA dibuat", conv is not None)
    wa_msg = await db.messages.find_one({"conversation_id": (conv or {}).get("id"), "direction": "out"})
    check("pesan WA outbound tercatat", wa_msg is not None)
    check("status pesan 'sent'", wa_msg and wa_msg.get("status") == "sent", str(wa_msg.get("status") if wa_msg else None))
    check("cost tercatat (>0)", wa_msg and float(wa_msg.get("cost") or 0) > 0, str(wa_msg.get("cost") if wa_msg else None))
    check("wa_message_id mock ada", wa_msg and str(wa_msg.get("wa_message_id", "")).startswith("wamid.mock_"))
    check("conversation.total_cost terakumulasi", conv and float(conv.get("total_cost") or 0) > 0)
    body = (wa_msg or {}).get("body", "")
    check("template ter-render ({customer_name}->Budi POC, {company}->Rahaza Travel)",
          "Budi POC" in body and "Rahaza Travel" in body and "{" not in body, body[:80])

    # --- 4) assign_agent benar-benar menugaskan lead ---
    lead_after = await db.leads.find_one({"id": lead["id"]})
    check("lead ter-assign ke agen", lead_after and lead_after.get("assigned_to") == agent["id"])

    # --- 5) notification dibuat ---
    notif = await db.notification_tasks.find_one({"dedupe_key": f"auto:{rule_lead['id']}:{ev['id']}"})
    check("notification otomasi dibuat", notif is not None)

    # --- 6) IDEMPOTENCY: emit ulang (dedupe_key sama) -> tak ada event/run baru ---
    n_events_before = await db.events.count_documents({"dedupe_key": f"lead.created:{lead['id']}"})
    ev2 = await events.emit(db, "lead.created", payload, dedupe_key=f"lead.created:{lead['id']}")
    n_events_after = await db.events.count_documents({"dedupe_key": f"lead.created:{lead['id']}"})
    check("emit dedupe: tidak ada event duplikat", ev2 is None and n_events_before == n_events_after == 1)
    # proses event lama lagi -> run dedupe (rule:event) mencegah duplikat
    from services.automation import process_event
    again = await process_event(db, ev)
    n_runs = await db.automation_runs.count_documents({"rule_id": rule_lead["id"], "event_id": ev["id"]})
    check("run dedupe: tak ada run duplikat utk (rule,event)", again == 0 and n_runs == 1, f"again={again} n_runs={n_runs}")

    # --- 7) WA INBOUND (handle_inbound) ---
    res = await whatsapp.handle_inbound(db, "081277778888", "Halo, mau tanya sewa Hiace", name="Sinta POC")
    check("handle_inbound diterima", res.get("status") == "received")
    in_conv = await db.conversations.find_one({"id": res.get("conversation_id")})
    check("inbound: conversation ada + session window terbuka", in_conv and in_conv.get("session_expires_at"))
    in_msg = await db.messages.find_one({"conversation_id": res.get("conversation_id"), "direction": "in"})
    check("inbound: pesan masuk tercatat", in_msg is not None)
    auto = await db.messages.find_one({"conversation_id": res.get("conversation_id"),
                                       "direction": "out", "source": "auto_reply"})
    check("inbound: auto-reply terkirim", auto is not None)
    new_lead = await db.leads.find_one({"phone": "081277778888", "_poc": {"$exists": False}})
    check("inbound: lead WA dibuat (source=whatsapp)", new_lead and new_lead.get("source") == "whatsapp")
    wa_event = await db.events.find_one({"type": "wa.inbound", "ref_id": res.get("conversation_id")})
    check("inbound: event wa.inbound dipancarkan", wa_event is not None)
    if new_lead:
        await db.leads.delete_one({"id": new_lead["id"]})
        await db.conversations.delete_many({"id": res.get("conversation_id")})
        await db.messages.delete_many({"conversation_id": res.get("conversation_id")})
        await db.lead_activities.delete_many({"lead_id": new_lead["id"]})
        await db.events.delete_many({"ref_id": res.get("conversation_id")})

    await cleanup(db, tag)
    print(f"\n=== HASIL: {G}{passed} PASS{X} | {R}{failed} FAIL{X} ===\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))
