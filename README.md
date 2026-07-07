# VA Claims-Help Deserts

**County-level map and dataset of where U.S. veterans lack nearby VA-accredited claims help.**

Three-quarters of veterans with pending VA disability claims use an accredited representative — a county veterans service officer (CVSO), a VSO rep, an attorney, or a claims agent ([GAO-25-107211](https://www.gao.gov/products/gao-25-107211)). But accredited help is unevenly distributed, and no one has mapped it against where veterans actually live. This project does.

**Headline findings (July 2026 data):**

- **338 counties with 1,000+ veterans have zero accredited representatives** registered in the county — **735,000+ veterans live in these deserts**.
- **658 counties with 1,000+ veterans have no government service officer** (county CVSO or state department officer) — the free, public-sector help that exists precisely so veterans don't have to pay private consultants.
- The largest desert: Cochise County, AZ — ~18,900 veterans, nearest accredited rep ~59 miles away in Tucson.

**Click any county on the map** for its full profile: distance to nearest accredited help, FY24 VA compensation dollars per veteran vs. the state average (below-average dollars in a desert often mean unclaimed benefits), congressional district(s), and a link to its trend over time.

The CVSO Act (§302 of the Dole Act, signed January 2025) requires VA to prioritize outreach grants to areas with a critical shortage of county or tribal veterans service officers. As of July 2026, VA has published no shortage-area determination. This dataset is an independent attempt to identify those areas from public data.

## The map

Interactive county choropleth: **[view the map](https://dan77450-ff.github.io/va-claims-help-deserts/)** (live once GitHub Pages is enabled).

## The data

`data/county_rep_density.csv` — one row per county (3,150 rows):

| column | meaning |
|---|---|
| FIPS | 5-digit county FIPS (CT uses 2022 planning regions) |
| county, State | county name, state |
| Veterans | projected veteran population, FY2026 (VetPop2023) |
| reps | unique accredited representatives registered in county |
| attorney / agent / vso_rep / cvso / state_vso | breakdown by type |
| reps_per_1k_vets | reps per 1,000 veterans |

`data/state_backlog.csv` — VA compensation claims pending and backlog (>125 days) by claimant state, from the VBA Monday Morning Workload Report.

## Sources & method

All source data is public: VA OGC accreditation roster (refreshed 3×/week), VBA Monday Morning Workload Report (weekly), VetPop2023 county projections, Census ZCTA↔county relationship file, CTData planning-region crosswalk. Full method and limitations: [METHODOLOGY.md](METHODOLOGY.md) — **read the limitations before citing.** The pipeline is three scripts in `code/`.

## Reproducing / updating

1. Download the four OGC roster lists and the latest MMWR (URLs in METHODOLOGY.md).
2. `python3 code/build_density.py` → `data/county_rep_density.csv`
3. `python3 code/extract_mmwr_state.py data/MMWR-<date>.xlsx` → `data/state_backlog.csv`
4. `python3 code/build_map.py` → the map HTML.

## License

Code: MIT. Data and documentation: CC BY 4.0. Derived entirely from U.S. government public records; cite as "VA Claims-Help Deserts dataset (Daniel B. Gray)".

## Caveats in one sentence

"Zero reps" means zero *registered addresses* in the county — not necessarily zero help (adjacent counties, remote service, and non-individually-accredited CVSO offices are invisible here); accreditation ≠ active capacity; see METHODOLOGY.md.
