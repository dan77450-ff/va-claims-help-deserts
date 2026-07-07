"""Generate docs/index.html — county choropleth with hover tooltip + click side panel.

Hover: quick stats. Click: full county profile (nearest help, GDX $/veteran vs state,
congressional districts, trends link). Embeds density + backlog + profiles as JSON;
loads D3/topojson from cdnjs and county topology from jsdelivr (needs internet).
"""
import json
import pandas as pd

d = pd.read_csv("data/county_rep_density.csv", dtype={"FIPS": str})
d["FIPS"] = d["FIPS"].str.zfill(5)
b = pd.read_csv("data/state_backlog.csv")
profiles = json.load(open("data/county_profiles.json"))

ABBR = {"Alabama":"AL","Alaska":"AK","Arizona":"AZ","Arkansas":"AR","California":"CA","Colorado":"CO","Connecticut":"CT","Delaware":"DE","District of Columbia":"DC","Florida":"FL","Georgia":"GA","Hawaii":"HI","Idaho":"ID","Illinois":"IL","Indiana":"IN","Iowa":"IA","Kansas":"KS","Kentucky":"KY","Louisiana":"LA","Maine":"ME","Maryland":"MD","Massachusetts":"MA","Michigan":"MI","Minnesota":"MN","Mississippi":"MS","Missouri":"MO","Montana":"MT","Nebraska":"NE","Nevada":"NV","New Hampshire":"NH","New Jersey":"NJ","New Mexico":"NM","New York":"NY","North Carolina":"NC","North Dakota":"ND","Ohio":"OH","Oklahoma":"OK","Oregon":"OR","Pennsylvania":"PA","Puerto Rico":"PR","Rhode Island":"RI","South Carolina":"SC","South Dakota":"SD","Tennessee":"TN","Texas":"TX","Utah":"UT","Vermont":"VT","Virginia":"VA","Washington":"WA","West Virginia":"WV","Wisconsin":"WI","Wyoming":"WY"}

counties = {}
for _, r in d.iterrows():
    counties[r["FIPS"]] = [r["county"], ABBR.get(r["State"], ""), int(r["Veterans"]),
                           int(r["reps"]), int(r["attorney"]), int(r["agent"]),
                           int(r["vso_rep"]), float(r["reps_per_1k_vets"]) if r["Veterans"] else None,
                           int(r["cvso"]), int(r["state_vso"])]
backlog = {r["state"]: [int(r["pending"]), int(r["backlog_gt125d"]), float(r["pct_backlog"])] for _, r in b.iterrows()}
report_date = b["report_date"].iloc[0]
roster_date = open("data/roster-snapshot-date.txt").read().strip()

HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>VA Claims-Help Desert Map</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/topojson/3.0.2/topojson.min.js"></script>
<style>
body{font-family:-apple-system,Segoe UI,sans-serif;margin:20px;max-width:1340px}
h1{font-size:22px;margin-bottom:2px} .sub{color:#555;margin-top:0;font-size:13.5px}
#wrap{display:flex;gap:16px;align-items:flex-start;flex-wrap:wrap}
#map{flex:1 1 640px;min-width:340px}
#panel{flex:0 0 300px;border:1px solid #ddd;border-radius:8px;padding:14px 16px;font-size:13.5px;line-height:1.55;background:#fafafa;position:sticky;top:10px}
#panel h2{font-size:16px;margin:0 0 2px} #panel .muted{color:#666}
#panel .stat{margin:9px 0} #panel .big{font-size:15px;font-weight:600}
.badge{display:inline-block;background:#b2182b;color:#fff;border-radius:4px;padding:1px 7px;font-size:11.5px;font-weight:600;margin-left:6px;vertical-align:middle}
.pos{color:#1a7a3a}.neg{color:#b2182b}
#tip{position:absolute;pointer-events:none;background:#fff;border:1px solid #999;border-radius:4px;padding:6px 9px;font-size:12.5px;box-shadow:2px 2px 6px rgba(0,0,0,.2);display:none;line-height:1.45}
.legend text{font-size:11.5px}
.note{font-size:12.5px;color:#444;background:#f6f6f6;border-left:3px solid #bbb;padding:9px 13px;margin-top:16px;line-height:1.5}
a{color:#1c5f9e} path.county{cursor:pointer}
</style></head><body>
<h1>VA Claims-Help Deserts</h1>
<p class="sub">Accredited representatives per 1,000 veterans by county &middot; roster __RSNAP__ &middot; backlog __RDATE__ &middot;
hover for quick stats, <b>click a county for the full picture</b> &middot; <a href="trends.html">trends</a> &middot; <a href="https://github.com/dan77450-ff/va-claims-help-deserts">data &amp; methodology</a></p>
<div id="wrap"><div id="map"></div><div id="panel"><span class="muted">Click a county to see its profile: distance to nearest help, benefit dollars vs. state average, and whose district it is.</span></div></div>
<div id="tip"></div>
<div class="note"><b>Read this before citing:</b> "0 accredited reps" means no rep has a registered address in that county —
help may exist in adjacent counties or remotely; roster counts accreditation, not active capacity.
Dollars are FY24 VA Compensation &amp; Pension expenditures (GDX) per projected FY26 veteran. Districts are 118th-Congress boundaries.
Backlog is state-level only. Sources: VA OGC roster; VBA MMWR; VetPop2023; VA GDX FY24; Census.</div>
<script>
const C=__COUNTIES__, B=__BACKLOG__, P=__PROFILES__;
const W=1000,H=640,svg=d3.select('#map').append('svg').attr('viewBox',`0 0 ${W} ${H}`).attr('width','100%');
const tip=d3.select('#tip'), panel=d3.select('#panel');
const fmt=n=>n.toLocaleString();
const color=v=>v==null?'#eee':v[3]===0?(v[2]>=1000?'#b2182b':'#f4a582'):v[7]<0.25?'#fddbc7':v[7]<0.5?'#d1e5f0':v[7]<1?'#67a9cf':'#2166ac';
let selected=null;
function showPanel(f){
  const v=C[f]; if(!v)return;
  const p=P[f]||{}, st=B[v[1]];
  let h=`<h2>${v[0]}${v[3]===0&&v[2]>=1000?'<span class="badge">DESERT</span>':''}</h2>`;
  h+=`<div class="muted">${fmt(v[2])} veterans (FY26 proj.)</div>`;
  h+=`<div class="stat"><span class="big">${v[3]}</span> accredited rep${v[3]===1?'':'s'} in county<br>`+
     `<span class="muted">${v[8]} county CVSO &middot; ${v[9]} state dept &middot; ${v[6]} VSO &middot; ${v[4]} attorney &middot; ${v[5]} agent</span></div>`;
  if(p.nearest_mi!=null) h+=`<div class="stat">Nearest accredited rep: <span class="big">~${p.nearest_mi} mi</span><br><span class="muted">${p.nearest_loc}</span></div>`;
  if(p.cp_per_vet!=null){
    const dpct=p.st_cp_per_vet?Math.round((p.cp_per_vet/p.st_cp_per_vet-1)*100):null;
    h+=`<div class="stat">VA compensation: <span class="big">$${fmt(p.cp_per_vet)}</span> per veteran/yr`;
    if(dpct!=null) h+=` <span class="${dpct<0?'neg':'pos'}">(${dpct>0?'+':''}${dpct}% vs ${v[1]} avg $${fmt(p.st_cp_per_vet)})</span>`;
    if(dpct!=null&&dpct<0&&v[3]===0) h+=`<br><span class="muted">Below-average dollars in a desert county often mean unclaimed benefits, not healthier veterans.</span>`;
    h+=`</div>`;
  }
  if(st) h+=`<div class="stat">${v[1]} claims backlog: <span class="big">${(st[2]*100).toFixed(1)}%</span> of ${fmt(st[0])} pending &gt;125 days</div>`;
  if(p.cds) h+=`<div class="stat">Congressional district${p.cds.length>1?'s':''}: <b>${p.cds.join(', ')}</b><br><a href="https://www.house.gov/representatives/find-your-representative" target="_blank">Find &amp; contact the representative</a></div>`;
  h+=`<div class="stat"><a href="trends.html?fips=${f}">County trend over time &rarr;</a></div>`;
  panel.html(h);
}
d3.json('https://cdn.jsdelivr.net/npm/us-atlas@3/counties-albers-10m.json').then(us=>{
  const feats=topojson.feature(us,us.objects.counties).features;
  svg.append('g').selectAll('path').data(feats).join('path').attr('class','county')
    .attr('d',d3.geoPath()).attr('fill',d=>color(C[d.id])).attr('stroke','#fff').attr('stroke-width',.3)
    .on('mousemove',(e,d)=>{const v=C[d.id];if(!v)return;
      tip.style('display','block').style('left',(e.pageX+14)+'px').style('top',(e.pageY-10)+'px')
        .html(`<b>${v[0]}</b><br>${fmt(v[2])} veterans &middot; ${v[3]} reps (${v[7]==null?'–':v[7].toFixed(2)}/1k)<br><span style="color:#888">click for details</span>`);})
    .on('mouseout',()=>tip.style('display','none'))
    .on('click',(e,d)=>{if(!C[d.id])return;
      if(selected)selected.attr('stroke','#fff').attr('stroke-width',.3);
      selected=d3.select(e.currentTarget).attr('stroke','#222').attr('stroke-width',1.4).raise();
      showPanel(d.id);});
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
            .replace("__PROFILES__", json.dumps(profiles, separators=(",", ":")))
            .replace("__RDATE__", str(report_date))
            .replace("__RSNAP__", roster_date))
with open("docs/index.html", "w") as f:
    f.write(html)
print("docs/index.html written,", len(html) // 1024, "KB")
