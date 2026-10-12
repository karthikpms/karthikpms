"""Fetch contribution and commit aggregates for the profile renderer.

Usage: python3 fetch.py <login> <stats.json>

GITHUB_TOKEN   reads the public contribution calendar (private contributions show up
               as anonymous counts when the profile setting is on).
PROFILE_TOKEN  optional read-only token that can see private repos; used for commit
               hour-of-day and conventional-commit counts. Without it the previous
               commit aggregates in stats.json are kept.

Only aggregates are written: no repository names, no commit messages.
"""
import collections
import datetime as dt
import json
import os
import sys
import urllib.parse
import urllib.request

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
API = "https://api.github.com"


def request(url, token, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def calendar(login, token):
    query = """query($login:String!){user(login:$login){contributionsCollection{
      contributionCalendar{weeks{contributionDays{date contributionCount weekday}}}}}}"""
    data = request(f"{API}/graphql", token, {"query": query, "variables": {"login": login}})
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return [
        {"date": d["date"], "count": d["contributionCount"], "weekday": d["weekday"]}
        for w in weeks
        for d in w["contributionDays"]
    ]


def commit_aggregates(login, token):
    since = (dt.date.today() - dt.timedelta(days=365)).isoformat()
    hours = [0] * 24
    kinds = collections.Counter()
    n = 0
    for page in range(1, 11):  # search API caps at 1,000 results
        q = urllib.parse.quote(f"author:{login} committer-date:>{since}")
        items = request(f"{API}/search/commits?q={q}&sort=committer-date&per_page=100&page={page}", token)["items"]
        for item in items:
            when = dt.datetime.fromisoformat(item["commit"]["author"]["date"].replace("Z", "+00:00"))
            hours[when.astimezone(IST).hour] += 1
            subject = item["commit"]["message"].split("\n", 1)[0]
            if ":" in subject:
                kinds[subject.split(":")[0].split("(")[0].strip().lower()] += 1
            n += 1
        if len(items) < 100:
            break
    keep = ("feat", "fix", "test", "refactor", "perf", "docs", "chore")
    return {"hours": hours, "kinds": {k: kinds[k] for k in keep}, "n_commits": n}


if __name__ == "__main__":
    login, out = sys.argv[1], sys.argv[2]
    previous = json.load(open(out)) if os.path.exists(out) else {}
    stats = {"days": calendar(login, os.environ["GITHUB_TOKEN"])}
    if os.environ.get("PROFILE_TOKEN"):
        stats.update(commit_aggregates(login, os.environ["PROFILE_TOKEN"]))
    else:
        stats.update({k: previous[k] for k in ("hours", "kinds", "n_commits")})
    stats["generated"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes")
    with open(out, "w") as f:
        json.dump(stats, f, separators=(",", ":"))
    print(f"{sum(d['count'] for d in stats['days'])} contributions, {stats['n_commits']} commits sampled")
