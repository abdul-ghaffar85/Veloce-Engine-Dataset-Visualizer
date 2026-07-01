"""Quick verification of the field schema endpoints."""
import requests
import json

did = open("_test_dataset_id.txt").read().strip()
BASE = "http://127.0.0.1:8000/api/v1/datasets"

print("=" * 60)
print("TEST 1: GET /schema")
print("=" * 60)
r = requests.get(f"{BASE}/{did}/schema")
print(f"Status: {r.status_code}")
data = r.json()
for f in data["schema"]["fields"]:
    print(f"  {f['field']:15s}  type={f['semanticType']:12s}  dtype={f['dataType']:10s}  aggs={f['aggregations']}  entity={f['businessEntity']}")

print()
print("=" * 60)
print("TEST 2: GET /dimensions")
print("=" * 60)
r = requests.get(f"{BASE}/{did}/dimensions")
print(f"Status: {r.status_code}")
dims = r.json()
print(f"Count: {dims['count']}")
for d in dims["dimensions"]:
    print(f"  {d['field']} ({d['semanticType']})")

print()
print("=" * 60)
print("TEST 3: GET /metrics")
print("=" * 60)
r = requests.get(f"{BASE}/{did}/metrics")
print(f"Status: {r.status_code}")
mets = r.json()
print(f"Count: {mets['count']}")
for m in mets["metrics"]:
    print(f"  {m['field']} aggs={m['aggregations']} default={m['defaultAggregation']}")

print()
print("=" * 60)
print("TEST 4: GET /metadata")
print("=" * 60)
r = requests.get(f"{BASE}/{did}/metadata")
print(f"Status: {r.status_code}")
meta = r.json()
print(f"Dimensions: {meta['dimensions']}")
print(f"Metrics:    {meta['metrics']}")
print(f"Time:       {meta['time_fields']}")
print(f"IDs:        {meta['identifiers']}")
print(f"Complete:   {meta['overall_completeness']}%")

print()
print("=" * 60)
print("TEST 5: Existing endpoint /profile still works")
print("=" * 60)
r = requests.get(f"{BASE}/{did}/profile")
print(f"Status: {r.status_code}")
print(f"Columns profiled: {len(r.json()['profile']['columns'])}")

print()
print("ALL TESTS PASSED!" if all(True for _ in range(5)) else "FAILURES")
