#!/usr/bin/env python3
"""Regenerate a GitHub-safe profile analytics SVG from GitHub's API.

Runs with the repo GITHUB_TOKEN on a schedule. It fails rather than publishing
invented numbers when the API is unavailable.
"""
import os, json, urllib.request
from pathlib import Path
from datetime import datetime, timedelta, timezone, date
from collections import defaultdict
from html import escape

USER = "AnandVB07"
TOKEN = os.environ["GITHUB_TOKEN"]
TODAY = datetime.now(timezone.utc).date()
COLORS = {"JavaScript":"#F7D94E","TypeScript":"#247DFA","Jupyter Notebook":"#FF7B24",
          "HTML":"#F65444","Python":"#468FDA","CSS":"#963EDC","Java":"#EB784C",
          "C++":"#718EC9","Dart":"#41CAD8","Go":"#4BD8CE"}

def api(url, payload=None):
    req = urllib.request.Request(url,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Authorization":"Bearer "+TOKEN,"User-Agent":"profile-analytics",
                 "Accept":"application/vnd.github+json","Content-Type":"application/json",
                 "X-GitHub-Api-Version":"2022-11-28"},
        method="POST" if payload is not None else "GET")
    with urllib.request.urlopen(req,timeout=30) as res:
        result=json.loads(res.read().decode())
    if isinstance(result,dict) and result.get("errors"):
        raise RuntimeError(str(result["errors"]))
    return result

QUERY = """
query($login:String!, $from:DateTime!, $to:DateTime!){
  user(login:$login){
    pullRequests(first:1){totalCount}
    issues(first:1){totalCount}
    contributionsCollection(from:$from,to:$to){
      totalCommitContributions
      contributionCalendar{
        weeks{contributionDays{date contributionCount}}
      }
      commitContributionsByRepository(maxRepositories:100){repository{nameWithOwner}}
      pullRequestContributionsByRepository(maxRepositories:100){repository{nameWithOwner}}
      issueContributionsByRepository(maxRepositories:100){repository{nameWithOwner}}
    }
  }
}
"""
def contributions(start,end):
    d=api("https://api.github.com/graphql",{"query":QUERY,"variables":{
        "login":USER,"from":start.isoformat()+"T00:00:00Z",
        "to":end.isoformat()+"T23:59:59Z"}})["data"]["user"]
    c=d["contributionsCollection"]
    days={v["date"]:int(v["contributionCount"])
          for w in c["contributionCalendar"]["weeks"] for v in w["contributionDays"]
          if start.isoformat()<=v["date"]<=end.isoformat()}
    repos=set()
    for key in ("commitContributionsByRepository","pullRequestContributionsByRepository",
                "issueContributionsByRepository"):
        repos.update(v["repository"]["nameWithOwner"] for v in c[key])
    return c,days,repos,d

def streaks(days):
    active=sorted(date.fromisoformat(k) for k,v in days.items() if v>0)
    longest=(0,None,None)
    if active:
        start=prev=active[0]
        for d in active[1:]+[TODAY+timedelta(days=2)]:
            if d!=prev+timedelta(days=1):
                length=(prev-start).days+1
                if length>longest[0]:longest=(length,start,prev)
                start=d
            prev=d
    end=TODAY if days.get(TODAY.isoformat(),0)>0 else TODAY-timedelta(days=1)
    if not days.get(end.isoformat(),0):
        current=(0,None,None)
    else:
        start=end
        while days.get((start-timedelta(days=1)).isoformat(),0)>0:
            start-=timedelta(days=1)
        current=((end-start).days+1,start,end)
    return current,longest

def stamp_range(r):
    _,a,b=r
    if not a:return "No active streak"
    if a==b:return a.strftime("%d %b %Y")
    return a.strftime("%d %b %Y")+" - "+b.strftime("%d %b %Y")

