"""Weekly AI safety research updates for aisafetyresearch.co.uk.

1. Collects new papers and posts from arXiv, the Alignment Forum and LessWrong.
2. Asks Gemini which items relate to each of our research questions and to
   summarise them, using only the text we collected.
3. Checks Gemini's answer: links always come from our own collected data,
   never from the model, and anything that doesn't match is dropped.
4. Writes data/research-updates.json and pr-body.md (the review notes).

Needs the GEMINI_API_KEY environment variable. Optional settings:
GEMINI_MODEL (otherwise the newest stable "flash" model is chosen),
DAYS (how far back to look, default 8), MAX_PER_QUESTION (default 4).
Uses only the Python standard library.
"""

import csv
import datetime as dt
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

QUESTIONS_CSV = (
    "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ6_xOYEMg6qJRN7T0YQmxfVTwmA0s_"
    "-nVtD2c-uUv3pwshbpK7qbWv1ctTJPyZ3a-x8OeogAh5tSyj/pub?gid=0&single=true&output=csv"
)
DATA_FILE = "data/research-updates.json"
REVIEW_FILE = "pr-body.md"
WEEKS_KEPT = 12
DAYS = int(os.environ.get("DAYS", "8"))
MAX_PER_QUESTION = int(os.environ.get("MAX_PER_QUESTION", "4"))
API = "https://generativelanguage.googleapis.com/v1beta"
UA = "aisafetyresearch.co.uk research updates (contact via site)"

ARXIV_TERMS = [
    '"AI safety"', "alignment", "interpretability", '"chain of thought"',
    '"chain-of-thought"', '"reward hacking"', '"red teaming"', "jailbreak",
    '"dangerous capabilities"', '"model evaluation"', "sandbagging",
    "deception", "scheming", '"sparse autoencoder"', "probing",
    '"compute governance"', '"AI governance"', '"scalable oversight"',
]
FEEDS = [
    ("Alignment Forum", "https://www.alignmentforum.org/feed.xml", False),
    ("LessWrong", "https://www.lesswrong.com/feed.xml?view=curated-rss", True),
    ("LessWrong", "https://www.lesswrong.com/feed.xml?view=frontpage-rss&karmaThreshold=40", True),
]
AI_WORDS = re.compile(
    r"\b(AI|LLMs?|language models?|alignment|interpretab|safety|governance|"
    r"chain[- ]of[- ]thought|reward|eval|agents?|superintelligen|frontier model)",
    re.I,
)


def log(msg):
    print(msg, flush=True)


def get(url, headers=None, data=None, timeout=60):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def clean(text, limit=None):
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"&nbsp;|&#160;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&quot;", '"', text)
    text = re.sub(r"&#39;|&rsquo;|&lsquo;", "'", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit] if limit else text


# ---------- questions ----------

def load_questions():
    rows = list(csv.reader(io.StringIO(get(QUESTIONS_CSV))))
    qs = []
    for r in rows[1:]:
        if r and re.match(r"^Q\d+$", (r[0] or "").strip()) and len(r) > 2 and r[2].strip():
            qs.append({"id": r[0].strip(), "area": r[1].strip(), "question": r[2].strip(),
                       "why": (r[3] if len(r) > 3 else "").strip()})
    if not qs:
        raise SystemExit("No questions found in the questions sheet.")
    return qs


# ---------- sources ----------

def from_arxiv(since):
    terms = " OR ".join("abs:%s" % t for t in ARXIV_TERMS)
    query = "(cat:cs.AI OR cat:cs.LG OR cat:cs.CL OR cat:cs.CY) AND (%s)" % terms
    url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode({
        "search_query": query, "sortBy": "submittedDate", "sortOrder": "descending",
        "start": 0, "max_results": 200,
    })
    ns = {"a": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(get(url, timeout=90))
    items = []
    for e in root.findall("a:entry", ns):
        published = dt.datetime.fromisoformat(e.findtext("a:published", "", ns).replace("Z", "+00:00"))
        if published < since:
            continue
        link = e.findtext("a:id", "", ns).strip()
        link = re.sub(r"v\d+$", "", link).replace("http://", "https://")
        authors = [a.findtext("a:name", "", ns) for a in e.findall("a:author", ns)]
        items.append({
            "source": "arXiv",
            "title": clean(e.findtext("a:title", "", ns)),
            "url": link,
            "authors": ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else ""),
            "published": published.date().isoformat(),
            "text": clean(e.findtext("a:summary", "", ns), 1500),
        })
    return items


