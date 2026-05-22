#!/usr/bin/env python3
"""Comprehensive TradePath AI API test suite."""
import json
import subprocess
import sys

import uuid as _uuid
BASE = "http://127.0.0.1:8037/api/v1"
PASS = 0
FAIL = 0
_RUN_ID = _uuid.uuid4().hex[:8]

def curl(*args):
    cmd = ["curl", "-s"] + list(args)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    return r.stdout

def curl_code(*args):
    cmd = ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}"] + list(args)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    return r.stdout.strip()

def check(label, code, expected):
    global PASS, FAIL
    import re
    if re.match(f"^({expected})$", str(code)):
        print(f"  PASS  {label} ({code})")
        PASS += 1
    else:
        print(f"  FAIL  {label} ({code}, expected {expected})")
        FAIL += 1

def jget(s, key, default=""):
    try:
        return json.loads(s).get(key, default)
    except:
        return default

print("=" * 60)
print("  TradePath AI — API Test Suite")
print("=" * 60)

# AUTH
print("\n[AUTH]")
_EMAIL = f"audit_{_RUN_ID}@tradepath.ai"
_PASS = "AuditPass1!"

code = curl_code("-X", "POST", f"{BASE}/auth/register",
    "-H", "Content-Type: application/json",
    "-d", json.dumps({"email":_EMAIL,"password":_PASS,"full_name":"Audit User","role":"customs_broker"}))
check("POST /auth/register", code, "201")

code = curl_code("-X", "POST", f"{BASE}/auth/register",
    "-H", "Content-Type: application/json",
    "-d", json.dumps({"email":_EMAIL,"password":_PASS,"full_name":"Dup","role":"customs_broker"}))
check("POST /auth/register duplicate -> 400|409", code, "400|409")

login_resp = curl("-X", "POST", f"{BASE}/auth/login",
    "-H", "Content-Type: application/x-www-form-urlencoded",
    "-d", f"username={_EMAIL}&password={_PASS}")
token = jget(login_resp, "access_token")
AUTH = ["-H", f"Authorization: Bearer {token}"]

code = curl_code(f"{BASE}/auth/me", *AUTH)
check("GET /auth/me", code, "200")
code = curl_code(f"{BASE}/shipments")
check("GET /shipments (unauth) -> 401", code, "401|403")

# SHIPMENTS
print("\n[SHIPMENTS]")
ship_resp = curl("-X", "POST", f"{BASE}/shipments",
    *AUTH, "-H", "Content-Type: application/json",
    "-d", json.dumps({
        "origin_country":"US","destination_country":"DE",
        "transport_mode":"sea","incoterms":"CIF",
        "exporter_name":"Acme Corp","importer_name":"Euro GmbH",
        "total_value_usd":50000,"total_weight_kg":1200
    }))
ship_id = jget(ship_resp, "id")
ship_ref = jget(ship_resp, "reference_number")
if ship_id:
    print(f"  PASS  POST /shipments (ref={ship_ref})")
    PASS += 1
else:
    print(f"  FAIL  POST /shipments: {ship_resp[:200]}")
    FAIL += 1

code = curl_code(f"{BASE}/shipments", *AUTH)
check("GET /shipments list", code, "200")
code = curl_code(f"{BASE}/shipments/{ship_id}", *AUTH)
check("GET /shipments/:id", code, "200")
code = curl_code("-X", "PATCH", f"{BASE}/shipments/{ship_id}/status?new_status=screening", *AUTH)
check("PATCH /shipments/:id/status", code, "200")
code = curl_code(f"{BASE}/shipments/00000000-0000-0000-0000-000000000000", *AUTH)
check("GET /shipments (not found) -> 404", code, "404")

ship2_resp = curl("-X", "POST", f"{BASE}/shipments",
    *AUTH, "-H", "Content-Type: application/json",
    "-d", json.dumps({"origin_country":"CN","destination_country":"US","transport_mode":"air","exporter_name":"Beijing Co","total_value_usd":12000}))
ship2_id = jget(ship2_resp, "id")

