#!/usr/bin/env python3
"""Fail if site copy claims generators are tested/compared when they are not in the scores data.

Checks "claim contexts" (home hero, FAQ section, JSON-LD, meta/og/twitter descriptions,
llms.txt, llms-full.txt, feed.xml). Any sentence there that names a generator NOT present in
site/data/scores.csv must also carry a future/queued qualifier (queued, next, planned, not yet ...).
Also bans phrases that imply multi-generator testing is already live.

Usage: python3 scripts/lint_claims.py   (exit 1 on violations). Runs in CI before Pages deploy.
"""
import csv, html, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = ROOT / "site"

# canonical generator -> regex of names/aliases
GENERATORS = {
    "meshy": r"\bmeshy\b",
    "tripo": r"\btripo(?:3d|sr)?\b",
    "rodin": r"\b(?:rodin|hyper3d)\b",
    "hunyuan3d": r"\bhunyuan\s?3d(?:-?\d(?:\.\d)?)?\b|\bhunyuan\b",
    "trellis": r"\btrellis\b",
    "hitem3d": r"\b(?:hitem3d|hi3d)\b",
}
QUALIFIERS = re.compile(
    r"\b(queued|queue|next|planned|plan|not yet|coming|will|roadmap|need(?:s)? (?:a )?(?:paid|budget)|"
    r"budget ok|reserved|unscored|once)\b", re.I)
BANNED = [
    r"runs? the same (?:locked )?prompts through",
    r"through several generators",
    r"added weekly",
    r"which generators need that cleanup and which don",
]
# possessive vendor mentions ("Meshy's own check") are about the vendor's product, not our test claim
POSSESSIVE = re.compile(
    r"(meshy|tripo|rodin|hitem3d)(?:'|’|&#x27;|&rsquo;)s\b"
    r"|\b(meshy|tripo|rodin|hitem3d) (?:output|already has)\b", re.I)


def scored_generators():
    gens = set()
    with open(SITE / "data" / "scores.csv", newline="") as f:
        for row in csv.DictReader(f):
            name = row["generator"].lower()
            for key, rx in GENERATORS.items():
                if re.search(rx, name, re.I):
                    gens.add(key)
    return gens


def strip_tags(s):
    return html.unescape(re.sub(r"<[^>]+>", " ", s))


def contexts():
    for p in sorted(SITE.rglob("*.html")):
        s = p.read_text(encoding="utf-8")
        rel = p.relative_to(ROOT)
        for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', s, re.S):
            try:
                json.loads(m.group(1))
            except json.JSONDecodeError as e:
                yield rel, "JSON-LD", None, f"invalid JSON-LD: {e}"
            yield rel, "JSON-LD", m.group(1), None
        for m in re.finditer(r'<meta (?:name|property)="(?:og:|twitter:)?description" content="([^"]*)"', s):
            yield rel, "meta description", m.group(1), None
        for m in re.finditer(r'<section class="wrap hero">(.*?)</section>', s, re.S):
            yield rel, "hero", strip_tags(m.group(1)), None
        for m in re.finditer(r'<section[^>]*id="faq"[^>]*>(.*?)</section>', s, re.S):
            yield rel, "FAQ", strip_tags(m.group(1)), None
    for name in ("llms.txt", "llms-full.txt", "feed.xml"):
        p = SITE / name
        if p.exists():
            yield p.relative_to(ROOT), name, p.read_text(encoding="utf-8"), None


def main():
    scored = scored_generators()
    if not scored:
        print("lint_claims: no generators found in site/data/scores.csv", file=sys.stderr)
        return 1
    errors = []
    for rel, ctx, text, err in contexts():
        if err:
            errors.append(f"{rel} [{ctx}] {err}")
            continue
        for rx in BANNED:
            for m in re.finditer(rx, text, re.I):
                errors.append(f"{rel} [{ctx}] banned live-claim phrase: '{m.group(0)}'")
        for sent in re.split(r"(?<=[.!?])\s+|\n+", text):
            clean = POSSESSIVE.sub("", sent)
            unscored = [k for k, rx in GENERATORS.items() if k not in scored and re.search(rx, clean, re.I)]
            if unscored and not QUALIFIERS.search(sent):
                errors.append(f"{rel} [{ctx}] names unscored {unscored} without queued/next qualifier: "
                              f"{' '.join(sent.split())[:160]}")
    if errors:
        print("lint_claims FAILED (scored: %s)" % ", ".join(sorted(scored)))
        for e in errors:
            print("  -", e)
        return 1
    print("lint_claims OK (scored generators: %s)" % ", ".join(sorted(scored)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