def from_feed(name, url, needs_ai_filter, since):
    root = ET.fromstring(get(url))
    items = []
    for it in root.iter("item"):
        try:
            published = parsedate_to_datetime(it.findtext("pubDate", ""))
        except (TypeError, ValueError):
            continue
        if published.tzinfo is None:
            published = published.replace(tzinfo=dt.timezone.utc)
        if published < since:
            continue
        title = clean(it.findtext("title", ""))
        text = clean(it.findtext("description", ""), 1500)
        if needs_ai_filter and not AI_WORDS.search(title + " " + text):
            continue
        author = clean(it.findtext("{http://purl.org/dc/elements/1.1/}creator", "") or it.findtext("author", ""))
        items.append({
            "source": name, "title": title, "url": (it.findtext("link", "") or "").strip(),
            "authors": author, "published": published.date().isoformat(), "text": text,
        })
    return items


def collect(seen):
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=DAYS)
    items, problems = [], []
    try:
        items += from_arxiv(since)
    except Exception as e:  # one source failing shouldn't stop the run
        problems.append("arXiv: %s" % e)
    for name, url, filt in FEEDS:
        try:
            items += from_feed(name, url, filt, since)
        except Exception as e:
            problems.append("%s feed: %s" % (name, e))
    unique, urls = [], set()
    for it in items:
        if it["url"].startswith("https://") and it["url"] not in urls and it["url"] not in seen and it["title"]:
            urls.add(it["url"])
            unique.append(it)
    return unique, problems


# ---------- Gemini ----------

def gemini(path, body=None):
    key = os.environ["GEMINI_API_KEY"]
    headers = {"x-goog-api-key": key, "Content-Type": "application/json"}
    data = json.dumps(body).encode() if body is not None else None
    for attempt in range(5):
        try:
            return json.loads(get(API + path, headers=headers, data=data, timeout=180))
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:300]
            if e.code in (429, 500, 502, 503, 504) and attempt < 4:
                wait = 20 * (attempt + 1)
                log("Gemini returned %s, retrying in %ss" % (e.code, wait))
                time.sleep(wait)
                continue
            raise SystemExit("Gemini request failed (%s): %s" % (e.code, detail))


def pick_model():
    if os.environ.get("GEMINI_MODEL"):
        return os.environ["GEMINI_MODEL"]
    models = gemini("/models?pageSize=200").get("models", [])
    usable = []
    for m in models:
        name = m.get("name", "").split("/")[-1]
        if "generateContent" not in m.get("supportedGenerationMethods", []):
            continue
        if "flash" not in name or re.search(r"lite|image|tts|audio|live|embed|thinking|exp", name):
            continue
        nums = [int(n) for n in re.findall(r"\d+", name.split("flash")[0])] or [0]
        usable.append(("preview" not in name, nums, name))
    if not usable:
        raise SystemExit("No suitable Gemini model found; set GEMINI_MODEL.")
    usable.sort(reverse=True)
    return usable[0][2]


PROMPT = """You help students find recent AI safety research related to specific research questions.

Below are our research questions and a numbered list of new papers and posts. For each item that is clearly and directly relevant to one or more questions, return the item number, the question IDs it relates to, and a summary.

Rules:
- Only include items a student working on that question would genuinely want to read. Leave out loosely related items. It is fine to return very few or none.
- At most {max_per_q} items per question.
- Summaries are two or three plain sentences in British English: what the authors did and what they found or argued. Use only the text given for that item. Do not add facts, numbers or claims that aren't in it. No hype, no links, no markdown.
- If the given text is too thin to say what the item found, say what it sets out to do instead.

Return JSON only, in this form:
{{"matches": [{{"item": 3, "questions": ["Q1"], "summary": "..."}}]}}

Research questions:
{questions}

Items:
{items}
"""


