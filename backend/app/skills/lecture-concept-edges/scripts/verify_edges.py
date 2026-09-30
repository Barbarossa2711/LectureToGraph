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
  - cross-chapter edges always point from a later to an earlier chapter (never forward)
  - reports cross-chapter edges so you can eyeball them

Exit code 0 when everything passes, 1 otherwise -- so it can gate a workflow.

Usage:
  python verify_edges.py --domain "CYPHER_Kapitel/*.cypher" \
                         --prereq "CYPHER_Kanten/*_prerequisites.cypher" \
                         [--facilitator "CYPHER_Kanten/*_facilitators.cypher"] \
                         [--sameas "CYPHER_Kanten/same_as.cypher"]

Globs may be repeated and are quoted in the shell. Chapter of a concept id is inferred from a
'BDT_CHNN' style prefix (best-effort); ids without such a prefix are skipped by the
chapter-direction check and the cross-chapter report.
"""
import argparse, glob, re, sys
from collections import defaultdict

CONCEPT_DEF = re.compile(r"MERGE \(n:Concept \{id:'([^']+)'\}\)")


def edge_re(rel):
    """
    Build the pattern for a Concept -> Concept edge statement of one type.

    :param rel: The relationship type.
    :return: The compiled pattern capturing source and target id.
    """
    return re.compile(
        r"\(a:Concept \{id:'([^']+)'\}\),\s*\(b:Concept \{id:'([^']+)'\}\)\s*"
        r"MERGE \(a\)-\[:" + rel + r"\]->\(b\)")


def expand(globs):
    """
    Expand shell globs into a sorted list of file paths.

    :param globs: The glob patterns, or None.
    :return: The matching files, sorted per pattern.
    """
    files = []
    for g in globs or []:
        files.extend(sorted(glob.glob(g)))
    return files


def read_texts(files):
    """
    Read files as UTF-8; unreadable files are reported and skipped.

    :param files: The file paths.
    :return: The file contents.
    """
    out = []
    for f in files:
        try:
            out.append(open(f, encoding="utf-8").read())
        except OSError as e:
            print(f"  ! could not read {f}: {e}")
    return out


def chapter_of(cid):
    """
    Infer the chapter from an id with a <CODE>_CHNN prefix.

    :param cid: The node id.
    :return: The chapter prefix, or "?" if the id has none.
    """
    m = re.match(r"([A-Za-z]+_CH\d+)", cid)
    return m.group(1) if m else "?"


def chapter_number(cid):
    """
    Infer the chapter number from an id with a <CODE>_CHNN prefix.

    :param cid: The concept id.
    :return: The chapter number, or None if the id has no chapter prefix.
    """
    m = re.match(r"[A-Za-z]+_CH(\d+)", cid)
    return int(m.group(1)) if m else None


def forward_edges(edges):
    """
    Find edges that point from an earlier to a later chapter.

    :param edges: The edges as (source, target) tuples.
    :return: The edges whose source chapter precedes their target chapter.
    """
    out = []
    for a, b in edges:
        ca, cb = chapter_number(a), chapter_number(b)
        if ca is not None and cb is not None and ca < cb:
            out.append((a, b))
    return out


def collect(globs, rel):
    """
    Collect all edges of one type from the matching files.

    :param globs: The glob patterns of the edge files.
    :param rel: The relationship type.
    :return: The edges as (source id, target id) tuples.
    """
    pat = edge_re(rel)
    edges = []
    for text in read_texts(expand(globs)):
        edges.extend(pat.findall(text))
    return edges


def find_cycle(edges):
    """
    Search a directed graph for a cycle with depth-first search.

    :param edges: The edges as (source, target) tuples.
    :return: The first cycle found as a node list ending in its start node, or None.
    """
    g = defaultdict(list)
    for a, b in edges:
        g[a].append(b)
    color = defaultdict(int)
    cyc = []

    def dfs(u, st):
        """
        Visit a node and its successors; gray nodes on the stack reveal a cycle.

        :param u: The node to visit.
        :param st: The current path.
        :return: True if a cycle was found.
        """
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
    """
    Check that all endpoints are defined concepts and that there are no duplicates or self-loops.

    :param name: The relationship type, used in the output.
    :param edges: The edges as (source, target) tuples.
    :param defined: The ids of the defined Concept nodes.
    :param ok_ref: Unused.
    :return: True if all checks pass.
    """
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
    """
    Run all edge checks and exit with 0 if they pass, 1 otherwise.

    :return: None
    """
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

    cyc = find_cycle(pre)
    print(("FAIL  PREREQUISITE cycle: " + " -> ".join(cyc)) if cyc
          else "PASS  PREREQUISITE graph is acyclic (DAG)")
    ok &= cyc is None

    same_un = set(same) | {(b, a) for a, b in same}
    ov = set(pre) & same_un
    print(("FAIL  PREREQUISITE∩SAME_AS: " + str(list(ov)[:5])) if ov
          else "PASS  no pair is both PREREQUISITE and SAME_AS")
    ok &= not ov

    if fac:
        pre_un = set(pre) | {(b, a) for a, b in pre}
        ovp = set(fac) & pre_un
        ovs = set(fac) & same_un
        print(("FAIL  FACILITATOR∩PREREQUISITE: " + str(list(ovp)[:5])) if ovp
              else "PASS  no FACILITATOR pair coincides with PREREQUISITE")
        print(("FAIL  FACILITATOR∩SAME_AS: " + str(list(ovs)[:5])) if ovs
              else "PASS  no FACILITATOR pair coincides with SAME_AS")
        ok &= not ovp and not ovs
        cyc2 = find_cycle(pre + fac)
        print(("FAIL  combined PREREQUISITE+FACILITATOR cycle: " + " -> ".join(cyc2)) if cyc2
              else "PASS  combined PREREQUISITE+FACILITATOR graph is acyclic (DAG)")
        ok &= cyc2 is None

    for name, edges in (("PREREQUISITE", pre), ("FACILITATOR", fac), ("SAME_AS", same)):
        if not edges:
            continue
        fwd = forward_edges(edges)
        print(("FAIL  " + name + " points from an earlier to a later chapter: " + str(fwd[:5]))
              if fwd else f"PASS  {name}: cross-chapter edges point from later to earlier chapters")
        ok &= not fwd

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
