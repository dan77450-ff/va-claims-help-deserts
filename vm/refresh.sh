#!/usr/bin/env bash
# Weekly refresh: download fresh rosters + latest MMWR, rebuild dataset + map, push.
# Run from anywhere; operates on the repo it lives in. Safe to re-run (only pushes on change).
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CACHE_DIR="$HOME/.cache/va-deserts"      # static inputs cached here (VetPop, crosswalks)
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
cd "$REPO_DIR"
git pull --ff-only

mkdir -p "$CACHE_DIR/raw" data/ogc-rosters

log(){ echo "[$(date -u +%FT%TZ)] $*"; }

# ---------- 1. static inputs (download once, cache) ----------
fetch_cached(){ # url, dest
  [ -s "$2" ] && return 0
  log "fetching static input: $1"
  curl -fsSL -A "$UA" -o "$2" "$1"
}
fetch_cached "https://www.data.va.gov/api/views/jrjd-qghv/rows.csv?accessType=DOWNLOAD" \
             "$CACHE_DIR/VetPop2023_County_Data__9L.csv"
fetch_cached "https://www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/tab20_zcta520_county20_natl.txt" \
             "$CACHE_DIR/tab20_zcta520_county20_natl.txt"
fetch_cached "https://raw.githubusercontent.com/CT-Data-Collaborative/zip-to-planningregion/main/ZIP-to-PlanningRegion.xlsx" \
             "$CACHE_DIR/ZIP-to-PlanningRegion.xlsx"
fetch_cached "https://www.va.gov/VETDATA/docs/GDX/GDX_FY24.xlsx" "$CACHE_DIR/GDX_FY24.xlsx"
fetch_cached "https://www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/tab20_cd11820_county20_natl.txt" \
             "$CACHE_DIR/tab20_cd11820_county20_natl.txt"
if [ ! -s "$CACHE_DIR/2023_Gaz_counties_national.txt" ]; then
  fetch_cached "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2023_Gazetteer/2023_Gaz_counties_national.zip" \
               "$CACHE_DIR/gaz.zip"
  python3 -c "import zipfile;zipfile.ZipFile('$CACHE_DIR/gaz.zip').extractall('$CACHE_DIR')"
fi
for f in VetPop2023_County_Data__9L.csv tab20_zcta520_county20_natl.txt ZIP-to-PlanningRegion.xlsx \
         GDX_FY24.xlsx tab20_cd11820_county20_natl.txt 2023_Gaz_counties_national.txt; do
  cp -n "$CACHE_DIR/$f" data/ 2>/dev/null || true
done

# ---------- 2. fresh rosters ----------
for f in attorneyexcellist caexcellist orgsexcellist; do
  log "downloading roster: $f"
  curl -fsSL -A "$UA" -o "$CACHE_DIR/raw/$f.xls" \
    "https://www.va.gov/ogc/apps/accreditation/$f.asp"
done
python3 code/clean_rosters.py "$CACHE_DIR/raw"
date +%F > data/roster-snapshot-date.txt

# archive today's roster snapshot (valuable time series nobody else keeps)
SNAP="snapshots/$(date +%F)"
mkdir -p "$SNAP"
cp data/ogc-rosters/*.csv "$SNAP/"

# ---------- 3. latest MMWR (posted Mondays, dated the preceding Saturday) ----------
MMWR=""
for i in $(seq 0 13); do
  D=$(date -d "-$i days" +%m-%d-%Y); Y=$(date -d "-$i days" +%Y)
  for ext in xlsx xlsm; do
    URL="https://www.benefits.va.gov/REPORTS/mmwr/$Y/MMWR-$D.$ext"
    if curl -fsSL -A "$UA" -o "$CACHE_DIR/raw/mmwr.$ext" "$URL" 2>/dev/null \
       && [ "$(head -c2 "$CACHE_DIR/raw/mmwr.$ext")" = "PK" ]; then
      # magic-byte check: va.gov serves HTML error pages with HTTP 200
      MMWR="$CACHE_DIR/raw/mmwr.$ext"; log "got MMWR-$D.$ext"; break 2
    fi
  done
done
[ -n "$MMWR" ] || { log "ERROR: no MMWR found in last 14 days"; exit 1; }
python3 code/extract_mmwr_state.py "$MMWR"

# ---------- 4. rebuild ----------
python3 code/build_density.py
python3 code/build_profiles.py
python3 code/append_trends.py
python3 code/build_map.py   # writes docs/index.html directly

# ---------- 5. commit & push only if something changed ----------
git add -A
if git diff --cached --quiet; then
  log "no changes; done."
else
  git commit -m "auto-refresh: roster $(cat data/roster-snapshot-date.txt), MMWR $(python3 -c "import csv;print(next(csv.DictReader(open('data/state_backlog.csv')))['report_date'])")"
  git push
  log "pushed."
fi