def summarise(model, questions, items):
    qtext = "\n".join("%s (%s): %s %s" % (q["id"], q["area"], q["question"], q["why"]) for q in questions)
    itext = "\n\n".join("[%d] %s | %s\n%s" % (i, it["source"], it["title"], it["text"]) for i, it in enumerate(items))
    body = {
        "contents": [{"role": "user", "parts": [{"text": PROMPT.format(max_per_q=MAX_PER_QUESTION, questions=qtext, items=itext)}]}],
        "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
    }
    res = gemini("/models/%s:generateContent" % model, body)
    try:
        text = "".join(p.get("text", "") for p in res["candidates"][0]["content"]["parts"])
        fence = chr(96) * 3  # strip a markdown code fence if Gemini adds one
        text = re.sub(r"^" + fence + r"(?:json)?|" + fence + r"$", "", text.strip()).strip()
        return json.loads(text).get("matches", [])
    except (KeyError, IndexError, ValueError) as e:
        raise SystemExit("Could not read Gemini's answer: %s" % e)


def validate(matches, items, qids):
    """Keep only well-formed matches. Links and titles always come from our data."""
    kept, per_q, dropped = [], {q: 0 for q in qids}, 0
    for m in matches if isinstance(matches, list) else []:
        try:
            idx = int(m.get("item"))
        except (TypeError, ValueError, AttributeError):
            dropped += 1
            continue
        qs = [q for q in (m.get("questions") or []) if q in qids]
        summary = clean(re.sub(r"https?://\S+", "", str(m.get("summary") or "")))
        if not (0 <= idx < len(items)) or not qs or not (40 <= len(summary) <= 900):
            dropped += 1
            continue
        qs = [q for q in qs if per_q[q] < MAX_PER_QUESTION]
        if not qs:
            continue
        for q in qs:
            per_q[q] += 1
        it = items[idx]
        kept.append({k: it[k] for k in ("title", "url", "source", "authors", "published")} | {"questions": qs, "summary": summary})
    return kept, dropped


# ---------- main ----------

def main():
    if not os.environ.get("GEMINI_API_KEY"):
        raise SystemExit("GEMINI_API_KEY is not set.")
    try:
        with open(DATA_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {"updated": None, "weeks": []}
    seen = {i["url"] for w in data.get("weeks", []) for i in w.get("items", [])}

    questions = load_questions()
    qids = {q["id"] for q in questions}
    items, problems = collect(seen)
    log("Collected %d new items. Problems: %s" % (len(items), problems or "none"))
    for p in problems:
        log("WARNING " + p)

    today = dt.date.today().isoformat()
    model, kept, dropped = None, [], 0
    if items:
        model = pick_model()
        log("Using model %s" % model)
        kept, dropped = validate(summarise(model, questions, items[:250]), items, qids)
    log("Kept %d items, dropped %d malformed." % (len(kept), dropped))

    if kept:
        kept.sort(key=lambda x: x["published"], reverse=True)
        data["weeks"] = ([{"week_of": today, "model": model, "items": kept}] + data.get("weeks", []))[:WEEKS_KEPT]
        data["updated"] = today
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")

    qname = {q["id"]: q["question"] for q in questions}
    lines = ["## Research updates for review", "",
             "Gemini (%s) read %d new papers and posts from the last %d days and matched %d to our questions."
             % (model or "not needed", len(items), DAYS, len(kept)), "",
             "**Before merging:** open a few links and check each summary says what the original says. "
             "To drop an item, edit data/research-updates.json in this pull request and delete it.", ""]
    if problems:
        lines += ["Sources that failed this week: " + "; ".join(problems), ""]
    for q in sorted(qids, key=lambda s: int(s[1:])):
        its = [i for i in kept if q in i["questions"]]
        if its:
            lines += ["### %s: %s" % (q, qname[q]), ""]
            lines += ["- [%s](%s) (%s, %s): %s" % (i["title"], i["url"], i["source"], i["published"], i["summary"]) for i in its]
            lines += [""]
    with open(REVIEW_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as f:
            f.write("\n".join(lines))


if __name__ == "__main__":
    main()
