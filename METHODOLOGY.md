# VA Claims-Help Desert Map — Methodology (v1.2, July 2026)

## What it shows
County-level density of VA-accredited representatives (VSO representatives, attorneys, claims agents) per 1,000 veterans, with state-level claims backlog context. Built to identify areas where veterans lack nearby free, accredited claims help — the gap the CVSO Act (§302, Dole Act, Jan 2025) requires VA to prioritize in grant-making.

## Sources
1. **Representatives:** VA Office of General Counsel accreditation lists (attorneyexcellist, caexcellist, orgsexcellist), downloaded 2026-07-07 from va.gov/ogc/apps/accreditation. 15,431 unique individuals after dedup by Registration Number (8,690 VSO reps, 6,043 attorneys, 697 claims agents, minus cross-list overlap).
2. **Veteran population:** VetPop2023 county projections (data.va.gov, dataset 9L), FY2026 values, all ages/sexes.
3. **Backlog:** VBA Monday Morning Workload Report, 2026-07-04, raw Data sheet (MT=6 state view by claimant address, CAT=11 compensation). Backlog = rating claims pending >125 days.

## Method
Rep zip → county FIPS via Census 2020 ZCTA↔county relationship file (primary county = largest land-area overlap of the zip); Connecticut zips via CTData's ZCTA→planning-region crosswalk (2022 county-equivalents); territories (PR/GU/VI/AS/MP) matched to VetPop's aggregate rows; non-ZCTA zips (PO boxes) fall back to name matching via the `zipcodes` package. Density = unique reps (deduped by Registration Number) ÷ FY2026 projected veterans × 1,000.

Rep types: reps affiliated with the National Association of County Veterans Service Officers are classified `cvso`; reps of state veterans departments/commissions as `state_vso`; remaining org-affiliated reps as `vso_rep`; plus `attorney` and `agent`. Dual-affiliated reps are classified by priority cvso > state_vso > vso_rep (so a CVSO also accredited under American Legion counts as CVSO). Totals: 2,119 CVSOs, 3,728 state officers, 2,832 other VSO reps, 6,039 attorneys, 696 agents; 16 of 15,431 zips unmapped.

## Limitations — read before citing
- **"Zero reps" ≠ zero help.** Reps in adjacent counties, county CVSOs registered under a parent organization's address, and phone/remote services are invisible here. This maps *registered addresses*, not service coverage.
- **Accreditation ≠ capacity.** Many accredited attorneys take few or no VA cases; the roster has no caseload data.
- **Zip→county assigns each zip wholly to its primary county** (largest land overlap). Reps near county lines may be attributed to the neighboring county. 16 of 15,431 rep zips (0.1%) failed to map and are excluded.
- **"Foreign Countries"** is an aggregate VetPop row with no rep join (77k veterans abroad).
- **CVSO classification is roster-derived:** CVSOs accredited only through a state department (not NACVSO) appear as `state_vso`; a few counties run CVSO offices whose officers hold no individual VA accreditation and are invisible here.
- **Backlog is state-level only** (finest published geography, by claimant address). County backlog does not exist publicly.
- **Point-in-time:** roster changes 3x/week; backlog weekly; VetPop is a projection model, not a count.

## County profiles (click panel), v1.2
- **Nearest help:** great-circle distance from the county's Census-gazetteer centroid (2023) to the nearest rep's zip centroid; computed only for zero-rep counties. Road distance will be longer.
- **Dollars:** FY24 GDX "County Direct Exp" Compensation & Pension, divided by FY26 projected veterans (fiscal-year mismatch noted); state benchmark = state C&P total / state veterans. Above/below state average is descriptive - high per-veteran dollars can reflect an older or more service-connected population, not just claiming rates.
- **Districts:** Census county-CD relationship file, 118th Congress. A few states redrew districts for the 119th (e.g., AL, GA, LA, NC, NY) - verify via the house.gov lookup linked in the panel.
- **Trends:** weekly roster snapshots (since 2026-07-07) feed docs/trends.csv / trends-summary.csv, rendered at trends.html.

## Files
- `desert-map.html` — interactive map (needs internet for base geography)
- `data/county_rep_density.csv` — the dataset (3,150 counties)
- `data/state_backlog.csv` — state backlog extract
- `code/build_density.py`, `code/extract_mmwr_state.py`, `code/build_map.py` — full pipeline
