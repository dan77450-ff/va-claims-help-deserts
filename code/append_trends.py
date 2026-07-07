"""Append today's snapshot to the trend series (docs/trends.csv + docs/trends-summary.csv).

trends.csv: wide — FIPS, county, then one column per roster-snapshot date (reps count).
trends-summary.csv: date, total_reps, desert_counties (0 reps & >=1,000 vets), desert_veterans.
Idempotent: re-running on the same date overwrites that date's column/row.
"""
import pandas as pd
import os

d = pd.read_csv("data/county_rep_density.csv", dtype={"FIPS": str})
d["FIPS"] = d["FIPS"].str.zfill(5)
date = open("data/roster-snapshot-date.txt").read().strip()

# --- per-county wide series ---
path = "docs/trends.csv"
if os.path.exists(path):
    t = pd.read_csv(path, dtype={"FIPS": str})
    t["FIPS"] = t["FIPS"].str.zfill(5)
else:
    t = d[["FIPS", "county"]].copy()
cur = d.set_index("FIPS")["reps"]
t[date] = t["FIPS"].map(cur)
# keep county names fresh, add any new counties
t = t.set_index("FIPS").combine_first(d.set_index("FIPS")[["county"]]).reset_index()
cols = ["FIPS", "county"] + sorted([c for c in t.columns if c not in ("FIPS", "county")])
t = t[cols]
t.to_csv(path, index=False)

# --- national summary ---
spath = "docs/trends-summary.csv"
deserts = d[(d.reps == 0) & (d.Veterans >= 1000)]
row = {"date": date, "total_reps": int(d["reps"].sum()),
       "desert_counties": len(deserts), "desert_veterans": int(deserts["Veterans"].sum())}
if os.path.exists(spath):
    s = pd.read_csv(spath, dtype={"date": str})
    s = s[s["date"] != date]
    s = pd.concat([s, pd.DataFrame([row])], ignore_index=True).sort_values("date")
else:
    s = pd.DataFrame([row])
s.to_csv(spath, index=False)
print(f"trends: {len(t)} counties x {len(cols)-2} dates | summary: {row}")
