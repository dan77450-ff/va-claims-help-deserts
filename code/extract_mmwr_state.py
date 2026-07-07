"""Extract state-level compensation rating-bundle backlog from an MMWR workbook.

Data sheet decoding (reverse-engineered from 'Rating Bundle - State' SUMIFS):
  MT=6  -> state-view rating bundle (by claimant address)
  CAT: 0=all benefit types, 11=compensation, 12=pension, 13=other
  LOC: 2-letter state code (also '100'=national, district ids)
  INV=# pending, BL=# pending >125 days (backlog), ADP=avg days pending

Usage: python3 code/extract_mmwr_state.py data/MMWR-07-04-2026.xlsx
Output: data/state_backlog.csv
"""
import sys
import csv
import openpyxl

STATES = set("AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY PR".split())

def main(path):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    date = str(wb["DT"]["A2"].value)[:10]
    rows = []
    for r in wb["Data"].iter_rows(min_row=2, values_only=True):
        mt, cat, loc, _, inv, bl, adp = r[0], r[1], r[2], r[3], r[4], r[5], r[6]
        if str(mt) == "6" and str(cat) == "11" and isinstance(loc, str) and loc in STATES:
            inv = int(inv or 0)
            bl = int(bl or 0)
            rows.append({"state": loc, "pending": inv, "backlog_gt125d": bl,
                         "pct_backlog": round(bl / inv, 4) if inv else None,
                         "avg_days_pending": adp, "report_date": date})
    rows.sort(key=lambda x: -x["pending"])
    out = "data/state_backlog.csv"
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} states -> {out} (report {date})")
    print("top5:", [(r['state'], r['pending'], r['pct_backlog']) for r in rows[:5]])

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/MMWR-07-04-2026.xlsx")
