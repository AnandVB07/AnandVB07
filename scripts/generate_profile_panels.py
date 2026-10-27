#!/usr/bin/env python3
"""Regenerate the illustrated GitHub profile panels with fresh repository data.

Only repository metadata comes from the API; interests and goals remain authored
static text. Never invent a date or silently publish the wrong information.
"""
from datetime import datetime, timezone
from html import escape
from pathlib import Path
import os
import json
import urllib.request

USER = "AnandVB07"
TOKEN = os.environ["GITHUB_TOKEN"]

def get(url):
    request = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + TOKEN,
        "User-Agent": "AnandVB07-profile-panels",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)

repos = []
for page in range(1, 5):
    result = get(f"https://api.github.com/users/{USER}/repos?per_page=100&page={page}&type=owner")
    repos += result
    if len(result) < 100:
        break

public = [r for r in repos if not r.get("fork") and not r.get("private")]
by_name = {r["name"].lower(): r for r in public}

def last_push(name):
    r = by_name.get(name.lower())
    if r is None:
        return "View project on GitHub"
    pushed = r.get("pushed_at")
    if not pushed:
        return "View public repository"
    date = datetime.fromisoformat(pushed.replace("Z", "+00:00"))
    return "Latest push " + date.strftime("%d %b %Y")

subs = {
    "[[REPO_COUNT]]": str(len(public)),
    "[[PORTFOLIO_UPDATED]]": last_push("AnandPortfolio"),
    "[[FINTECH_UPDATED]]": last_push("zenBull")
}
template = Path("assets/profile-panels-template.svg").read_text(encoding="utf-8")
for key, value in subs.items():
    if key not in template:
        raise RuntimeError(f"Missing SVG template placeholder: {key}")
    template = template.replace(key, escape(value))
if "[[" in template:
    raise RuntimeError("Unresolved SVG placeholder remains")
path = Path("assets/profile-panels-live.svg")
path.write_text(template, encoding="utf-8")
print(f"Refreshed illustrated panels: {len(public)} public repositories")
