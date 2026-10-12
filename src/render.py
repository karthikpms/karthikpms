"""Render profile hero SVGs from GitHub contribution data.

Usage: python3 render.py <stats.json> <outdir> [--static]
--static freezes every animation at its resting frame (for previews).
"""
import collections
import datetime as dt
import json
import math
import sys
from html import escape

MONO = "ui-monospace,'SF Mono',SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"


# ---------------------------------------------------------------- data

def load(stats_path):
    """stats.json is written by fetch.py and holds aggregates only (no repo names, no messages)."""
    raw = json.load(open(stats_path))
    days = raw["days"]
    counts = [d["count"] for d in days]
    streak = best_streak = 0
    for c in counts:
        streak = streak + 1 if c else 0
        best_streak = max(best_streak, streak)
    peak = max(days, key=lambda d: d["count"])
    return {
        "days": days,
        "counts": counts,
        "total": sum(counts),
        "active": sum(1 for c in counts if c),
        "streak": best_streak,
        "peak": {"date": peak["date"], "contributionCount": peak["count"]},
        "weekend": sum(d["count"] for d in days if d["weekday"] in (0, 6)),
        "hours": raw["hours"],
        "kinds": collections.Counter(raw["kinds"]),
        "n_commits": raw["n_commits"],
    }


def fmt_date(iso):
    return dt.date.fromisoformat(iso).strftime("%d %b %Y")


STATIC = "--static" in sys.argv


def svg(w, h, body, style="", title=""):
    if STATIC:
        style += "*{animation:none!important}"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'role="img" aria-label="{escape(title)}"><title>{escape(title)}</title>'
        f"<style>{style}</style>{body}</svg>\n"
    )


# ---------------------------------------------------------------- A: signal

