"""Generate desert-map.html — self-contained county choropleth.

Embeds county density + state backlog as JSON; loads D3/topojson from cdnjs
and US county topology from jsdelivr (needs internet when opened).
Output: dataset-projects/desert-map.html
"""
import json
import pandas as pd

d = pd.read_csv("data/county_rep_density.csv", dtype={"FIPS": str})
d["FIPS"] = d["FIPS"].str.zfill(5)
b = pd.read_csv("data/state_backlog.csv")

ABBR = {"Alabama":"AL","Alaska":"AK","Arizona":"AZ","Arkansas":"AR","California":"CA","Colorado":"CO","Connecticut":"CT","Delaware":"DE","District of Columbia":"DC","Florida":"FL","Georgia":"GA","Hawaii":"HI","Idaho":"ID","Illinois":"IL","Indiana":"IN","Iowa":"IA","Kansas":"KS","Kentucky":"KY","Louisiana":"LA","Maine":"ME","Maryland":"MD","Massachusetts":"MA","Michigan":"MI","Minnesota":"MN","Mississippi":"MS","Missouri":"MO","Montana":"MT","Nebraska":"NE","Nevada":"NV","New Hampshire":"NH","New Jersey":"NJ","New Mexico":"NM","New York":"NY","North Carolina":"NC","North Dakota":"ND","Ohio":"OH","Oklahoma":"OK","Oregon":"OR","Pennsylvania":"PA","Puerto Rico":"PR","Rhode Island":"RI","South Carolina":"SC","South Dakota":"SD","Tennessee":"TN","Texas":"TX","Utah":"UT","Vermont":"VT","Virginia":"VA","Washington":"WA","West Virginia":"WV","Wisconsin":"WI","Wyoming":"WY"}

counties = {}
for _, r in d.iterrows():
    counties[r["FIPS"]] = [r["county"], ABBR.get(r["State"], ""), int(r["Veterans"]),
                           int(r["reps"]), int(r["attorney"]), int(r["agent"]),
                           int(r["vso_rep"]), float(r["reps_per_1k_vets"]) if r["Veterans"] else None,
                           int(r["cvso"]), int(r["state_vso"])]
backlog = {r["state"]: [int(r["pending"]), int(r["backlog_gt125d"]), float(r["pct_backlog"])] for _, r in b.iterrows()}
report_date = b["report_date"].iloc[0]

HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>VA Claims-Help Desert Map</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/topojson/3.0.2/topojson.min.js"></script>
<style>
body{font-family:-apple-system,Segoe UI,sans-serif;margin:20px;max-width:1060px}
h1{font-size:22px;margin-bottom:2px} .sub{color:#555;margin-top:0;font-size:14px}
#tip{position:absolute;pointer-events:none;background:#fff;border:1px solid #999;border-radius:4px;padding:8px 10px;font-size:12.5px;box-shadow:2px 2px 6px rgba(0,0,0,.2);display:none;line-height:1.5}
.legend text{font-size:11.5px} .cap{font-size:12px;color:#666}
.note{font-size:13px;color:#444;background:#f6f6f6;border-left:3px solid #bbb;padding:10px 14px;margin-top:18px;line-height:1.55}
</style></head><body>
<h1>VA Claims-Help Deserts</h1>
<p class="sub">Accredited representatives (VSO reps, attorneys, claims agents) per 1,000 veterans by county
&middot; roster snapshot 2026-07-07 &middot; backlog report __RDATE__ &middot; v1.1 (ZCTA crosswalk, CT planning regions, territories, CVSO breakdown)</p>
<div id="map"></div><div id="tip"></div>
<div class="note"><b>Read this before citing:</b> "0 accredited reps" means no rep has a registered address in that county —
veterans may still get help from reps in adjacent counties, county CVSOs registered under a parent org elsewhere, or remote services.
Roster counts accreditation, not active capacity. Zip&rarr;county uses each zip's primary county. Backlog (share of claims pending &gt;125 days) is only published
at state level, by claimant address. Sources: VA OGC accreditation roster; VBA Monday Morning Workload Report; VetPop2023 (FY2026 projection).</div>
<script>
const C=__COUNTIES__, B=__BACKLOG__;
const W=1000,H=640,svg=d3.select('#map').append('svg').attr('viewBox',`0 0 ${W} ${H}`);
const tip=d3.select('#tip');
const color=v=>v==null?'#eee':v[3]===0?(v[2]>=1000?'#b2182b':'#f4a582'):v[7]<0.25?'#fddbc7':v[7]<0.5?'#d1e5f0':v[7]<1?'#67a9cf':'#2166ac';
d3.json('https://cdn.jsdelivr.net/npm/us-atlas@3/counties-albers-10m.json').then(us=>{
  const counties=topojson.feature(us,us.objects.counties).features;
  svg.append('g').selectAll('path').data(counties).join('path')
    .attr('d',d3.geoPath()).attr('fill',d=>color(C[d.id])).attr('stroke','#fff').attr('stroke-width',.3)
    .on('mousemove',(e,d)=>{const v=C[d.id];if(!v)return;
      const st=B[v[1]];
      tip.style('display','block').style('left',(e.pageX+14)+'px').style('top',(e.pageY-10)+'px')
        .html(`<b>${v[0]}</b><br>Veterans (FY26 proj.): ${v[2].toLocaleString()}<br>`+
          `Accredited reps: <b>${v[3]}</b><br><span style="color:#666">${v[8]} county CVSO &middot; ${v[9]} state dept &middot; ${v[6]} VSO &middot; ${v[4]} attorney &middot; ${v[5]} agent</span><br>`+
          `Per 1,000 vets: <b>${v[7]==null?'–':v[7].toFixed(2)}</b>`+
          (st?`<br><span style="color:#666">${v[1]} backlog: ${(st[2]*100).toFixed(1)}% of ${st[0].toLocaleString()} pending</span>`:''));})
    .on('mouseout',()=>tip.style('display','none'));
  svg.append('path').datum(topojson.mesh(us,us.objects.states,(a,b)=>a!==b))
    .attr('fill','none').attr('stroke','#666').attr('stroke-width',.7).attr('d',d3.geoPath());
  const items=[['#b2182b','0 reps, ≥1,000 vets (desert)'],['#f4a582','0 reps, <1,000 vets'],['#fddbc7','<0.25 per 1k'],['#d1e5f0','0.25–0.5'],['#67a9cf','0.5–1'],['#2166ac','≥1 per 1k']];
  const lg=svg.append('g').attr('class','legend').attr('transform','translate(15,540)');
  items.forEach((it,i)=>{const g=lg.append('g').attr('transform',`translate(0,${i*17})`);
    g.append('rect').attr('width',13).attr('height',13).attr('fill',it[0]);
    g.append('text').attr('x',18).attr('y',11).text(it[1]);});
});
</script></body></html>"""

html = (HTML.replace("__COUNTIES__", json.dumps(counties, separators=(",", ":")))
            .replace("__BACKLOG__", json.dumps(backlog, separators=(",", ":")))
            .replace("__RDATE__", report_date))
with open("desert-map.html", "w") as f:
    f.write(html)
print("desert-map.html written,", len(html) // 1024, "KB")