# CLASSIFICATION
print("\n[CLASSIFICATION]")
cls_resp = curl("-X", "POST", f"{BASE}/classification",
    *AUTH, "-H", "Content-Type: application/json",
    "-d", json.dumps({"product_description":"Industrial hydraulic pump","materials":"cast iron","intended_use":"manufacturing"}))
cls_id = jget(cls_resp, "id")
cls_hs = jget(cls_resp, "hs_code_6digit", "?")
if cls_id:
    print(f"  PASS  POST /classification (hs={cls_hs})")
    PASS += 1
else:
    print(f"  FAIL  POST /classification: {cls_resp[:200]}")
    FAIL += 1

itar_resp = curl("-X", "POST", f"{BASE}/classification",
    *AUTH, "-H", "Content-Type: application/json",
    "-d", json.dumps({"product_description":"Military encryption device for defense cryptographic communications","materials":"silicon","intended_use":"defense"}))
itar_flag = jget(itar_resp, "is_itar_ear_flagged", "?")
if itar_flag == "true":
    print(f"  PASS  ITAR/EAR detection (flagged=true)")
    PASS += 1
else:
    print(f"  FAIL  ITAR not detected: flag={itar_flag}")
    FAIL += 1

code = curl_code(f"{BASE}/classification/{cls_id}", *AUTH)
check("GET /classification/:id", code, "200")
code = curl_code("-X", "POST", f"{BASE}/classification/{cls_id}/confirm", *AUTH)
check("POST /classification/:id/confirm", code, "200")

# SCREENING
print("\n[SCREENING]")
scr_resp = curl("-X", "POST", f"{BASE}/screening",
    *AUTH, "-H", "Content-Type: application/json",
    "-d", json.dumps({"shipment_id":ship_id,"party_name":"Acme Trading LLC","party_type":"consignee","party_country":"DE"}))
scr_id = jget(scr_resp, "id")
scr_result = jget(scr_resp, "overall_result", "?")
if scr_id:
    print(f"  PASS  POST /screening (result={scr_result})")
    PASS += 1
else:
    print(f"  FAIL  POST /screening: {scr_resp[:200]}")
    FAIL += 1

scr2_resp = curl("-X", "POST", f"{BASE}/screening",
    *AUTH, "-H", "Content-Type: application/json",
    "-d", json.dumps({"shipment_id":ship2_id,"party_name":"Huawei Technologies","party_type":"manufacturer","party_country":"CN"}))
scr2_result = jget(scr2_resp, "overall_result", "?")
print(f"  INFO  Huawei Technologies screening: {scr2_result}")

code = curl_code("-X", "POST", f"{BASE}/screening/{scr_id}/review",
    *AUTH, "-H", "Content-Type: application/json",
    "-d", json.dumps({"decision":"approved","notes":"Cleared","apply_legal_hold":False,"whitelist":False}))
check("POST /screening/:id/review", code, "200")
code = curl_code(f"{BASE}/screening/shipment/{ship_id}", *AUTH)
check("GET /screening/shipment/:id", code, "200")

# DECLARATIONS
print("\n[DECLARATIONS]")
decl_resp = curl("-X", "POST", f"{BASE}/declarations",
    *AUTH, "-H", "Content-Type: application/json",
    "-d", json.dumps({"shipment_id":ship_id,"declaration_type":"cbp_entry_01","declared_value_usd":50000,"fob_value_usd":48000,"total_duty_usd":2400}))
decl_id = jget(decl_resp, "id")
if decl_id:
    print(f"  PASS  POST /declarations")
    PASS += 1
else:
    print(f"  FAIL  POST /declarations: {decl_resp[:200]}")
    FAIL += 1

code = curl_code(f"{BASE}/declarations/shipment/{ship_id}", *AUTH)
check("GET /declarations/shipment/:id", code, "200")
code = curl_code("-X", "POST", f"{BASE}/declarations/{decl_id}/validate", *AUTH)
check("POST /declarations/:id/validate", code, "200")
code = curl_code("-X", "POST", f"{BASE}/declarations/{decl_id}/submit", *AUTH)
check("POST /declarations/:id/submit", code, "200")

