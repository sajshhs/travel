"""Cleanup FE-test import data + extra pre_import archives (iteration 115)."""
import os
import sys

import requests
from dotenv import dotenv_values
from pymongo import MongoClient

be = dotenv_values("/app/backend/.env")
fe = dotenv_values("/app/frontend/.env")
API = fe["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
cli = MongoClient(be["MONGO_URL"])
db = cli[be["DB_NAME"]]
rx = {"$regex": "^TEST_FE115"}
print("customers", db.customers.delete_many({"name": rx}).deleted_count)
print("vehicles", db.vehicles.delete_many({"name": rx}).deleted_count)
print("drivers", db.drivers.delete_many({"name": rx}).deleted_count)
print("partners", db.partners.delete_many({"name": rx}).deleted_count)
print("addons", db.addons.delete_many({"label": rx}).deleted_count)
print("cities", db.cities.delete_many({"name": {"$regex": "^Kota FE [XY] 115$"}}).deleted_count)

s = requests.Session()
tok = requests.post(f"{API}/auth/login", json={"email": "owner@demo.local", "password": "demo12345"}, timeout=60).json()
s.headers.update({"Authorization": f"Bearer {tok.get('token') or tok.get('access_token')}"})
ov = s.get(f"{API}/data/overview", timeout=180).json()
removed = 0
for b in [x for x in ov["backups"] if x["kind"] == "pre_import"]:
    if s.delete(f"{API}/data/backups/{b['id']}", timeout=120).status_code == 200:
        removed += 1
print("pre_import archives removed:", removed)
print("remaining archives:", len(s.get(f"{API}/data/overview", timeout=180).json()["backups"]))
cli.close()
