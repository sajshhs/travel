#!/usr/bin/env python3
"""test_core_eads_e6.py — POC E-ADS (atribusi & marketing) + E6 prep (WA Meta Cloud).

Membuktikan INTI (tanpa HTTP, kecuali Graph API yang sengaja TIDAK dipanggil tanpa kredensial):
  E-ADS
  1. derive_channel: gclid→google_ads, fbclid→meta_ads, ttclid→tiktok_ads, utm+medium berbayar→*_ads,
     organik/referral/direct benar.
  2. build_attribution: first+last touch tersimpan; channel final (last bermakna > first > fallback).
  3. ads.create_ad_lead: lead ter-atribusi (channel={provider}_ads, consent, attribution) + parsing
     envelope Meta field_data + abaikan tanpa phone/email.
  4. channels_roi: kelompok per channel; cpl/cac/roas konsisten dgn spend.
  5. segments: kriteria channel & marketing_consent menyaring lead dgn benar.
  E6
  6. MetaCloudProvider: _ready() benar; tanpa kredensial → 'failed' pesan jelas (TANPA raise);
     MockProvider 'sent'; send_wa(mock) → 'sent'.

Jalankan: cd /app && python test_core_eads_e6.py
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
from services import ads as ads_service  # noqa: E402
from services import analytics  # noqa: E402
from services import attribution as attr  # noqa: E402
from services import segments  # noqa: E402
from services import whatsapp as wa  # noqa: E402
from core_utils import new_id, now_iso  # noqa: E402

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ.get("DB_NAME", "app_db")
G, R, Y, X = "\033[92m", "\033[91m", "\033[93m", "\033[0m"
passed = failed = 0
TEST_TAG = "eads_poc"
TEST_PHONE = "628999000111"


def check(label, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  {G}[PASS]{X} {label}")
    else:
        failed += 1
        print(f"  {R}[FAIL]{X} {label} {Y}{detail}{X}")


async def cleanup(db):
    await db.leads.delete_many({"_test_tag": TEST_TAG})
    convs = await db.conversations.find({"contact_phone": TEST_PHONE}, {"_id": 0, "id": 1}).to_list(50)
    ids = [c["id"] for c in convs]
    if ids:
        await db.messages.delete_many({"conversation_id": {"$in": ids}})
        await db.conversations.delete_many({"id": {"$in": ids}})


async def main():
    print(f"\n{'='*60}\n  POC E-ADS + E6 prep\n{'='*60}")
    db = AsyncIOMotorClient(MONGO_URL)[DB_NAME]
    await cleanup(db)

    # --- 1. derive_channel ---
    print(f"\n{Y}[1] derive_channel (normalisasi UTM/click-id){X}")
    check("gclid → google_ads", attr.derive_channel({"gclid": "abc"}) == "google_ads")
    check("fbclid → meta_ads", attr.derive_channel({"fbclid": "x"}) == "meta_ads")
    check("ttclid → tiktok_ads", attr.derive_channel({"ttclid": "y"}) == "tiktok_ads")
    check("utm_source=google + medium=cpc → google_ads",
          attr.derive_channel({"utm_source": "google", "utm_medium": "cpc"}) == "google_ads")
    check("utm_source=instagram + medium=paid_social → instagram_ads",
          attr.derive_channel({"utm_source": "instagram", "utm_medium": "paid_social"}) == "instagram_ads")
    check("utm_source=instagram organik → instagram (bukan ads)",
          attr.derive_channel({"utm_source": "instagram", "utm_medium": "social"}) == "instagram")
    check("utm_source=newsletter → email", attr.derive_channel({"utm_source": "newsletter"}) == "email")
    check("hanya referrer → referral", attr.derive_channel({"referrer": "https://blog.x.id"}) == "referral")
    check("kosong → direct", attr.derive_channel({}) == "direct")

    # --- 2. build_attribution ---
    print(f"\n{Y}[2] build_attribution (first + last touch){X}")
    b1 = attr.build_attribution({"first_touch": {"gclid": "g1"}, "last_touch": {}})
    check("first=google_ads, last kosong → channel fallback ke first (google_ads)", b1["channel"] == "google_ads", b1["channel"])
    check("first_touch & last_touch tersimpan",
          b1["attribution"]["first_touch"]["channel"] == "google_ads" and "last_touch" in b1["attribution"])
    b2 = attr.build_attribution({"first_touch": {}, "last_touch": {"fbclid": "f1", "utm_campaign": "promo-lebaran"}})
    check("last bermakna (fbclid) menang → meta_ads", b2["channel"] == "meta_ads", b2["channel"])
    check("utm_campaign terbawa", b2["utm_campaign"] == "promo-lebaran", b2["utm_campaign"])
    b3 = attr.build_attribution({}, fallback_source="website")
    check("payload kosong → channel = fallback (website)", b3["channel"] == "website", b3["channel"])
    b4 = attr.build_attribution({"utm_source": "google", "utm_medium": "cpc"})  # single-touch toleran
    check("single-touch (tanpa first/last) tetap terbaca → google_ads", b4["channel"] == "google_ads", b4["channel"])

    # --- 3. ads.create_ad_lead ---
    print(f"\n{Y}[3] ads.create_ad_lead (Lead Ads → lead ber-atribusi){X}")
    r_meta = await ads_service.create_ad_lead(db, "meta", {
        "full_name": "Budi Ads", "phone": "62811222333", "campaign": "promo-bali", "_test_tag": TEST_TAG})
    check("meta lead dibuat (status received)", r_meta.get("status") == "received", str(r_meta))
    check("channel = meta_ads", r_meta.get("channel") == "meta_ads", str(r_meta))
    lead_meta = await db.leads.find_one({"id": r_meta.get("id")}, {"_id": 0}) if r_meta.get("id") else None
    # tandai utk cleanup (create_ad_lead tak menambahkan _test_tag)
    if lead_meta:
        await db.leads.update_one({"id": lead_meta["id"]}, {"$set": {"_test_tag": TEST_TAG}})
    check("lead.source=ads & consent=True & attribution.channel=meta_ads",
          bool(lead_meta) and lead_meta["source"] == "ads" and lead_meta["marketing_consent"] is True
          and lead_meta["attribution"]["channel"] == "meta_ads", str(lead_meta and lead_meta.get("channel")))

    r_env = await ads_service.create_ad_lead(db, "meta", {
        "field_data": [{"name": "full_name", "values": ["Sinta Form"]},
                       {"name": "phone_number", "values": ["62822333444"]},
                       {"name": "campaign_name", "values": ["lead-form-juni"]}]})
    if r_env.get("id"):
        await db.leads.update_one({"id": r_env["id"]}, {"$set": {"_test_tag": TEST_TAG}})
    lead_env = await db.leads.find_one({"id": r_env.get("id")}, {"_id": 0}) if r_env.get("id") else None
    check("envelope Meta field_data ter-parse (nama+telepon)",
          bool(lead_env) and lead_env["customer_name"] == "Sinta Form" and lead_env["phone"] == "62822333444",
          str(lead_env and lead_env.get("customer_name")))
    r_ignore = await ads_service.create_ad_lead(db, "google", {"name": "Tanpa Kontak"})
    check("tanpa phone/email → ignored", r_ignore.get("status") == "ignored", str(r_ignore))

    # --- 4. channels_roi ---
    print(f"\n{Y}[4] channels_roi (CPL/CAC/ROAS per channel){X}")
    now = now_iso()
    seed_leads = [
        {"channel": "google_ads", "stage": "won", "value": 5_000_000},
        {"channel": "google_ads", "stage": "new", "value": 0},
        {"channel": "google_ads", "stage": "won", "value": 3_000_000},
        {"channel": "meta_ads", "stage": "new", "value": 0},
    ]
    for s in seed_leads:
        await db.leads.insert_one({
            "id": new_id("led"), "_test_tag": TEST_TAG, "customer_name": "ROI Test",
            "phone": "", "email": "", "source": "ads", "stage": s["stage"], "channel": s["channel"],
            "value": s["value"], "created_at": now, "last_activity_at": now,
        })
    rng = analytics.parse_range(days=30)
    spend_map = {"google_ads": 2_000_000, "meta_ads": 500_000}
    roi = await analytics.channels_roi(db, rng, spend_map)
    by_ch = {c["channel"]: c for c in roi["channels"]}
    g = by_ch.get("google_ads", {})
    # catatan: data seed lain mungkin menambah; kita uji minimal sesuai test leads kita
    check("google_ads punya >=2 lead & >=2 won (dari test)", g.get("leads", 0) >= 3 and g.get("won", 0) >= 2, str(g))
    check("google_ads cpl = spend/leads", g.get("cpl") == round(2_000_000 / g["leads"], 2) if g.get("leads") else False, str(g.get("cpl")))
    check("google_ads cac = spend/won", g.get("cac") == round(2_000_000 / g["won"], 2) if g.get("won") else False, str(g.get("cac")))
    check("google_ads roas = revenue/spend (>0)", (g.get("roas") or 0) > 0, str(g.get("roas")))
    check("ada label channel (Google Ads)", g.get("label") == "Google Ads", str(g.get("label")))

    # --- 5. segments filter ---
    print(f"\n{Y}[5] segments: kriteria channel & marketing_consent{X}")
    cnt_ch, members_ch = await segments.resolve(db, "lead", {"channel": "google_ads"})
    check("segment channel=google_ads menyaring lead", cnt_ch >= 3, f"count={cnt_ch}")
    ok_ch = True
    for m in members_ch[:5]:
        ld = await db.leads.find_one({"id": m["target_id"]}, {"_id": 0, "channel": 1})
        if not ld or ld.get("channel") != "google_ads":
            ok_ch = False
            break
    check("anggota segmen punya channel google_ads (cek via DB)", ok_ch)
    cnt_consent, _ = await segments.resolve(db, "lead", {"channel": "meta_ads", "marketing_consent": True})
    check("segment meta_ads + consent=True menyaring lead consent", cnt_consent >= 1, f"count={cnt_consent}")

    # --- 6. E6 Meta Cloud provider ---
    print(f"\n{Y}[6] E6: MetaCloudProvider & send_wa{X}")
    prov_empty = wa.MetaCloudProvider({"meta": {}, "price_per_message": 350})
    check("_ready() False tanpa kredensial", prov_empty._ready() is False)
    res_empty = await prov_empty.send_text("628111", "halo")
    check("send_text tanpa kredensial → failed (tanpa raise)", res_empty.get("status") == "failed", str(res_empty))
    check("pesan error menyebut kredensial", "Kredensial" in (res_empty.get("error") or ""), str(res_empty.get("error")))
    res_tpl = await prov_empty.send_template("628111", "lead_ack", {}, body="Halo terkirim")
    check("send_template(body) tanpa kredensial → failed graceful", res_tpl.get("status") == "failed", str(res_tpl))
    prov_ready = wa.MetaCloudProvider({"meta": {"phone_number_id": "123", "access_token": "tok"}})
    check("_ready() True bila phone_number_id+access_token ada", prov_ready._ready() is True)
    mock = wa.MockProvider({"price_per_message": 350})
    res_mock = await mock.send_text("628111", "halo")
    check("MockProvider send_text → sent", res_mock.get("status") == "sent", str(res_mock))
    res_wa = await wa.send_wa(db, TEST_PHONE, text="POC E6 test", source="test")
    check("send_wa (provider default mock) → sent", res_wa.get("status") == "sent", str(res_wa))

    # ---
    await cleanup(db)
    print(f"\n{'='*60}\n  HASIL: {G}{passed} PASS{X} / {R if failed else G}{failed} FAIL{X}\n{'='*60}\n")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
