"""Build county-level accredited-rep density (reps per 1,000 veterans).

Inputs (relative to dataset-projects/):
  data/ogc-rosters/{attorneyexcellist,caexcellist,orgsexcellist}.csv  (snapshot 2026-07-07)
  data/VetPop2023_County_Data__9L.csv
Output:
  data/county_rep_density.csv

Method notes:
- Reps deduped by Registration Num within each file; a person accredited as both
  attorney and agent counts once (dedupe across files by RegNum).
- Zip -> county via `zipcodes` package (primary county per zip; many-to-many
  zips are assigned to their primary county — v1 simplification, upgrade path:
  Census ZCTA-county relationship file).
- County name+state -> FIPS lookup built from the VetPop file itself.
- Veteran population: VetPop2023 projection for FY2026 (09/30/2026), all ages/sexes.
"""
import pandas as pd
import zipcodes
import re

DATA = "data"

def zip5(z):
    z = re.sub(r"\D", "", str(z))[:5]
    return z.zfill(5) if 3 <= len(z) <= 5 and z != "" else None

def load_reps():
    frames = []
    a = pd.read_csv(f"{DATA}/ogc-rosters/attorneyexcellist.csv", dtype=str)
    a = a.rename(columns={"Zip": "zip", "State": "src_state"})
    a["kind"] = "attorney"
    frames.append(a[["Registration Num", "zip", "src_state", "kind"]])
    c = pd.read_csv(f"{DATA}/ogc-rosters/caexcellist.csv", dtype=str)
    c = c.rename(columns={"Zip": "zip", "State": "src_state"})
    c["kind"] = "agent"
    frames.append(c[["Registration Num", "zip", "src_state", "kind"]])
    o = pd.read_csv(f"{DATA}/ogc-rosters/orgsexcellist.csv", dtype=str)
    o = o.rename(columns={"Rep Zip": "zip", "Rep State": "src_state"})
    org = o["Organization Name"].fillna("")
    o["kind"] = "vso_rep"
    o.loc[org.str.contains(r"Department of|Veterans Commission|Executive Office of Veterans|Division of Veterans", case=False, regex=True), "kind"] = "state_vso"
    o.loc[org.str.contains("County Veterans Service Officers", case=False), "kind"] = "cvso"
    # one row per rep; reps appear once per org — dedupe keeping highest-priority kind
    # (cvso > state_vso > vso_rep) so dual-accredited CVSOs are classified as CVSOs
    prio = {"cvso": 0, "state_vso": 1, "vso_rep": 2}
    o["_p"] = o["kind"].map(prio)
    o = o.sort_values("_p").drop_duplicates(subset=["Registration Num"]).drop(columns="_p")
    frames.append(o[["Registration Num", "zip", "src_state", "kind"]])
    reps = pd.concat(frames, ignore_index=True)
    # cross-file dedupe: keep first occurrence of a RegNum (attorney > agent > vso order irrelevant for count)
    reps = reps.drop_duplicates(subset=["Registration Num"])
    reps["zip5"] = reps["zip"].map(zip5)
    return reps

def load_zcta_crosswalk():
    """ZCTA -> primary county FIPS (largest land-area overlap). Census 2020 relationship file.
    CT zips overridden with 2022 planning-region county-equivalents (CTData crosswalk)."""
    xw = pd.read_csv(f"{DATA}/tab20_zcta520_county20_natl.txt", sep="|", dtype=str,
                     usecols=["GEOID_ZCTA5_20", "GEOID_COUNTY_20", "AREALAND_PART"])
    xw["AREALAND_PART"] = pd.to_numeric(xw["AREALAND_PART"], errors="coerce").fillna(0)
    xw = xw.dropna(subset=["GEOID_ZCTA5_20", "GEOID_COUNTY_20"])
    xw = xw.sort_values("AREALAND_PART", ascending=False).drop_duplicates("GEOID_ZCTA5_20")
    m = dict(zip(xw["GEOID_ZCTA5_20"], xw["GEOID_COUNTY_20"]))
    ct = pd.read_excel(f"{DATA}/ZIP-to-PlanningRegion.xlsx", dtype=str)
    for z, g in zip(ct["ZCTA_5"], ct["PlanningRegion_GeoID"]):
        m[z.zfill(5)] = g.zfill(5)
    return m

