"""TWEA Flywheel scheduled jobs for GitHub Actions.

Usage:  python scripts/run_job.py scan|news|newsletter|reminder

Each job reads the JSON files in data/, asks Claude (with web search where needed),
and writes its results back into data/ and drafts/. The GitHub workflow then opens a
pull request, so a TWEA reviewer approves everything before it reaches the site.
Nothing here posts, submits or emails anything.
"""
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DRAFTS = ROOT / "drafts"
PROMPTS = ROOT / "prompts"
MODEL = os.environ.get("CLAUDE_MODEL") or "claude-sonnet-5-5"
NOW = dt.datetime.now(dt.timezone.utc)
TODAY = NOW.date()
QM = ["January to March", "April to June", "July to September", "October to December"]


# ---------- small helpers ----------
def load(name, default):
    p = DATA / name
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def save(name, value):
    (DATA / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def slug(text, prefix=""):
    s = re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")[:60] or "item"
    return prefix + s


def quarter(d):
    q = (d.month - 1) // 3 + 1
    return f"{d.year}-Q{q}", f"{QM[q - 1]} {d.year}"


def profile():
    p = load("profile.json", {})
    return f"TWEA PROFILE:\n{p.get('text', '')}\n\nBRAND VOICE:\n{p.get('voice', '')}"


def builtin_names():
    """Names already listed inside index.html, so the scan never adds them twice."""
    html = (ROOT / "index.html").read_text(encoding="utf-8") if (ROOT / "index.html").exists() else ""
    return {m.lower() for m in re.findall(r'\bname:"([^"]+)"', html)}


def log_run(task, summary):
    runs = load("runs.json", [])
    runs.append({"id": f"{task}-{TODAY.isoformat()}", "task": task, "ranAt": NOW.isoformat(), "summary": summary})
    save("runs.json", runs[-200:])
    # Shown in the pull request description
    (ROOT / ".last_summary").write_text(summary, encoding="utf-8")


def queue_item(kind, title, source, body, item_id):
    q = load("queue.json", [])
    if any(x.get("id") == item_id for x in q):
        item_id += "-" + NOW.strftime("%H%M")
    q.append({"id": item_id, "kind": kind, "title": title, "source": source, "body": body,
              "status": "needs_review", "auto": True, "createdAt": NOW.isoformat(), "updatedAt": NOW.isoformat()})
    save("queue.json", q)


# ---------- Claude ----------
def ask_claude(prompt, web=True, max_searches=25):
    """Send one job to Claude. Returns the JSON object found between <json> and </json>."""
    import anthropic

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
    tools = [{"type": "web_search_20250305", "name": "web_search", "max_uses": max_searches}] if web else []
    messages = [{"role": "user", "content": prompt}]
    for _ in range(8):  # long searches may pause; continue them
        kwargs = dict(model=MODEL, max_tokens=16000, messages=messages)
        if tools:
            kwargs["tools"] = tools
        resp = client.messages.create(**kwargs)
        if resp.stop_reason == "pause_turn":
            messages = messages + [{"role": "assistant", "content": resp.content}]
            continue
        break
    text = "".join(getattr(b, "text", "") for b in resp.content if getattr(b, "type", "") == "text")
    m = re.search(r"<json>\s*(.*?)\s*</json>", text, re.S)
    raw = m.group(1) if m else text[text.find("{"): text.rfind("}") + 1]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise SystemExit("Claude's reply did not contain valid JSON. Nothing was changed.\n\n" + text[:3000])


def fill(template, **values):
    t = (PROMPTS / template).read_text(encoding="utf-8")
    for k, v in values.items():
        t = t.replace("{{" + k + "}}", v)
    return t


# ---------- jobs ----------
LANES = {"apply", "partner", "signpost", "watch", "filtered"}
TYPES = {"Grant", "Prize", "Accelerator", "Investment", "Programme", "Fellowship", "In-kind"}


def job_scan():
    opps = load("opps.json", [])
    stories = [s for s in load("stories.json", []) if not s.get("example")]
    known = builtin_names() | {o.get("name", "").lower() for o in opps}
    out = ask_claude(fill("scan.md", PROFILE=profile(), TODAY=TODAY.isoformat(),
                          KNOWN="\n".join(sorted(known)) or "(none)",
                          STORIES=json.dumps(stories[:12], ensure_ascii=False)))
    added, bids = [], 0
    for o in out.get("opps", []):
        name = str(o.get("name", "")).strip()
        if not name or name.lower() in known:
            continue
        o["id"] = slug(f"{o.get('funder', '')} {name}")
        o["lane"] = o.get("lane") if o.get("lane") in LANES else "watch"
        o["type"] = o.get("type") if o.get("type") in TYPES else "Grant"
        o.update({"addedBy": "scan", "foundAt": NOW.isoformat(), "addedAt": NOW.isoformat()})
        opps.append(o)
        known.add(name.lower())
        added.append(o)
    save("opps.json", opps)
    for b in out.get("bids", [])[:3]:
        body = str(b.get("body", "")).strip()
        if body:
            sid = slug(b.get("title", "bid"), "bid-")
            (DRAFTS / "bids" / f"{TODAY.isoformat()}-{sid}.md").write_text(body + "\n", encoding="utf-8")
            queue_item("Bid outline", b.get("title", "Bid outline"), b.get("title", ""), body, sid)
            bids += 1
    lanes = {}
    for o in added:
        lanes[o["lane"]] = lanes.get(o["lane"], 0) + 1
    summary = out.get("summary") or f"Added {len(added)} new funding routes ({lanes}), drafted {bids} bid outlines."
    log_run("scan", summary)


def job_news():
    stories = load("stories.json", [])
    known = [{"title": s.get("title"), "date": s.get("date")} for s in stories]
    to_post = [s for s in stories if s.get("consent") and not s.get("postsDrafted") and not s.get("example")][:6]
    out = ask_claude(fill("news.md", PROFILE=profile(), TODAY=TODAY.isoformat(),
                          KNOWN=json.dumps(known, ensure_ascii=False),
                          TO_POST=json.dumps(to_post, ensure_ascii=False)))
    new = 0
    titles = {str(s.get("title", "")).lower() for s in stories}
    for s in out.get("stories", []):
        t = str(s.get("title", "")).strip()
        if not t or t.lower() in titles:
            continue
        s.update({"id": slug(t, "auto-"), "consent": False, "source": "Found online", "createdAt": NOW.isoformat()})
        stories.append(s)
        titles.add(t.lower())
        new += 1
    drafted = 0
    by_id = {s.get("id"): s for s in stories}
    for p in out.get("posts", []):
        sid, body = p.get("story_id"), str(p.get("body", "")).strip()
        if sid in by_id and body:
            (DRAFTS / "posts" / f"{TODAY.isoformat()}-{slug(sid)}.md").write_text(body + "\n", encoding="utf-8")
            queue_item("Social posts", by_id[sid].get("title", ""), by_id[sid].get("title", ""), body, "posts-" + sid)
            by_id[sid]["postsDrafted"] = True
            drafted += 1
    save("stories.json", stories)
    log_run("stories", out.get("summary") or f"Found {new} new items online; drafted posts for {drafted} stories.")


def job_newsletter():
    qid, qlabel = quarter(TODAY)
    stories = [s for s in load("stories.json", [])
               if not s.get("example") and s.get("date") and quarter(dt.date.fromisoformat(s["date"][:10]))[0] == qid]
    signposts = [o for o in load("opps.json", []) if o.get("lane") == "signpost"]
    html = (ROOT / "index.html").read_text(encoding="utf-8") if (ROOT / "index.html").exists() else ""
    builtin = re.findall(r'lane:"signpost"[^}]*?name:"([^"]+)"[^}]*?amount:"([^"]+)"', html)
    out = ask_claude(fill("newsletter.md", PROFILE=profile(), QUARTER=qlabel,
                          STORIES=json.dumps(stories, ensure_ascii=False),
                          SIGNPOSTS=json.dumps(signposts[:10], ensure_ascii=False) + "\nAlso listed in the tool: " + "; ".join(f"{n} ({a})" for n, a in builtin[:12])),
                     web=True, max_searches=5)
    body = str(out.get("body", "")).strip()
    (DRAFTS / "newsletters" / f"{qid}.md").write_text(body + "\n", encoding="utf-8")
    queue_item("Newsletter", f"TWEA newsletter · {qlabel}", qlabel, body, "newsletter-" + qid.lower())
    log_run("newsletter", out.get("summary") or f"Newsletter draft built from {len(stories)} stories.")


def job_reminder():
    """No AI needed: writes the GitHub issue text for the quarter-end story reminder."""
    qid, qlabel = quarter(TODAY)
    stories = [s for s in load("stories.json", [])
               if not s.get("example") and s.get("date") and quarter(dt.date.fromisoformat(s["date"][:10]))[0] == qid]
    gaps = []
    if len(stories) < 3:
        gaps.append(f"Only {len(stories)} {'story' if len(stories) == 1 else 'stories'} so far. Aim for 3 or more.")
    if not any(s.get("type") == "Founder win" for s in stories):
        gaps.append("No founder win yet, so there's nothing for the spotlight.")
    unchecked = [s for s in stories if not s.get("consent")]
    if unchecked:
        gaps.append(f"{len(unchecked)} stories aren't marked OK to share yet.")
    if not any(s.get("numbers") for s in stories):
        gaps.append("No numbers yet (people reached, founders helped, money raised).")
    lines = [f"The {qlabel} newsletter draft will be built automatically on the 20th.", "",
             "**Stories so far**"] + [f"- {s.get('date', '')[:10]} · {s.get('title', '')}" for s in stories] + \
            ["", "**Gaps**"] + [f"- {g}" for g in gaps or ["None. Great work!"]] + \
            ["", "Please add missing stories to `data/stories.json` (or ask Giulio) by the 19th."]
    (ROOT / ".issue_body.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    log_run("nudge", f"Reminder issued: {len(stories)} stories, {len(gaps)} gaps.")


if __name__ == "__main__":
    jobs = {"scan": job_scan, "news": job_news, "newsletter": job_newsletter, "reminder": job_reminder}
    if len(sys.argv) != 2 or sys.argv[1] not in jobs:
        raise SystemExit("Usage: python scripts/run_job.py " + "|".join(jobs))
    if sys.argv[1] != "reminder" and not os.environ.get("ANTHROPIC_API_KEY"):
        print("No ANTHROPIC_API_KEY secret is set, so this job was skipped. Nothing was changed.")
        sys.exit(0)
    DATA.mkdir(exist_ok=True)
    for d in ("bids", "posts", "newsletters"):
        (DRAFTS / d).mkdir(parents=True, exist_ok=True)
    jobs[sys.argv[1]]()
