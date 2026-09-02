#!/usr/bin/env python3
"""test_core_e2.py — POC E2 (CRM Growth Engine).

Membuktikan inti TANPA HTTP: Lead Scoring + SLA breach (+event), RFM/LTV + at-risk (+event),
Segment resolve, Nurturing Sequence (enroll + process_due via WA mock), Campaign broadcast
(send ke segment, hormati opt-out, cost), serta aksi otomasi enroll_sequence (E1).

Jalankan: cd /app && python test_core_e2.py
"""
import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
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
from services import growth, segments as seg_svc, sequences as seq_svc, campaigns as cmp_svc, events  # noqa: E402
from services.automation import default_rules, process_event  # noqa: E402

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ.get("DB_NAME", "app_db")
G, R, Y, X = "\033[92m", "\033[91m", "\033[93m", "\033[0m"
passed = failed = 0
TAG = "__poc_e2__"


def check(label, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1; print(f"  {G}[PASS]{X} {label}")
    else:
        failed += 1; print(f"  {R}[FAIL]{X} {label} {Y}{detail}{X}")


async def cleanup(db):
    for col in ("leads", "customers", "bookings", "conversations", "messages", "segments",
                "sequences", "sequence_enrollments", "campaigns", "campaign_recipients",
                "automation_rules", "users", "lead_activities", "notification_tasks"):
        await db[col].delete_many({"_poc": TAG})


async def run():
    db = AsyncIOMotorClient(MONGO_URL)[DB_NAME]
    await cleanup(db)
    print(f"\n=== POC E2 — CRM Growth Engine (DB: {DB_NAME}) ===\n")
    cfg = await growth.get_config(db)

    # --- 1) LEAD SCORING ---
    hot_lead = {"source": "referral", "value": 6_000_000, "phone": "0812", "email": "a@b.c",
                "destination": "Bali", "trip_date": now_iso(), "stage": "quoted"}
    score, band, factors = growth.compute_lead_score(hot_lead, cfg, activity_count=3)
    check("lead lengkap & bernilai → skor tinggi", score >= 65, f"score={score}")
    check("band = hot", band == "hot", band)
    cold = growth.compute_lead_score({"source": "manual", "value": 0, "stage": "new"}, cfg, 0)
    check("lead minim → band cold", cold[1] == "cold", cold[1])

    # --- 2) SLA breach + event ---
    past = (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat()
    led = {"id": new_id("led"), "customer_name": "SLA POC", "phone": "081200000001",
           "source": "website", "stage": "new", "assigned_to": None, "value": 0,
           "first_response_at": None, "created_at": past, "last_activity_at": past, "_poc": TAG}
    await db.leads.insert_one(led)
    status, due = growth._sla_status(led, cfg)
    check("SLA respons telat → breached", status == "breached", status)
    await growth.scan_sla(db)
    ev = await db.events.find_one({"type": "lead.sla_breached", "ref_id": led["id"]})
    check("event lead.sla_breached dipancarkan", ev is not None)

    # --- 3) RFM/LTV + at-risk ---
    cust_a = {"id": new_id("cus"), "name": "POCseg Aktif", "phone": "081200000010",
              "created_at": now_iso(), "_poc": TAG}
    await db.customers.insert_one(cust_a)
    recent = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    for i in range(5):
        await db.bookings.insert_one({"id": new_id("bkg"), "customer_id": cust_a["id"],
                                      "status": "completed", "start_datetime": recent,
                                      "paid_amount": 5_000_000, "total_amount": 5_000_000, "_poc": TAG})
    rfm = await growth.rfm_for_customer(db, cust_a, cfg)
    check("RFM frequency=5", rfm["frequency"] == 5, str(rfm["frequency"]))
    check("RFM monetary terhitung (25jt)", rfm["monetary"] == 25_000_000, str(rfm["monetary"]))
    check("RFM lifecycle aktif", rfm["lifecycle"] == "aktif", rfm["lifecycle"])
    check("RFM segmen Champions/Loyal", rfm["rfm_segment"] in ("Champions", "Loyal"), rfm["rfm_segment"])

    cust_churn = {"id": new_id("cus"), "name": "POCseg Churn", "phone": "081200000011",
                  "created_at": now_iso(), "wa_opt_in": False, "_poc": TAG}
    await db.customers.insert_one(cust_churn)
    old = (datetime.now(timezone.utc) - timedelta(days=200)).isoformat()
    await db.bookings.insert_one({"id": new_id("bkg"), "customer_id": cust_churn["id"],
                                  "status": "completed", "start_datetime": old,
                                  "paid_amount": 3_000_000, "total_amount": 3_000_000, "_poc": TAG})
    await growth.scan_rfm(db)
    ar = await db.events.find_one({"type": "customer.at_risk", "ref_id": cust_churn["id"]})
    check("event customer.at_risk dipancarkan (churn)", ar is not None)
    cc = await db.customers.find_one({"id": cust_churn["id"]})
    check("lifecycle churned ter-cache di customer", cc.get("lifecycle") == "churned", str(cc.get("lifecycle")))

    # --- 4) SEGMENT resolve ---
    seg = {"id": new_id("seg"), "name": "POC Segmen", "audience": "customer",
           "criteria": {"q": "POCseg"}, "_poc": TAG}
    await db.segments.insert_one(seg)
    count, members = await seg_svc.resolve_segment(db, seg)
    check("segment resolve menemukan 2 anggota POCseg", count == 2, f"count={count}")

    # --- 5) NURTURING SEQUENCE (enroll + process_due via WA mock) ---
    sequence = {"id": new_id("seq"), "name": "POC Nurture", "audience": "customer", "enabled": True,
                "steps": [{"delay_hours": 0, "action": "send_wa", "text": "Halo {name}, langkah 1 nurture."},
                          {"delay_hours": 24, "action": "send_wa", "text": "Halo {name}, langkah 2."}],
                "stats": {"enrolled": 0, "completed": 0}, "_poc": TAG}
    await db.sequences.insert_one(sequence)
    enr = await seq_svc.enroll(db, sequence, cust_a["id"], name=cust_a["name"], phone=cust_a["phone"])
    check("enroll sequence berhasil", enr is not None)
    dup = await seq_svc.enroll(db, sequence, cust_a["id"], name=cust_a["name"], phone=cust_a["phone"])
    check("enroll idempotent (tak dobel)", dup is None)
    n = await seq_svc.process_due(db)
    check("process_due menjalankan ≥1 langkah", n >= 1, f"n={n}")
    enr2 = await db.sequence_enrollments.find_one({"id": enr["id"]})
    check("enrollment maju ke step 1 + next_run_at masa depan",
          enr2.get("step_index") == 1 and enr2.get("next_run_at") > now_iso(), str(enr2.get("step_index")))
    wa = await db.messages.find_one({"conversation_id": {"$exists": True}, "source": f"sequence:{sequence['id']}"})
    check("langkah WA terkirim (mock) + tercatat", wa is not None and float(wa.get("cost") or 0) > 0)

    # --- 6) CAMPAIGN broadcast (segment, hormati opt-out, cost) ---
    camp = {"id": new_id("cmp"), "name": "POC Kampanye", "channel": "whatsapp", "audience": "customer",
            "segment_id": seg["id"], "message": "Promo spesial untuk {name}!", "status": "draft",
            "stats": {}, "created_at": now_iso(), "_poc": TAG}
    await db.campaigns.insert_one(camp)
    # opt-out cust_churn: buat conversation WA opted-out
    await db.conversations.insert_one({"id": new_id("cnv"), "channel": "whatsapp",
                                       "contact_phone": cust_churn["phone"], "wa_opt_in": False,
                                       "customer_id": cust_churn["id"], "created_at": now_iso(),
                                       "last_message_at": now_iso(), "_poc": TAG})
    stats = await cmp_svc.send_campaign(db, camp)
    check("kampanye total 2 penerima", stats.get("total") == 2, str(stats))
    check("kampanye terkirim ke 1 (cust aktif)", stats.get("sent") == 1, str(stats))
    check("kampanye skip 1 (opt-out)", stats.get("skipped") == 1, str(stats))
    check("biaya kampanye terakumulasi (>0)", float(stats.get("cost") or 0) > 0, str(stats.get("cost")))
    recs = await db.campaign_recipients.count_documents({"campaign_id": camp["id"]})
    check("campaign_recipients tercatat (2)", recs == 2, str(recs))
    sent_camp = await db.campaigns.find_one({"id": camp["id"]})
    check("status kampanye → sent", sent_camp.get("status") == "sent", sent_camp.get("status"))

    # --- 7) AKSI OTOMASI enroll_sequence (E1) ---
    seq2 = {"id": new_id("seq"), "name": "POC AutoNurture", "audience": "lead", "enabled": True,
            "steps": [{"delay_hours": 0, "action": "create_task", "text": "tindak lanjut"}],
            "stats": {"enrolled": 0}, "_poc": TAG}
    await db.sequences.insert_one(seq2)
    rule = {"id": new_id("aur"), "name": "POC enroll", "event_type": "lead.created", "enabled": True,
            "conditions": [], "actions": [{"type": "enroll_sequence", "params": {"sequence_id": seq2["id"]}}],
            "system": False, "_poc": TAG}
    await db.automation_rules.insert_one(rule)
    led2 = {"id": new_id("led"), "customer_name": "Enroll POC", "phone": "081200000022",
            "source": "website", "stage": "new", "_poc": TAG}
    await db.leads.insert_one(led2)
    ev2 = await events.emit(db, "lead.created", {"lead_id": led2["id"], "customer_name": "Enroll POC",
                            "phone": led2["phone"]}, dedupe_key=f"poc.enroll:{led2['id']}")
    run_doc = await db.automation_runs.find_one({"rule_id": rule["id"], "event_id": ev2["id"]})
    check("rule enroll_sequence dieksekusi sukses", run_doc and run_doc.get("status") == "success", str(run_doc.get("status") if run_doc else None))
    enr3 = await db.sequence_enrollments.find_one({"sequence_id": seq2["id"], "target_id": led2["id"]})
    check("lead ter-enroll ke sequence via otomasi", enr3 is not None)

    # bersihkan jejak (termasuk yang dihasilkan emit/send_wa tanpa tag)
    for cid in [c["id"] for c in await db.conversations.find({"customer_id": {"$in": [cust_a["id"], cust_churn["id"]]}}, {"_id": 0, "id": 1}).to_list(50)]:
        await db.messages.delete_many({"conversation_id": cid})
        await db.conversations.delete_many({"id": cid})
    await db.events.delete_many({"ref_id": {"$in": [led["id"], cust_churn["id"], led2["id"]]}})
    await db.automation_runs.delete_many({"rule_id": rule["id"]})
    await db.campaign_recipients.delete_many({"campaign_id": camp["id"]})
    await cleanup(db)

    print(f"\n=== HASIL: {G}{passed} PASS{X} | {R}{failed} FAIL{X} ===\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))
