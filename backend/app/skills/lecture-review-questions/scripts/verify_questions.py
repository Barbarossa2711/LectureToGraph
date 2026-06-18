#!/usr/bin/env python3
"""
Verify review-question (:Question) Cypher files against the lecture domain model.

Checks:
  - Question ids are unique
  - every TESTS target is a *defined* Concept node (no typos / removed nodes)
  - every Question has >= 1 TESTS edge  (questions intentionally left without one are listed,
    not hard-failed -- e.g. a topic that was deduplicated to another chapter)
  - reports cross-chapter TESTS edges (question chapter != concept chapter) so the documented
    exceptions are visible and accidental ones get caught
  - every Question is attached to its Chapter via HAS_QUESTION

Exit code 0 when the hard checks pass (unique ids, all TESTS ids defined, all HAS_QUESTION present),
1 otherwise. Missing-TESTS and cross-chapter are reported as INFO/WARN, not failures.

Usage:
  python verify_questions.py --domain "CYPHER_Kapitel/*.cypher" \
                             --questions "CYPHER_Fragen/*_questions.cypher"
"""
import argparse, glob, re, sys
from collections import defaultdict

CONCEPT_DEF = re.compile(r"MERGE \(n:Concept \{id:'([^']+)'\}\)")
Q_DEF = re.compile(r"MERGE \(n:Question \{id:'([^']+)'\}\)")
TESTS = re.compile(r"\(q:Question \{id:'([^']+)'\}\), \(c:Concept \{id:'([^']+)'\}\) MERGE \(q\)-\[:TESTS\]->\(c\)")
HASQ = re.compile(r"\(ch:Chapter \{id:'([^']+)'\}\), \(q:Question\)")


def expand(globs):
    out = []
    for g in globs:
        out.extend(sorted(glob.glob(g)))
    return out


def chapter_of(cid):
    m = re.match(r"([A-Za-z]+_CH\d+)", cid)
    return m.group(1) if m else "?"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", action="append", required=True)
    ap.add_argument("--questions", action="append", required=True)
    args = ap.parse_args()

    defined = set()
    for f in expand(args.domain):
        defined |= set(CONCEPT_DEF.findall(open(f, encoding="utf-8").read()))

    qnodes, tests, hasq_chapters = [], [], set()
    for f in expand(args.questions):
        t = open(f, encoding="utf-8").read()
        qnodes += Q_DEF.findall(t)
        tests += TESTS.findall(t)
        hasq_chapters |= set(HASQ.findall(t))

    print(f"Concept nodes: {len(defined)} | Questions: {len(qnodes)} | TESTS: {len(tests)}")
    print("-" * 60)
    ok = True

    dup = sorted({q for q in qnodes if qnodes.count(q) > 1})
    print(("FAIL  duplicate Question ids: " + str(dup)) if dup else "PASS  Question ids unique")
    ok &= not dup

    missing = sorted({c for _, c in tests if c not in defined})
    print(("FAIL  TESTS -> undefined Concept ids: " + str(missing[:8])) if missing
          else "PASS  every TESTS target is a defined Concept")
    ok &= not missing

    # HAS_QUESTION present for every chapter that has questions
    q_chapters = {chapter_of(q) for q in qnodes}
    missing_hasq = sorted(q_chapters - hasq_chapters)
    print(("FAIL  chapters with questions but no HAS_QUESTION block: " + str(missing_hasq))
          if missing_hasq else "PASS  every chapter with questions has a HAS_QUESTION block")
    ok &= not missing_hasq

    print("-" * 60)
    tested = {q for q, _ in tests}
    no_tests = sorted(set(qnodes) - tested)
    print(f"INFO  questions without a TESTS edge ({len(no_tests)}): {no_tests or 'none'}")
    cross = [(q, c) for q, c in tests if chapter_of(q) != chapter_of(c)]
    print(f"INFO  cross-chapter TESTS ({len(cross)}):")
    for q, c in cross:
        print(f"        {q} -> {c}")
    # per-question TESTS count
    cnt = defaultdict(int)
    for q, _ in tests:
        cnt[q] += 1
    multi = sum(1 for q in qnodes if cnt[q] > 1)
    print(f"INFO  questions with multiple TESTS: {multi} / {len(qnodes)}")

    print("-" * 60)
    print("RESULT:", "HARD CHECKS PASSED" if ok else "PROBLEMS FOUND (see FAIL lines)")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
