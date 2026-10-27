#!/usr/bin/env python3
"""Render the GitHub profile's live project / goals panels as a GitHub-safe SVG.

Project dates and repository counts are fetched from the owner's public GitHub
repositories every scheduled refresh. Goals and interests are editorial text,
not automatically verified progress. If the GitHub API fails, do not overwrite.
"""
from datetime import datetime, timezone
from html import escape
from pathlib import Path
import json
import os
import urllib.request

USER = "AnandVB07"
TOKEN = os.environ["GITHUB_TOKEN"]
UTC = datetime.now(timezone.utc)

def github(url):
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "AnandVB07-profile-widget"
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)

repos = []
for page in range(1, 5):
    results = github(f"https://api.github.com/users/{USER}/repos?per_page=100&page={page}&type=owner")
    repos.extend(results)
    if len(results) < 100:
        break
public_repos = [r for r in repos if not r.get("fork") and not r.get("private")]
by_name = {r["name"].lower(): r for r in public_repos}
def project_meta(name):
    found = by_name.get(name.lower())
    if not found:
        return "Repository unavailable"
    updated = found.get("pushed_at") or found.get("updated_at")
    return f"Updated {datetime.fromisoformat(updated.replace('Z','+00:00')).strftime('%d %b %Y')}" if updated else "Public repository"
latest = max(public_repos, key=lambda r: r.get("pushed_at") or "") if public_repos else None
latest_name = latest["name"] if latest else "No public repositories"
latest_date = project_meta(latest_name) if latest else "No updates"

def tag(v):
    return escape(str(v), quote=True)