def render_signal(d):
    """The contribution year drawn as an audio waveform, with a sweeping playhead."""
    W, H = 1000, 420
    x0, x1, mid, amp = 48, W - 48, 196, 112
    n = len(d["counts"])
    step = (x1 - x0) / n
    peak = max(d["counts"])
    bw = step * 0.58

    def height(c):
        return max(4, amp * math.log1p(c) / math.log1p(peak))

    bars = []
    for i, c in enumerate(d["counts"]):
        x = x0 + i * step
        if c == 0:
            bars.append(f'<rect x="{x:.2f}" y="{mid - 1}" width="{bw:.2f}" height="2" rx="1" class="z"/>')
        else:
            h = height(c)
            bars.append(f'<rect x="{x:.2f}" y="{mid - h:.2f}" width="{bw:.2f}" height="{2 * h:.2f}" rx="{bw / 2:.2f}"/>')
    wave = "".join(bars)

    ticks = []
    for i, day in enumerate(d["days"]):
        if day["date"][8:] == "01":
            x = x0 + i * step
            ticks.append(
                f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{mid + amp + 16}" y2="{mid + amp + 22}" class="rule"/>'
                f'<text x="{x + 5:.1f}" y="{mid + amp + 23}" class="mono s10 dim">'
                f'{dt.date.fromisoformat(day["date"]).strftime("%b").upper()}</text>'
            )

    pi = next(i for i, x in enumerate(d["days"]) if x["date"] == d["peak"]["date"])
    px = x0 + pi * step + bw / 2
    ph = height(d["peak"]["contributionCount"])
    span = x1 - x0
    style = f"""
      .mono{{font-family:{MONO}}} .sans{{font-family:{SANS}}}
      .s10{{font-size:10px;letter-spacing:.14em}} .s11{{font-size:11px;letter-spacing:.06em}}
      .dim{{fill:#596072}} .mid{{fill:#9aa3b5}} .hi{{fill:#f1f3f8}}
      .rule{{stroke:#262b38;stroke-width:1}}
      .base rect{{fill:url(#heat);opacity:.34}} .base .z{{opacity:.5}}
      .hot rect{{fill:url(#heat)}}
      #sweep{{animation:sweep 10s cubic-bezier(.5,0,.3,1) infinite}}
      #head{{opacity:0;animation:head 10s cubic-bezier(.5,0,.3,1) infinite}}
      @keyframes sweep{{0%{{width:0}}80%,100%{{width:{span}px}}}}
      @keyframes head{{0%{{transform:translateX(0);opacity:1}}80%{{transform:translateX({span}px);opacity:1}}90%,100%{{transform:translateX({span}px);opacity:0}}}}
      .rec{{animation:blink 1.2s steps(2,end) infinite}}
      @keyframes blink{{50%{{opacity:.15}}}}
      .ring{{transform-origin:{px:.1f}px {mid - ph:.1f}px;animation:ring 2.4s ease-out infinite}}
      @keyframes ring{{0%{{transform:scale(.4);opacity:.9}}100%{{transform:scale(2.6);opacity:0}}}}
    """
    body = f"""
      <defs>
        <linearGradient id="heat" x1="{x0}" x2="{x1}" gradientUnits="userSpaceOnUse">
          <stop offset="0" stop-color="#2ee6c0"/><stop offset=".4" stop-color="#5b8cff"/>
          <stop offset=".72" stop-color="#b36bff"/><stop offset="1" stop-color="#ff7a45"/>
        </linearGradient>
        <clipPath id="played"><rect id="sweep" x="{x0}" y="0" width="{span}" height="{H}"/></clipPath>
        <radialGradient id="bg" cx=".5" cy=".45" r=".75"><stop offset="0" stop-color="#161a2b"/><stop offset="1" stop-color="#0a0b10"/></radialGradient>
        <filter id="glow" x="-5%" y="-30%" width="110%" height="160%"><feGaussianBlur stdDeviation="4" result="b"/>
          <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
      </defs>
      <rect width="{W}" height="{H}" rx="16" fill="url(#bg)"/>
      <rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="16" fill="none" stroke="#1f2431"/>

      <circle cx="{x0 + 5}" cy="42" r="5" fill="#ff4d5e" class="rec"/>
      <text x="{x0 + 18}" y="46" class="mono s11 hi">REC</text>
      <text x="{x0 + 56}" y="46" class="mono s11 mid">karthik.wav  ·  365 days  ·  1 sample per day  ·  private repos included</text>
      <text x="{x1}" y="46" text-anchor="end" class="mono s11 hi">{d['total']:,} events</text>

      <line x1="{x0}" x2="{x1}" y1="{mid}" y2="{mid}" class="rule"/>
      <g class="base">{wave}</g>
      <g class="hot" clip-path="url(#played)" filter="url(#glow)">{wave}</g>
      <g id="head" opacity="0"><line x1="{x0}" x2="{x0}" y1="{mid - amp - 12}" y2="{mid + amp + 12}" stroke="#f1f3f8" stroke-width="1.25"/>
        <rect x="{x0 - 4}" y="{mid - amp - 18}" width="8" height="8" rx="1.5" fill="#f1f3f8"/></g>

      <circle cx="{px:.1f}" cy="{mid - ph:.1f}" r="6" fill="none" stroke="#ff7a45" class="ring"/>
      <circle cx="{px:.1f}" cy="{mid - ph:.1f}" r="2.5" fill="#ff7a45"/>
      <line x1="{px:.1f}" x2="{px:.1f}" y1="{mid - ph - 8:.1f}" y2="72" stroke="#ff7a45" stroke-dasharray="2 3" opacity=".7"/>
      <text x="{px + 8:.1f}" y="76" class="mono s10" fill="#ff9a6b">CLIPPED · {d['peak']['contributionCount']} IN ONE DAY · {fmt_date(d['peak']['date']).upper()}</text>
      {''.join(ticks)}

      <line x1="{x0}" x2="{x1}" y1="{H - 86}" y2="{H - 86}" class="rule"/>
      <text x="{x0}" y="{H - 46}" class="sans hi" font-size="28" font-weight="700" letter-spacing="-.02em">Karthik Sakthivel</text>
      <text x="{x0}" y="{H - 22}" class="sans mid" font-size="14">Builds voice AI that talks back, and every layer of the stack it runs on.</text>
      <text x="{x1}" y="{H - 46}" text-anchor="end" class="mono s10 mid">{d['active']} ACTIVE DAYS  ·  {d['streak']}-DAY STREAK</text>
      <text x="{x1}" y="{H - 24}" text-anchor="end" class="mono s10 dim">{d['weekend']:,} CONTRIBUTIONS ON WEEKENDS. WEEKENDS ARE A SUGGESTION.</text>
    """
    return svg(W, H, body, style, f"Karthik's last 365 days of GitHub contributions drawn as an audio waveform: {d['total']} contributions.")


# ---------------------------------------------------------------- B: status page