profile=api("https://api.github.com/users/"+USER)
joined=date.fromisoformat(profile["created_at"][:10])
past=TODAY-timedelta(days=364)
year,_,recent,identity=contributions(past,TODAY)
daily={}
cursor=joined
while cursor<=TODAY:
    end=min(TODAY,cursor+timedelta(days=364))
    _,segment,_,_=contributions(cursor,end)
    daily.update(segment)
    cursor=end+timedelta(days=1)
current,longest=streaks(daily)

repos=[]
for page in range(1,5):
    part=api(f"https://api.github.com/users/{USER}/repos?type=owner&per_page=100&page={page}")
    repos.extend(part)
    if len(part)<100:break
stars=0
languages=defaultdict(int)
for repo in repos:
    if repo.get("fork") or repo.get("archived"):continue
    stars+=int(repo.get("stargazers_count",0))
    for lang,bytes_ in api(repo["languages_url"]).items():languages[lang]+=int(bytes_)
total_bytes=sum(languages.values()) or 1
top=sorted(languages.items(),key=lambda pair:pair[1],reverse=True)[:6]

def t(x,y,s,size=21,color="#E6F2FF",bold=False,anchor="start"):
    return (f'<text x="{x}" y="{y}" text-anchor="{anchor}" fill="{color}" '
            f'font-family="Arial,Helvetica,sans-serif" font-size="{size}" '
            f'font-weight="{700 if bold else 400}">{escape(str(s))}</text>')
def shape(kind,x,y,color="#00E5FF"):
    shapes={
      "star":'<path d="M15 2l4 9 10 1.5-7 7 1.6 10-8.6-5-8.6 5 1.6-10-7-7L11 11Z"/>',
      "clock":'<circle cx="15" cy="15" r="12"/><path d="M15 8v9l6 4"/>',
      "pr":'<circle cx="6" cy="5" r="3"/><circle cx="6" cy="26" r="3"/><circle cx="25" cy="26" r="3"/><path d="M6 8v15M25 23v-7c0-5-9-4-9-10m0 0-4 4m4-4 4 4"/>',
      "issue":'<circle cx="15" cy="15" r="12"/><path d="M15 8v11M15 23v.2"/>',
      "repo":'<rect x="6" y="2" width="19" height="27" rx="2"/><path d="M6 23h19"/>',
      "chart":'<path d="M3 27V16M10 27V11M18 27V18M26 27V4"/>',
      "flame":'<path d="M17 2c3 8-3 10 0 14 4-2 5-5 5-7 8 10 3 21-7 21C4 30 0 17 10 9c0 5 1 7 3 9-1-7 0-11 4-16Z"/>',
      "trophy":'<path d="M9 4h13v8c0 10-13 10-13 0V4Zm0 2H4v3c0 5 5 7 8 7M22 6h5v3c0 5-5 7-8 7M16 20v6m-7 2h14"/>',
    }
    return f'<g transform="translate({x} {y})" fill="none" stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">{shapes[kind]}</g>'