pieces = [
'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="1220" viewBox="0 0 1200 1220" role="img" aria-labelledby="title desc">
<title id="title">Beyond Coding, Project Galaxy, and 2026 Goals</title>
<desc id="desc">Neat navy and neon-blue GitHub profile panels. Project update dates and public repo count refresh from GitHub; personal interests and goals are static.</desc>
<defs>
 <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#030B18"/><stop offset=".55" stop-color="#071529"/><stop offset="1" stop-color="#040E1D"/></linearGradient>
 <linearGradient id="line" x1="0" y1="0" x2="1" y2="0"><stop stop-color="#06E1F3"/><stop offset="1" stop-color="#3468FF"/></linearGradient>
 <linearGradient id="panel" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#091B30"/><stop offset="1" stop-color="#061324"/></linearGradient>
 <linearGradient id="tile" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#0D2238"/><stop offset="1" stop-color="#081426"/></linearGradient>
 <radialGradient id="haze"><stop stop-color="#0C73B9" stop-opacity=".26"/><stop offset="1" stop-color="#0C73B9" stop-opacity="0"/></radialGradient>
</defs>
<rect width="1200" height="1220" rx="22" fill="url(#bg)"/>
<circle cx="1080" cy="90" r="230" fill="url(#haze)"/>
<circle cx="1040" cy="698" r="240" fill="url(#haze)" opacity=".55"/>
<rect x="1" y="1" width="1198" height="1218" rx="21" fill="none" stroke="#1E3A5D" stroke-width="2"/>
'''
]
def rect(x,y,w,h,fill="#0B1B2D",stroke="#244B6B",rx=13):
    pieces.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>')

def text(x,y,value,size=20,color="#EAF4FF",weight=500,anchor=None):
    att=f' text-anchor="{anchor}"' if anchor else ""
    pieces.append(f'<text x="{x}" y="{y}" fill="{color}" font-family="Arial,Helvetica,sans-serif" font-size="{size}" font-weight="{weight}"{att}>{tag(value)}</text>')

def icon(kind,x,y,color):
    paths={
      "code":'<path d="M12 8L4 16l8 8m8-16 8 8-8 8M19 5l-6 22"/>',
      "chart":'<path d="M5 25V17M12 25V12M19 25V7M26 25V4"/>',
      "brain":'<path d="M11 8a7 7 0 0 1 11-1 6 6 0 0 1 2 7 6 6 0 0 1 0 12 7 7 0 0 1-12-2M11 8C2 6 2 18 8 19c-3 7 5 11 11 5M13 4v23"/>',
      "rocket":'<path d="M7 19l-2 7 7-2m0-13 10-6 4 4-6 10-8 2-3-7Zm3 4 4 4M11 20l-4-4"/>',
      "grid":'<rect x="4" y="4" width="10" height="10" rx="1"/><rect x="18" y="4" width="10" height="10" rx="1"/><rect x="4" y="18" width="10" height="10" rx="1"/><rect x="18" y="18" width="10" height="10" rx="1"/>',
      "java":'<path d="M13 23h14M16 7c6 5-5 6 0 11m-9 3c0 6 19 6 19 0M8 25c2 3 14 3 17 0"/>',
      "network":'<rect x="3" y="7" width="8" height="8" rx="2"/><rect x="21" y="7" width="8" height="8" rx="2"/><rect x="12" y="23" width="8" height="7" rx="2"/><path d="M7 15v4h18v-4m-9 4v4"/>',
      "globe":'<circle cx="16" cy="16" r="13"/><path d="M3 16h26M16 3c-9 7-9 19 0 26M16 3c9 7 9 19 0 26"/>',
      "terminal":'<rect x="2" y="5" width="28" height="23" rx="3"/><path d="m8 12 6 5-6 5m9 0h7"/>',
      "target":'<circle cx="16" cy="16" r="13"/><circle cx="16" cy="16" r="7"/><circle cx="16" cy="16" r="2"/>',
      "book":'<path d="M16 5C9 2 4 5 3 6v22c7-4 10-3 13 0 4-3 8-4 13 0V6c-7-3-10-2-13-1Zm0 0v23"/>',
      "trophy":'<path d="M9 5h14v10c0 12-14 12-14 0ZM9 8H4c-1 7 3 8 7 9m12-9h5c1 7-3 8-7 9M16 24v5M10 30h12"/>'
    }
    path=paths[kind]
    pieces.append(f'<g transform="translate({x},{y})" stroke="{color}" fill="none" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">{path}</g>')

def heading(y,title,sub):
    text(63,y,title,34,"#F5F9FF",700)
    text(63,y+26,sub,13,"#91A8C5",600)
    pieces.append(f'<path d="M63 {y+40}H1136" stroke="url(#line)" stroke-width="1.8" opacity=".64"/>')

def card(x,y,title,subtitle,kind,color,width=518,height=75):
    rect(x,y,width,height, "url(#tile)","#27435D",12)
    rect(x+13,y+14,46,46,"#0A2841",color,10)
    icon(kind,x+20,y+21,color)
    text(x+74,y+33,title,21,"#EDF5FF",700)
    text(x+74,y+58,subtitle,16,"#A8BCD2",400)

rect(30,28,1140,310,"url(#panel)","#1973AB",19)
heading(79,"Beyond Coding","WHAT I'M EXPLORING")
card(62,140,"MERN Stack","Full-stack apps and clean user experiences","code","#17BFE8")
card(620,140,"Trading Systems","Finance workflows and market tools","chart","#24D1B1")
card(62,230,"AI + Finance","Practical machine learning ideas","brain","#B28CFF")
card(620,230,"FinTech Ideas","Building useful products step by step","rocket","#FF9BA7")

rect(30,360,1140,445,"url(#panel)","#1973AB",19)
heading(414,"Project Galaxy","LINKS TO REAL WORK + RECENT ACTIVITY")
card(62,474,"DSA Universe","Data Structures and Algorithms","target","#1BCBEF",518,80)
card(620,474,"Java Projects","Core Java applications and practice","java","#FFB15E",518,80)
card(62,568,"Networking Labs","Cisco Packet Tracer learning","network","#51DBCE",518,80)
card(620,568,"Portfolio Website",project_meta("AnandPortfolio"),"globe","#B28CFF",518,80)
card(62,662,"FinTech Experiments",project_meta("zenBull"),"chart","#F699B7",518,80)
card(620,662,"ChurnIQ",project_meta("ChurnIQ"),"terminal","#62BEFF",518,80)

rect(30,827,1140,365,"url(#panel)","#1973AB",19)
heading(878,"2026 Goals","PERSONAL TARGETS · NOT AUTOMATIC COMPLETION CLAIMS")
goals=[
 (62,935,"Solve 500+ DSA Problems","target","#25C8FB"),
 (620,935,"Learn Backend Development","code","#4FDDC2"),
 (62,1011,"Build a Strong GitHub Portfolio","grid","#AF8BFF"),
 (620,1011,"Launch a FinTech Project","rocket","#F39EB8"),
 (62,1087,"Master Java Development","java","#FFB15E"),
 (620,1087,"Secure a Software Engineering Role","trophy","#40CBEF"),
]
for x,y,label,kind,color in goals:
    rect(x,y,518,62,"url(#tile)","#27435D",12)
    rect(x+12,y+12,38,38,"#0A2841",color,9)
    icon(kind,x+15,y+14,color)
    text(x+64,y+38,label,18,"#EAF4FF",600)

# Live source metadata is grounded in GitHub's REST API.
rect(918,44,220,39,"#0A2943","#1D699B",15)
pieces.append('<circle cx="941" cy="64" r="5" fill="#22E1A8"/>')
text(958,69,f"{len(public_repos)} public repos",17,"#B6F6FF",700)
text(1140,1180,f"Refreshed {UTC.strftime('%d %b %Y %H:%M UTC')}",13,"#7FA3BD",400,"end")
pieces.append('</svg>')

output=Path("assets/profile-panels-live.svg")
output.parent.mkdir(exist_ok=True,parents=True)
output.write_text("\n".join(pieces),encoding="utf-8")
print(f"Wrote {output} with {len(public_repos)} public repos; latest push: {latest_name} ({latest_date})")
