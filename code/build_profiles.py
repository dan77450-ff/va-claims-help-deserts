"""Build county_profiles.json — click-panel enrichment for the desert map.

Per county FIPS:
  nearest_mi / nearest_loc : distance (mi) from county centroid to nearest
                             accredited rep, and that rep's city/state
  cp_total / cp_per_vet    : FY24 GDX Compensation & Pension dollars, per veteran
  state_cp_per_vet         : state benchmark
  cds                      : congressional districts overlapping the county (118th)

Inputs (data/): 2023_Gaz_counties_national.txt, GDX_FY24.xlsx,
  tab20_cd11820_county20_natl.txt, ogc-rosters/*.csv, county_rep_density.csv,
  tab20_zcta520_county20_natl.txt, ZIP-to-PlanningRegion.xlsx
"""
import json
import math
import pandas as pd
import zipcodes
from build_density import load_reps, county_key

DATA = "data"

ABBR = {"Alabama":"AL","Alaska":"AK","Arizona":"AZ","Arkansas":"AR","California":"CA","Colorado":"CO","Connecticut":"CT","Delaware":"DE","District of Columbia":"DC","Florida":"FL","Georgia":"GA","Hawaii":"HI","Idaho":"ID","Illinois":"IL","Indiana":"IN","Iowa":"IA","Kansas":"KS","Kentucky":"KY","Louisiana":"LA","Maine":"ME","Maryland":"MD","Massachusetts":"MA","Michigan":"MI","Minnesota":"MN","Mississippi":"MS","Missouri":"MO","Montana":"MT","Nebraska":"NE","Nevada":"NV","New Hampshire":"NH","New Jersey":"NJ","New Mexico":"NM","New York":"NY","North Carolina":"NC","North Dakota":"ND","Ohio":"OH","Oklahoma":"OK","Oregon":"OR","Pennsylvania":"PA","Puerto Rico":"PR","Rhode Island":"RI","South Carolina":"SC","South Dakota":"SD","Tennessee":"TN","Texas":"TX","Utah":"UT","Vermont":"VT","Virginia":"VA","Washington":"WA","West Virginia":"WV","Wisconsin":"WI","Wyoming":"WY"}
ABBR_BY_NAME = ABBR

def rep_points():
    reps = load_reps()
    pts = []
    cache = {}
    for z in reps["zip5"]:
        if not isinstance(z, str) or not z:
            continue
        if z not in cache:
            m = zipcodes.matching(z)
            cache[z] = (float(m[0]["lat"]), float(m[0]["long"]),
                        f'{m[0]["city"]}, {m[0]["state"]}') if m else None
        if cache[z]:
            pts.append(cache[z])
    return pts

def load_centroids():
    g = pd.read_csv(f"{DATA}/2023_Gaz_counties_national.txt", sep="\t", dtype=str)
    g.columns = [c.strip() for c in g.columns]
    return {r["GEOID"]: (float(r["INTPTLAT"]), float(r["INTPTLONG"]), r["NAME"].strip())
            for _, r in g.iterrows()}

def haversine_mi(lat1, lon1, lat2, lon2):
    r = 3958.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))

def nearest(lat, lon, pts):
    best, loc = None, None
    for plat, plon, ploc in pts:
        d = haversine_mi(lat, lon, plat, plon)
        if best is None or d < best:
            best, loc = d, ploc
    return best, loc

def load_gdx():
    """County Direct Exp sheet -> {(county_key): cp_dollars}; also state totals."""
    df = pd.read_excel(f"{DATA}/GDX_FY24.xlsx", sheet_name="County Direct Exp",
                       skiprows=2, usecols="B:E", dtype=str)
    df.columns = ["state", "county", "total_direct", "cp"]
    df = df.dropna(subset=["state", "county"])
    df["cp"] = pd.to_numeric(df["cp"], errors="coerce")
    df = df.dropna(subset=["cp"])
    out, state_tot = {}, {}
    for _, r in df.iterrows():
        usps = ABBR_BY_NAME.get(str(r["state"]).strip())
        if not usps:
            continue
        k = county_key(str(r["county"]), usps)
        if k:
            out[k] = out.get(k, 0) + float(r["cp"])
        state_tot[usps] = state_tot.get(usps, 0) + float(r["cp"])
    return out, state_tot

def load_cds():
    cd = pd.read_csv(f"{DATA}/tab20_cd11820_county20_natl.txt", sep="|", dtype=str,
                     usecols=["GEOID_CD118_20", "GEOID_COUNTY_20"])
    cd = cd.dropna()
    m = {}
    for _, r in cd.iterrows():
        g = r["GEOID_CD118_20"]
        if len(g) != 4:
            continue
        m.setdefault(r["GEOID_COUNTY_20"], set()).add(g)
    return m

FIPS_TO_USPS = {}  # filled in main from density csv

def main():
    dens = pd.read_csv(f"{DATA}/county_rep_density.csv", dtype={"FIPS": str})
    dens["FIPS"] = dens["FIPS"].str.zfill(5)
    cents = load_centroids()
    pts = rep_points()
    gdx, gdx_state = load_gdx()
    cds = load_cds()
    # veterans per state for benchmark
    st_vets = dens.groupby(dens["FIPS"].str[:2])["Veterans"].sum().to_dict()
    st_usps = {}
    for _, r in dens.iterrows():
        st_usps[r["FIPS"][:2]] = ABBR.get(r["State"], "")

    profiles = {}
    for _, r in dens.iterrows():
        f = r["FIPS"]
        prof = {}
        # nearest help (only for counties with zero reps; else 0)
        c = cents.get(f)
        if r["reps"] == 0 and c:
            d, loc = nearest(c[0], c[1], pts)
            if d is not None:
                prof["nearest_mi"] = round(d)
                prof["nearest_loc"] = loc
        # GDX
        usps = ABBR.get(r["State"], "")
        k = county_key(str(r["county"]).rsplit(", ", 1)[0], usps)
        cp = gdx.get(k)
        if cp and r["Veterans"]:
            prof["cp_per_vet"] = round(cp / r["Veterans"])
            sv = st_vets.get(f[:2])
            scp = gdx_state.get(usps)
            if sv and scp:
                prof["st_cp_per_vet"] = round(scp / sv)
        # congressional districts
        dl = sorted(cds.get(f, []))
        if dl:
            prof["cds"] = [f"{st_usps.get(g[:2], g[:2])}-{'AL' if g[2:] in ('00','98') else g[2:]}"
                           for g in dl]
        profiles[f] = prof

    with open(f"{DATA}/county_profiles.json", "w") as fh:
        json.dump(profiles, fh, separators=(",", ":"))
    n_near = sum(1 for p in profiles.values() if "nearest_mi" in p)
    n_cp = sum(1 for p in profiles.values() if "cp_per_vet" in p)
    n_cd = sum(1 for p in profiles.values() if "cds" in p)
    print(f"profiles: {len(profiles)} | nearest computed: {n_near} | cp: {n_cp} | cds: {n_cd}")
    far = sorted(((p["nearest_mi"], f) for f, p in profiles.items() if "nearest_mi" in p), reverse=True)[:5]
    print("farthest-from-help deserts:", far)

if __name__ == "__main__":
    main()