parts=["""<svg xmlns="http://www.w3.org/2000/svg" width="1640" height="900" viewBox="0 0 1640 900">
<title>Anand VB - Automatically Updated GitHub Analytics</title>
<defs>
<linearGradient id="bg" x2="1" y2="1"><stop stop-color="#031021"/><stop offset="1" stop-color="#071729"/></linearGradient>
<linearGradient id="blue" x2="1" y2="1"><stop stop-color="#00325B"/><stop offset="1" stop-color="#001A30"/></linearGradient>
<linearGradient id="teal" x2="1" y2="1"><stop stop-color="#003B40"/><stop offset="1" stop-color="#001E29"/></linearGradient>
<linearGradient id="purple" x2="1" y2="1"><stop stop-color="#30145A"/><stop offset="1" stop-color="#120E31"/></linearGradient>
<clipPath id="bar"><rect x="976" y="300" width="559" height="30" rx="15"/></clipPath>
</defs>
<rect width="1640" height="900" fill="url(#bg)"/>
<rect x="28" y="33" width="1584" height="830" rx="19" fill="#061326" stroke="#19699F" stroke-width="1.6"/>
<rect x="48" y="132" width="1544" height="440" rx="20" fill="#041121" stroke="#285677" stroke-width="1.5"/>
<rect x="68" y="59" width="56" height="54" rx="11" fill="#102947" stroke="#26B5EE"/>
<rect x="82" y="79" width="8" height="24" rx="3" fill="#3BE3A8"/>
<rect x="94" y="68" width="8" height="35" rx="3" fill="#24C5EE"/>
<rect x="106" y="85" width="8" height="18" rx="3" fill="#F376AE"/>
"""]
parts.append(t(151,101,"GitHub Analytics",39,"#F5F7FF",True))
parts.append(t(79,210,"ANAND VB's",29,"#F5F7FF",True))
parts.append(t(277,210,"GitHub Stats",29,"#0DE1EE",True))
parts.append('<path d="M644 185V537M943 185V537" stroke="#2B5473" stroke-width="2"/>')
rows=[
 ("star","Total Stars Earned",stars),
 ("clock","Commits (past year)",int(year["totalCommitContributions"])),
 ("pr","Total Pull Requests",int(identity["pullRequests"]["totalCount"])),
 ("issue","Total Issues",int(identity["issues"]["totalCount"])),
 ("repo","Repos worked on (past year)",len(recent)),
]
for i,(ico,label,value) in enumerate(rows):
    yy=262+57*i
    parts.append(f'<rect x="78" y="{yy-28}" width="52" height="45" rx="12" fill="#0B2338" stroke="#119DC5"/>')
    parts.append(shape(ico,88,yy-21))
    parts.append(t(154,yy+1,label,20,"#CBDEF1"))
    parts.append(t(616,yy+1,f"{value:,}",26,"#00E9EF",True,"end"))
    if i<4:parts.append(f'<path d="M151 {yy+17}H616" stroke="#203E53"/>')
# Decorative GitHub mascot silhouette, drawn as primitives.
parts.append("""<circle cx="793" cy="363" r="102" fill="none" stroke="#10384F" stroke-width="2"/>
<circle cx="793" cy="363" r="82" fill="#052539" stroke="#0B7C94" stroke-width="9"/>
<circle cx="793" cy="363" r="65" fill="#00CDE0"/>
<path d="M759 340l10-13 15 9q10-3 20 0l13-9 11 14c18 28 9 42-11 48v21h-49v-20c-20-7-30-26-9-50Z" fill="#041527"/>
<path d="M765 390q-15 2-20-13" fill="none" stroke="#041527" stroke-width="6" stroke-linecap="round"/>
<path d="M777 280q16-5 31 0" fill="none" stroke="#00F1F1" stroke-width="8" stroke-linecap="round"/>""")
parts.append(t(976,210,"Most Used",29,"#F6F8FF",True))
parts.append(t(1151,210,"Languages",29,"#00E5EF",True))
parts.append('<rect x="969" y="295" width="573" height="40" rx="20" fill="#091D30" stroke="#2D506D" stroke-width="1.5"/>')
parts.append('<g clip-path="url(#bar)">')
bar_x=976
for name,bytes_ in top:
    width=559*bytes_/total_bytes
    parts.append(f'<rect x="{bar_x:.2f}" y="300" width="{width:.2f}" height="30" fill="{COLORS.get(name,"#6994B3")}"/>')
    bar_x+=width