def zip_to_county(reps):
    zcta = load_zcta_crosswalk()
    cache = {}
    fips_list, counties, states = [], [], []
    for z in reps["zip5"]:
        if not isinstance(z, str) or not z:  # None / pd.NA (pandas>=3) / empty
            fips_list.append(None); counties.append(None); states.append(None); continue
        f = zcta.get(z)
        # fallback for non-ZCTA zips (PO boxes etc.): name-based via zipcodes pkg
        if z not in cache:
            m = zipcodes.matching(z)
            cache[z] = (m[0].get("county"), m[0].get("state")) if m else (None, None)
        c, s = cache[z]
        fips_list.append(f); counties.append(c); states.append(s)
    reps["fips"] = fips_list
    reps["county_name"] = counties
    reps["state"] = states
    return reps

def county_key(name, state):
    if not isinstance(name, str) or not isinstance(state, str):
        return None
    n = re.sub(r"\s+(County|Parish|Borough|Census Area|Municipality|city|City and Borough)$", "", name.strip(), flags=re.I)
    n = n.lower()
    n = re.sub(r"^saint\b", "st", n)   # Saint Louis -> st louis
    n = re.sub(r"^st\.", "st", n)      # St. Louis -> st louis
    n = re.sub(r"[^a-z]", "", n)       # de kalb/DeKalb -> dekalb; drop spaces/punct
    return f"{n}|{state.upper()}"

def load_vetpop():
    vp = pd.read_csv(f"{DATA}/VetPop2023_County_Data__9L.csv", dtype=str)
    vp["Veterans"] = pd.to_numeric(vp["Veterans"], errors="coerce")
    vp = vp[vp["Date"].str.startswith("09/30/2026")]
    tot = vp.groupby(["FIPS", "County, State", "State"], as_index=False)["Veterans"].sum()
    # key: "Autauga, AL" -> autauga|AL ; territories have no ", XX" suffix
    VP_SPECIAL = {"Puerto Rico, PR": "puertorico|PR", "Guam": "guam|GU",
                  "Virgin Islands": "virginislands|VI", "American Samoa": "americansamoa|AS",
                  "Northern Mariana Islands": "northernmarianaislands|MP"}
    parts = tot["County, State"].str.rsplit(", ", n=1, expand=True)
    tot["key"] = [VP_SPECIAL.get(full) or county_key(a, b)
                  for full, a, b in zip(tot["County, State"], parts[0], parts[1])]
    return tot

TERRITORY_KEYS = {"PR": "puertorico|PR", "GU": "guam|GU", "VI": "virginislands|VI",
                  "AS": "americansamoa|AS", "MP": "northernmarianaislands|MP"}

def main():
    reps = zip_to_county(load_reps())
    vp = load_vetpop()
    fips_set = set(vp["FIPS"])
    key_to_fips = dict(zip(vp["key"], vp["FIPS"]))
    # priority: territory aggregate > direct FIPS (if in VetPop) > name-key fallback
    def resolve(row):
        t = TERRITORY_KEYS.get(row["src_state"]) or TERRITORY_KEYS.get(row["state"])
        if t:
            return key_to_fips.get(t)
        if row["fips"] in fips_set:
            return row["fips"]
        return key_to_fips.get(county_key(row["county_name"], row["state"]))
    reps["res_fips"] = reps.apply(resolve, axis=1)
    unmapped = reps["res_fips"].isna().sum()
    counts = reps.groupby("res_fips").size().rename("reps").reset_index()
    by_kind = reps.pivot_table(index="res_fips", columns="kind", values="Registration Num", aggfunc="count").reset_index()
    out = vp.merge(counts, left_on="FIPS", right_on="res_fips", how="left").merge(
        by_kind, left_on="FIPS", right_on="res_fips", how="left")
    for c in ["reps", "attorney", "agent", "vso_rep", "cvso", "state_vso"]:
        if c in out:
            out[c] = out[c].fillna(0).astype(int)
    out["reps_per_1k_vets"] = (out["reps"] / out["Veterans"] * 1000).round(3)
    out = out.rename(columns={"County, State": "county"})
    out = out[["FIPS", "county", "State", "Veterans", "reps", "attorney", "agent",
               "vso_rep", "cvso", "state_vso", "reps_per_1k_vets"]]
    out.to_csv(f"{DATA}/county_rep_density.csv", index=False)
    n_desert = ((out["reps"] == 0) & (out["Veterans"] >= 1000)).sum()
    print(f"reps total (deduped): {len(reps)}; unmapped zips: {unmapped}")
    print(f"counties: {len(out)}; zero-rep counties with >=1000 vets: {n_desert}")
    print(out.sort_values('Veterans', ascending=False).head(5).to_string(index=False))

if __name__ == "__main__":
    main()