def render_status(d):
    W, H = 1000, 600
    x0, x1 = 44, W - 44
    n = len(d["counts"])
    step = (x1 - x0) / n
    uptime = 100 * d["active"] / n

    def colour(c):
        if c == 0:
            return "#272b34"
        if c < 8:
            return "#1c6b44"
        if c < 25:
            return "#25a35a"
        if c < 60:
            return "#3fd47a"
        return "#a6ffc6"

    bars = "".join(
        f'<rect x="{x0 + i * step:.2f}" y="146" width="{step * 0.68:.2f}" height="40" rx="1.2" fill="{colour(c)}"/>'
        for i, c in enumerate(d["counts"])
    )
    pi = next(i for i, x in enumerate(d["days"]) if x["date"] == d["peak"]["date"])
    comps = [
        ("Voice agents", "streaming STT → LLM tools → TTS · Indic languages · barge-in"),
        ("SaaS backends", "multi-tenant TypeScript · Bun / Node · Postgres · workers"),
        ("Mobile", "Flutter · Dart · Maestro end-to-end flows"),
        ("Infrastructure", "AWS · Terraform · Docker · Caddy · ISO 27001 controls"),
    ]
    rows = []
    for i, (name, sub) in enumerate(comps):
        y = 282 + i * 34
        rows.append(
            f'<line x1="{x0}" x2="{x1}" y1="{y + 13}" y2="{y + 13}" stroke="#1b1f27"/>'
            f'<text x="{x0}" y="{y}" class="sans t14 hi" font-weight="600">{name}</text>'
            f'<text x="{x0 + 150}" y="{y}" class="mono t12 dim">{escape(sub)}</text>'
            f'<text x="{x1}" y="{y}" text-anchor="end" class="sans t13 ok">Operational</text>'
            f'<circle cx="{x1 - 92}" cy="{y - 4.5}" r="4" fill="#3fd47a" class="pulse" style="animation-delay:{i * .5}s"/>'
        )
    incidents = [
        ("warn", fmt_date(d["peak"]["date"]), "Elevated commit rate",
         f'{d["peak"]["contributionCount"]} contributions in 24h. Root cause: someone said "quick change". Resolved: it shipped.'),
        ("warn", "Ongoing", "fix: outnumbers feat:",
         f'{d["kinds"]["fix"]} to {d["kinds"]["feat"]} across the last {d["n_commits"]:,} commits. Not a bug. This is what production looks like.'),
        ("ok", "Never", "Deploys between 03:00 and 06:00 IST",
         f'{sum(d["hours"][3:6])} commits in that window, against {sum(d["hours"][0:3])} between midnight and 3am. Sleep is a scheduled job.'),
    ]
    inc = []
    for i, (cls, when, title, desc) in enumerate(incidents):
        y = 454 + i * 46
        inc.append(
            f'<text x="{x0}" y="{y}" class="mono t12 dim">{escape(when)}</text>'
            f'<text x="{x0 + 110}" y="{y}" class="sans t13 {cls}" font-weight="600">{escape(title)}</text>'
            f'<text x="{x0 + 110}" y="{y + 19}" class="sans t13 mid">{escape(desc)}</text>'
        )
    style = f"""
      .mono{{font-family:{MONO}}} .sans{{font-family:{SANS}}}
      .t11{{font-size:11px}} .t12{{font-size:12px}} .t13{{font-size:13px}} .t14{{font-size:14px}}
      .cap{{font-size:11px;letter-spacing:.14em}}
      .hi{{fill:#e9edf3}} .mid{{fill:#a3abb9}} .dim{{fill:#687082}} .ok{{fill:#3fd47a}} .warn{{fill:#ffb648}}
      .pulse{{animation:pulse 2.4s ease-in-out infinite}}
      @keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.3}}}}
      .today{{animation:pulse 1.6s ease-in-out infinite}}
    """
    body = f"""
      <rect width="{W}" height="{H}" rx="16" fill="#0d1015"/>
      <rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="16" fill="none" stroke="#1f242d"/>
      <text x="{x0}" y="46" class="sans hi" font-size="17" font-weight="700">status<tspan class="dim" font-weight="400">.karthik</tspan></text>
      <text x="{x1}" y="46" text-anchor="end" class="mono t12 dim">rebuilt nightly by a GitHub Action · no third-party widgets</text>

      <rect x="{x0}" y="70" width="{x1 - x0}" height="50" rx="10" fill="#10291b" stroke="#1a4a2e"/>
      <circle cx="{x0 + 24}" cy="95" r="6.5" fill="#3fd47a" class="pulse"/>
      <text x="{x0 + 42}" y="101" class="sans hi" font-size="17" font-weight="600">All systems operational</text>
      <text x="{x1 - 18}" y="100" text-anchor="end" class="mono t12 mid">{d['total']:,} contributions · trailing 365 days</text>

      {bars}
      <rect x="{x0 + (n - 1) * step:.2f}" y="146" width="{step * 0.68:.2f}" height="40" rx="1.2" fill="#a6ffc6" class="today"/>
      <text x="{x0}" y="206" class="mono t11 dim">365 days ago</text>
      <text x="{(x0 + x1) / 2}" y="206" text-anchor="middle" class="mono t12 mid">{uptime:.1f}% uptime  ·  grey bars are scheduled maintenance (sleep)</text>
      <text x="{x1}" y="206" text-anchor="end" class="mono t11 dim">today</text>

      <text x="{x0}" y="250" class="mono cap dim">COMPONENTS</text>
      {''.join(rows)}

      <text x="{x0}" y="424" class="mono cap dim">PAST INCIDENTS</text>
      {''.join(inc)}
    """
    return svg(W, H, body, style, f"Status page for Karthik: all systems operational, {uptime:.1f}% of the last 365 days active.")


