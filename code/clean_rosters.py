"""Convert the four VA OGC roster downloads (HTML tables served as .xls)
into clean CSVs in data/ogc-rosters/.

Usage: python3 code/clean_rosters.py <dir-with-raw-files>
Expects: attorneyexcellist.xls caexcellist.xls orgsexcellist.xls (raw downloads)
"""
import sys
import pandas as pd
from pathlib import Path

def clean(src: Path, out: Path):
    dfs = pd.read_html(src, header=0)
    df = max(dfs, key=len)
    df.columns = [str(c).strip() for c in df.columns]
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].astype(str).str.lstrip("'").replace("nan", "")
    df.to_csv(out, index=False)
    print(f"{src.name}: {len(df)} rows -> {out}")

def main(raw_dir):
    raw = Path(raw_dir)
    outdir = Path("data/ogc-rosters")
    outdir.mkdir(parents=True, exist_ok=True)
    for name in ["attorneyexcellist", "caexcellist", "orgsexcellist"]:
        clean(raw / f"{name}.xls", outdir / f"{name}.csv")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "raw")