# COO
print("\n[CERTIFICATE OF ORIGIN]")
coo_resp = curl("-X", "POST", f"{BASE}/coo",
    *AUTH, "-H", "Content-Type: application/json",
    "-d", json.dumps({"shipment_id":ship_id,"coo_format":"usmca","origin_criterion":"regional_value_content","exporter_name":"Acme Corp","importer_name":"Euro GmbH","country_of_origin":"US"}))
coo_id = jget(coo_resp, "id")
if coo_id:
    print(f"  PASS  POST /coo")
    PASS += 1
else:
    print(f"  FAIL  POST /coo: {coo_resp[:200]}")
    FAIL += 1
code = curl_code(f"{BASE}/coo/shipment/{ship_id}", *AUTH)
check("GET /coo/shipment/:id", code, "200")

# FTA
print("\n[FTA ANALYSIS]")
fta_resp = curl("-X", "POST", f"{BASE}/fta",
    *AUTH, "-H", "Content-Type: application/json",
    "-d", json.dumps({"shipment_id":ship_id,"hs_code_6digit":"841330","product_description":"Industrial hydraulic pump","declared_value_usd":50000}))
fta_id = jget(fta_resp, "id")
if fta_id:
    print(f"  PASS  POST /fta")
    PASS += 1
else:
    print(f"  FAIL  POST /fta: {fta_resp[:200]}")
    FAIL += 1
code = curl_code(f"{BASE}/fta/shipment/{ship_id}", *AUTH)
check("GET /fta/shipment/:id", code, "200")

# RESTRICTIONS
print("\n[IMPORT RESTRICTIONS]")
rst_resp = curl("-X", "POST", f"{BASE}/restrictions/check",
    *AUTH, "-H", "Content-Type: application/json",
    "-d", json.dumps({"origin_country":"CN","destination_country":"US","hs_code_6digit":"841330"}))
rst_status = jget(rst_resp, "status", "ERR")
if rst_status != "ERR":
    print(f"  PASS  POST /restrictions/check CN->US ({rst_status})")
    PASS += 1
else:
    print(f"  FAIL  POST /restrictions/check: {rst_resp[:200]}")
    FAIL += 1

kp_resp = curl("-X", "POST", f"{BASE}/restrictions/check",
    *AUTH, "-H", "Content-Type: application/json",
    "-d", json.dumps({"origin_country":"KP","destination_country":"US","hs_code_6digit":"841330"}))
kp_status = jget(kp_resp, "status", "?")
if kp_status.upper() == "PROHIBITED":
    print(f"  PASS  POST /restrictions/check KP->US (prohibited)")
    PASS += 1
else:
    print(f"  FAIL  KP->US not prohibited: status={kp_status}")
    FAIL += 1

iran_resp = curl("-X", "POST", f"{BASE}/restrictions/check",
    *AUTH, "-H", "Content-Type: application/json",
    "-d", json.dumps({"origin_country":"IR","destination_country":"US","hs_code_6digit":"841330"}))
iran_status = jget(iran_resp, "status", "?")
print(f"  INFO  IR->US restriction: {iran_status}")

# ANALYTICS
print("\n[ANALYTICS]")
dash_resp = curl(f"{BASE}/analytics/dashboard", *AUTH)
try:
    dash = json.loads(dash_resp)
    if "shipments" in dash and "screening" in dash:
        ship_total = dash.get("shipments", {}).get("total", 0)
        print(f"  PASS  GET /analytics/dashboard (total_shipments={ship_total})")
        PASS += 1
    else:
        print(f"  FAIL  GET /analytics/dashboard: {dash_resp[:200]}")
        FAIL += 1
except Exception as e:
    print(f"  FAIL  GET /analytics/dashboard: {e}")
    FAIL += 1

# SUMMARY
print()
print("=" * 60)
print(f"  TOTAL: {PASS} PASSED / {FAIL} FAILED")
print(f"  PASS RATE: {PASS/(PASS+FAIL)*100:.0f}%")
print("=" * 60)