# ---------------------------------------------------------------- C: man page

def render_man(d):
    W, H = 1000, 560
    lh = 19
    night = sum(d["hours"][0:3])
    dawn = sum(d["hours"][3:6])
    lines = [
        ("h", "KARTHIK(1)".ljust(52) + "Pyramidion Manual".ljust(52) + "KARTHIK(1)"),
        ("", ""),
        ("s", "NAME"),
        ("t", "       karthik - turns ambiguous requirements into production systems"),
        ("", ""),
        ("s", "SYNOPSIS"),
        ("t", "       karthik [--voice-ai] [--flutter] [--backend] [--terraform apply]"),
        ("t", "               [-y | --ship-it] < requirements.docx > production"),
        ("", ""),
        ("s", "OPTIONS"),
        ("t", "       --voice-ai     Phone agents that listen, interrupt politely, and call tools."),
        ("t", "       --flutter      One codebase, two app stores, zero excuses."),
        ("t", "       --backend      Multi-tenant TypeScript. Bun when allowed, Node when not."),
        ("t", "       --terraform    Infrastructure you can delete and rebuild before lunch."),
        ("", ""),
        ("s", "EXIT STATUS"),
        ("t", f"       0      Shipped. ({d['total']:,} times in the last 365 days.)"),
        ("t", "       3      Prowler found something. Fixed before you read this line."),
        ("", ""),
        ("s", "BUGS"),
        ("t", f"       fix: commits outnumber feat: commits {d['kinds']['fix']} to {d['kinds']['feat']}. Working as intended."),
        ("t", f"       {night} of the last {d['n_commits']:,} commits landed between 00:00 and 03:00 IST. {dawn} landed"),
        ("t", "       between 03:00 and 06:00. That is the only maintenance window."),
    ]
    style = f"""
      .mono{{font-family:{MONO};font-size:13px;white-space:pre}}
      .h{{fill:#6b7280}} .s{{fill:#f4f4f5;font-weight:700}} .t{{fill:#c7cbd3}}
      .ln{{animation:in .18s ease-out backwards}}
      @keyframes in{{from{{opacity:0}}}}
      .typed{{width:110px;animation:type 1.1s steps(12,end) .3s backwards}}
      @keyframes type{{from{{width:0}}to{{width:110px}}}}
      .cur{{animation:blink 1s steps(2,end) infinite}}
      @keyframes blink{{50%{{opacity:0}}}}
    """
    out = [
        f'<rect width="{W}" height="{H}" rx="12" fill="#0c0c0e"/>',
        f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="12" fill="none" stroke="#26262b"/>',
        f'<rect width="{W}" height="34" rx="12" fill="#18181b"/><rect y="22" width="{W}" height="12" fill="#18181b"/>',
        '<circle cx="22" cy="17" r="6" fill="#ff5f57"/><circle cx="42" cy="17" r="6" fill="#febc2e"/><circle cx="62" cy="17" r="6" fill="#28c840"/>',
        f'<text x="{W / 2}" y="21" text-anchor="middle" class="mono" fill="#71717a" style="font-size:12px">karthik@pyramidion: ~</text>',
        '<clipPath id="tc"><rect class="typed" x="44" y="50" width="110" height="24"/></clipPath>',
        '<text x="28" y="66" class="mono" fill="#4ade80">$</text>',
        '<text x="44" y="66" class="mono t" clip-path="url(#tc)"> man karthik</text>',
    ]
    y = 98
    for i, (cls, text) in enumerate(lines):
        if text:
            out.append(
                f'<text x="28" y="{y}" class="mono ln {cls}" style="animation-delay:{1.6 + i * 0.07:.2f}s">{escape(text)}</text>'
            )
        y += lh
    out.append(
        f'<rect x="28" y="{y - 2}" width="320" height="18" fill="#e4e4e7" class="ln" style="animation-delay:{1.6 + len(lines) * 0.07:.2f}s"/>'
        f'<text x="34" y="{y + 11}" class="mono ln" style="animation-delay:{1.6 + len(lines) * 0.07:.2f}s;fill:#0c0c0e">Manual page karthik(1) line 1 (press q)</text>'
        f'<rect x="352" y="{y - 2}" width="8" height="18" fill="#e4e4e7" class="cur"/>'
    )
    return svg(W, H, "".join(out), style, "man karthik: a Unix manual page describing Karthik.")


if __name__ == "__main__":
    data = load(sys.argv[1])
    outdir = sys.argv[2]
    for name, fn in [("signal", render_signal), ("status", render_status), ("man", render_man)]:
        with open(f"{outdir}/{name}.svg", "w") as f:
            f.write(fn(data))
    print("rendered", data["total"], data["active"], data["streak"], data["kinds"].most_common(3))