parts.append("</g>")
for i,(name,count) in enumerate(top):
    x=990+285*(i%2)
    y=399+62*(i//2)
    shown=name if len(name)<=15 else name[:13]+"..."
    parts.append(f'<circle cx="{x}" cy="{y-8}" r="9" fill="{COLORS.get(name,"#6994B3")}"/>')
    parts.append(t(x+20,y,shown,18,"#DCE8F6"))
    parts.append(t(x+270,y,f"{count/total_bytes*100:.1f}%",20,"#04E5EE",True,"end"))
    if i<4:parts.append(f'<path d="M{x+20} {y+13}H{x+270}" stroke="#1D3952"/>')
if not top:parts.append(t(1060,399,"No public language data",18))
cards=[
 (52,"#099CEB","blue","chart",sum(daily.values()),"Total Contributions",f"Since {joined:%b %Y}"),
 (576,"#00D8CB","teal","flame",current[0],"Current Streak",stamp_range(current)),
 (1100,"#8D4CFF","purple","trophy",longest[0],"Longest Streak",stamp_range(longest)),
]
for x,color,fill,ico,num,label,detail in cards:
    parts.append(f'<rect x="{x}" y="602" width="488" height="237" rx="20" fill="url(#{fill})" stroke="{color}" stroke-width="1.6"/>')
    parts.append(f'<rect x="{x+28}" y="635" width="90" height="90" rx="17" fill="#092038" stroke="{color}"/>')
    parts.append(shape(ico,x+58,664,color))
    parts.append(t(x+148,691,f"{num:,}",50,"#FFFFFF",True))
    parts.append(t(x+148,735,label,23,"#E6F4FF",True))
    parts.append(t(x+31,804,detail,18,"#A2BED4"))
    if ico=="chart":
        for i,h in enumerate([22,38,50,66,82]):
            parts.append(f'<rect x="{x+362+i*24}" y="{799-h}" width="14" height="{h}" rx="6" fill="#0E8BC7" opacity=".20"/>')
    elif ico=="flame":
        # A compact, data-backed contribution grid lives inside the Current Streak card.
        # The snake path sweeps across the actual contribution squares from the last 21 days.
        grid_x,grid_y=x+302,675
        cell_w,cell_h,step_x,step_y=13,13,20,19
        recent_days=[TODAY-timedelta(days=20-i) for i in range(21)]
        for idx,day in enumerate(recent_days):
            row,col=divmod(idx,7)
            count=int(daily.get(day.isoformat(),0))
            color=("#142B3D" if count==0 else "#0B553B" if count==1 else
                   "#0E8B5A" if count<=3 else "#17B978" if count<=7 else "#46E99C")
            parts.append(f'<rect x="{grid_x+col*step_x}" y="{grid_y+row*step_y}" width="{cell_w}" height="{cell_h}" rx="3" fill="{color}"/>')
        points=[]
        for col in range(7):points.append((grid_x+cell_w/2+col*step_x,grid_y+cell_h/2))
        for col in range(6,-1,-1):points.append((grid_x+cell_w/2+col*step_x,grid_y+step_y+cell_h/2))
        for col in range(7):points.append((grid_x+cell_w/2+col*step_x,grid_y+2*step_y+cell_h/2))
        snake_d="M "+" L ".join(f"{px:.1f} {py:.1f}" for px,py in points)
        parts.append(f'<path d="{snake_d}" fill="none" stroke="#2AD98C" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="8 7" opacity=".9"><animate attributeName="stroke-dashoffset" values="0;-15" dur="1s" repeatCount="indefinite"/></path>')
        parts.append(f'<g><circle r="6" fill="#B9FFD7" stroke="#12BF77" stroke-width="2"><animateMotion dur="6s" repeatCount="indefinite" rotate="auto" path="{snake_d}"/></circle><circle r="1.5" cx="2" cy="-2" fill="#0B2832"><animateMotion dur="6s" repeatCount="indefinite" rotate="auto" path="{snake_d}"/></circle></g>')
    else:
        for i,h in enumerate([21,37,52,70]):
            parts.append(f'<rect x="{x+364+i*24}" y="{799-h}" width="14" height="{h}" rx="6" fill="#905CFA" opacity=".24"/>')
parts.append(t(1566,855,"Updated "+datetime.now(timezone.utc).strftime("%d %b %Y · %H:%M UTC")+" · scheduled refresh",13,"#7697B5",False,"end"))
parts.append("</svg>")
path=Path("assets/github-analytics-live.svg")
path.parent.mkdir(parents=True,exist_ok=True)
path.write_text("\n".join(parts),encoding="utf-8")
print(f"Updated {path}: {sum(daily.values())} lifetime contributions, {current[0]} day current streak.")
