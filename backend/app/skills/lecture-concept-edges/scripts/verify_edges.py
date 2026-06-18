#!/usr/bin/env python3
"""
Verify PREREQUISITE / FACILITATOR / SAME_AS edge files against lecture domain-model Cypher.

Checks that matter for a tutoring knowledge graph:
  - every edge endpoint is a *defined* Concept node (Concept -> Concept only)
  - no references to non-existent ids (typos, removed nodes)
  - no duplicate edges, no self-loops (per relationship type)
  - the PREREQUISITE graph is acyclic (a DAG) -> no "A needs B needs A"
  - PREREQUISITE and SAME_AS never describe the same pair (different meaning)
  - FACILITATOR never duplicates a PREREQUISITE or SAME_AS pair (either direction)
  - the COMBINED PREREQUISITE + FACILITATOR graph is acyclic
  - reports cross-chapter edges so you can eyeball them

Exit code 0 when everything passes, 1 otherwise -- so it can gate a workflow.

Usage:
  python verify_edges.py --domain "CYPHER_Kapitel/*.cypher" \
                         --prereq "CYPHER_Kanten/*_prerequisites.cypher" \
                         [--facilitator "CYPHER_Kanten/*_facilitators.cypher"] \
                         [--sameas "CYPHER_Kanten/same_as.cypher"]

Globs may be repeated and are quoted in the shell. Chapter of a concept id is inferred from a
'BDT_CHNN' style prefix (best-effort); if your ids differ, the cross-chapter report stays empty.
"""
import argparse, glob, re, sys
from collections import defaultdict

CONCEPT_DEF = re.compile(r"MERGE \(n:Concept \{id:'([^']+)'\}\)")


def edge_re(rel):
    return re.compile(
        r"\(a:Concept \{id:'([^']+)'\}\),\s*\(b:Concept \{id:'([^']+)'\}\)\s*"
        r"MERGE \(a\)-\[:" + rel + r"\]->\(b\)")


def expand(globs):
    files = []
    for g in globs or []:
        files.extend(sorted(glob.glob(g)))
    return files


def read_texts(files):
    out = []
    for f in files:
        try:
            out.append(open(f, encoding="utf-8").read())
        except OSError as e:
            print(f"  ! could not read {f}: {e}")
    return out


def chapter_of(cid):
    m = re.match(r"([A-Za-z]+_CH\d+)", cid)
    return m.group(1) if m else "?"


def collect(globs, rel):
    pat = edge_re(rel)
    edges = []
    for text in read_texts(expand(globs)):
        edges.extend(pat.findall(text))
    return edges


def find_cycle(edges):
    g = defaultdict(list)
    for a, b in edges:
        g[a].append(b)
    color = defaultdict(int)
    cyc = []

    def dfs(u, st):
        color[u] = 1
        st.append(u)
        for v in g[u]:
            if color[v] == 1:
                cyc.append(st[st.index(v):] + [v])
                return True
            if color[v] == 0 and dfs(v, st):
                return True
        color[u] = 2
        st.pop()
        return False

    for n in list(g):
        if color[n] == 0 and dfs(n, []):
            return cyc[0]
    return None


def basic_checks(name, edges, defined, ok_ref):
    """ids defined, no dups, no self-loops. Returns updated ok flag."""
    ok = True
    missing = sorted({x for e in edges for x in e if x not in defined})
    if missing:
        ok = False
        print(f"FAIL  {name}: undefined concept ids ({len(missing)}): {missing[:8]}")
    else:
        print(f"PASS  {name}: every endpoint is a defined Concept node")
    dups = sorted({e for e in edges if edges.count(e) > 1})
    print(("FAIL" if dups else "PASS") + f"  {name}: duplicates -> {dups[:5] or 'none'}")
    ok &= not dups
    loops = [e for e in edges if e[0] == e[1]]
    print(("FAIL" if loops else "PASS") + f"  {name}: self-loops -> {loops[:5] or 'none'}")
    ok &= not loops
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", action="append", required=True)
    ap.add_argument("--prereq", action="append", required=True)
    ap.add_argument("--facilitator", action="append", default=[])
    ap.add_argument("--sameas", action="append", default=[])
    args = ap.parse_args()

    defined = set()
    for text in read_texts(expand(args.domain)):
        defined.update(CONCEPT_DEF.findall(text))

    pre = collect(args.prereq, "PREREQUISITE")
    fac = collect(args.facilitator, "FACILITATOR")
    same = collect(args.sameas, "SAME_AS")

    print(f"Concept nodes: {len(defined)} | PREREQUISITE: {len(pre)} | "
          f"FACILITATOR: {len(fac)} | SAME_AS: {len(same)}")
    print("-" * 64)
    ok = True

    ok &= basic_checks("PREREQUISITE", pre, defined, ok)
    if fac:
        ok &= basic_checks("FACILITATOR", fac, defined, ok)
    if same:
        ok &= basic_checks("SAME_AS", same, defined, ok)
    print("-" * 64)

    # PREREQUISITE acyclic
    cyc = find_cycle(pre)
    print(("FAIL  PREREQUISITE cycle: " + " -> ".join(cyc)) if cyc
          else "PASS  PREREQUISITE graph is acyclic (DAG)")
    ok &= cyc is None

    # PREREQUISITE / SAME_AS disjoint
    same_un = set(same) | {(b, a) for a, b in same}
    ov = set(pre) & same_un
    print(("FAIL  PREREQUISITE∩SAME_AS: " + str(list(ov)[:5])) if ov
          else "PASS  no pair is both PREREQUISITE and SAME_AS")
    ok &= not ov

    if fac:
        # FACILITATOR must not duplicate PREREQUISITE or SAME_AS (either direction)
        pre_un = set(pre) | {(b, a) for a, b in pre}
        ovp = set(fac) & pre_un
        ovs = set(fac) & same_un
        print(("FAIL  FACILITATOR∩PREREQUISITE: " + str(list(ovp)[:5])) if ovp
              else "PASS  no FACILITATOR pair coincides with PREREQUISITE")
        print(("FAIL  FACILITATOR∩SAME_AS: " + str(list(ovs)[:5])) if ovs
              else "PASS  no FACILITATOR pair coincides with SAME_AS")
        ok &= not ovp and not ovs
        # combined acyclic
        cyc2 = find_cycle(pre + fac)
        print(("FAIL  combined PREREQUISITE+FACILITATOR cycle: " + " -> ".join(cyc2)) if cyc2
              else "PASS  combined PREREQUISITE+FACILITATOR graph is acyclic (DAG)")
        ok &= cyc2 is None

    print("-" * 64)
    for name, edges in (("PREREQUISITE", pre), ("FACILITATOR", fac)):
        if not edges:
            continue
        cross = [(a, b) for a, b in edges if chapter_of(a) != chapter_of(b)]
        print(f"INFO  cross-chapter {name}: {len(cross)}")
    print("-" * 64)
    print("RESULT:", "ALL CHECKS PASSED" if ok else "PROBLEMS FOUND (see FAIL lines)")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
