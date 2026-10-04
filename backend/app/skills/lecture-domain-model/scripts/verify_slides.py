#!/usr/bin/env python3
"""
Verify slide (:Slide) Cypher files against the lecture domain model.

Hard checks (exit 1 on failure):
  - Slide ids are unique
  - every COVERS target is a *defined* :Concept node (no typos / removed nodes)
  - every Slide carries all eight required properties
    (id, title, pageNumber, source, lecture, chapter, chapterIndex, chapterName)
  - every :Concept of a chapter that has slides is COVERED by at least one slide
    (no chapter concept may be left without a source slide)

Reported as INFO (never fail): slides without a COVERS edge — content-less slides
(table-of-contents / agenda / divider) that are removed automatically after loading,
so avoid creating them in the first place.

Usage:
  python verify_slides.py --domain "domain.cypher" --slides "*_slides.cypher"
"""
import argparse, glob, re, sys
from collections import defaultdict

CONCEPT_DEF = re.compile(r"MERGE \(\w+:Concept \{id:'([^']+)'\}\)")
# A Slide MERGE statement up to its terminating ';'
SLIDE_STMT = re.compile(
    r"MERGE \(\w+:Slide \{id:'([^']+)'\}\)(.*?);", re.DOTALL
)
COVERS = re.compile(
    r"\(\w+:Slide \{id:'([^']+)'\}\),\s*\(\w+:Concept \{id:'([^']+)'\}\)\s*"
    r"MERGE \(\w+\)-\[:COVERS\]->\(\w+\)"
)

REQUIRED = ["id", "title", "pageNumber", "source",
            "lecture", "chapter", "chapterIndex", "chapterName"]


def expand(globs):
    """
    Expand shell globs into a sorted list of file paths.

    :param globs: The glob patterns.
    :return: The matching files, sorted per pattern.
    """
    out = []
    for g in globs:
        out.extend(sorted(glob.glob(g)))
    return out


def chapter_of(nid):
    """
    Infer the chapter from an id with a <CODE>_CHNN prefix.

    :param nid: The node id.
    :return: The chapter prefix, or "?" if the id has none.
    """
    m = re.match(r"([A-Za-z]+_CH\d+)", nid)
    return m.group(1) if m else "?"


def main():
    """
    Run all slide checks and exit with 0 if the hard checks pass, 1 otherwise.

    :return: None
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", action="append", required=True)
    ap.add_argument("--slides", action="append", required=True)
    args = ap.parse_args()

    defined = set()
    for f in expand(args.domain):
        defined |= set(CONCEPT_DEF.findall(open(f, encoding="utf-8").read()))

    slide_ids, covers = [], []
    missing_props = []  # (slide_id, [missing])
    for f in expand(args.slides):
        t = open(f, encoding="utf-8").read()
        for sid, body in SLIDE_STMT.findall(t):
            slide_ids.append(sid)
            present = set(re.findall(r"\b\w+\.(\w+)\s*=", body)) | {"id"}
            miss = [p for p in REQUIRED if p not in present]
            if miss:
                missing_props.append((sid, miss))
        covers += COVERS.findall(t)

    print(f"Concept nodes: {len(defined)} | Slides: {len(slide_ids)} | COVERS: {len(covers)}")
    print("-" * 60)
    ok = True

    dup = sorted({s for s in slide_ids if slide_ids.count(s) > 1})
    print(("FAIL  duplicate Slide ids: " + str(dup)) if dup else "PASS  Slide ids unique")
    ok &= not dup

    missing_concepts = sorted({c for _, c in covers if c not in defined})
    print(("FAIL  COVERS -> undefined Concept ids: " + str(missing_concepts[:8]))
          if missing_concepts else "PASS  every COVERS target is a defined Concept")
    ok &= not missing_concepts

    print(("FAIL  slides missing required properties: " + str(missing_props[:8]))
          if missing_props else "PASS  every Slide has all required properties")
    ok &= not missing_props

    covered_targets = {c for _, c in covers}
    slide_chapters = {chapter_of(s) for s in slide_ids}
    required = {c for c in defined if chapter_of(c) in slide_chapters}
    uncovered = sorted(required - covered_targets)
    print(("FAIL  Concepts not covered by any Slide: " + str(uncovered[:8])
           + (f" (+{len(uncovered) - 8} more)" if len(uncovered) > 8 else ""))
          if uncovered else "PASS  every chapter Concept is covered by >= 1 Slide")
    ok &= not uncovered

    print("-" * 60)
    covered = {s for s, _ in covers}
    no_cover = sorted(set(slide_ids) - covered)
    print(f"INFO  slides without a COVERS edge ({len(no_cover)}, removed automatically): "
          f"{no_cover or 'none'}")
    cnt = defaultdict(int)
    for s, _ in covers:
        cnt[s] += 1
    multi = sum(1 for s in set(slide_ids) if cnt[s] > 1)
    print(f"INFO  slides covering multiple concepts: {multi} / {len(slide_ids)}")

    print("-" * 60)
    print("RESULT:", "HARD CHECKS PASSED" if ok else "PROBLEMS FOUND (see FAIL lines)")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
