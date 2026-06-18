---
name: lecture-concept-edges
description: >-
  Find and author the learning-dependency edges between Concept nodes of a lecture knowledge
  graph as Neo4j Cypher: PREREQUISITE (required), FACILITATOR (helpful but optional), and
  SAME_AS (identical concept across chapters). Use this whenever the user wants to connect
  lecture/course concepts by dependencies — phrases like "prerequisite edges", "facilitator
  edges", "Voraussetzungs-Kanten", "Facilitator-Kanten", "which concept needs which", "build
  the dependency graph", "PREREQUISITE/FACILITATOR", "Konzept-Abhängigkeiten" — or wants to
  extend an existing Lecture / Chapter / Topic / Subtopic / Concept domain model (e.g. from the
  lecture-domain-model skill) with edges. Trigger even if the user only names a chapter or a
  domain-model file and asks to "add the edges", "do facilitators", or "do the next chapter".
  Produces a conservative, acyclic Concept→Concept graph, one Cypher file per chapter per edge type.
---

# Lecture concept edges (PREREQUISITE + FACILITATOR + SAME_AS)

Turn a lecture's concept hierarchy into a **learning-dependency graph**. The nodes already exist
(typically `Lecture > Chapter > Topic > Subtopic > Concept` with `HAS_*` edges, e.g. from the
`lecture-domain-model` skill). You only add edges; you never invent nodes.

Work **one chapter at a time** and let the user verify each chapter before moving on. The graph
drives a tutoring system, so accuracy and restraint beat coverage — a wrong "you must learn X
first" sends students down the wrong path.

## The three edge types

Direction is always **from the dependent/specific concept to the more fundamental one** (`A -> B`):

- `(:Concept)-[:PREREQUISITE]->(:Concept)` — **A requires B.** You genuinely cannot understand A
  without already understanding B. The backbone of the graph.
- `(:Concept)-[:FACILITATOR]->(:Concept)` — **B helps with A but isn't required.** Context,
  analogy, "typical pairing", motivation. The soft layer.
- `(:Concept)-[:SAME_AS]-(:Concept)` — **A and B are the same concept** reappearing in another
  chapter. Not a dependency. Store once (later chapter → earlier), query direction-agnostically.

## Order of work

1. **PREREQUISITE first** (conservative — only the truly-required edges). During this pass you will
   spot edges that feel "helpful but not strictly necessary" — *don't* force them in; note them as
   facilitator candidates.
2. **SAME_AS** for any concept that is identical to one from an earlier chapter (collect in one
   shared `same_as.cypher`).
3. **FACILITATOR second** (moderate — see below), picking up the deferred candidates plus other
   clearly-helpful links.

## Hard constraints (always)

1. **Concept → Concept only.** Never connect Topic/Subtopic/Lecture/Slide nodes.
2. **PREREQUISITE is acyclic**, and the **combined PREREQUISITE + FACILITATOR graph is acyclic** too.
3. **No edge is two types at once.** A FACILITATOR pair must never coincide with a PREREQUISITE or
   SAME_AS pair (in either direction); PREREQUISITE and SAME_AS must not coincide either.
4. **Idempotent Cypher** (`MATCH ... MERGE`).
5. Cross-chapter edges are allowed and valuable, but **always later-chapter → earlier-chapter**
   (this respects learning order and structurally prevents cycles).

## PREREQUISITE: conservative by default

Only emit a PREREQUISITE when B is *truly necessary* to understand A. The test: *would A be
incomprehensible (not merely less motivated) if the student had never seen B?* When in doubt,
leave it out or demote to facilitator. Many concepts are legitimately **entry points** (no
outgoing edge) — foundational definitions, parallel sibling options, example systems, general math.

Recurring traps (details in `references/heuristics.md`): the "overview" link (`Feature ->
ProductOverview`), the **AND-semantics trap** (if A needs *any one of* B/C/D, don't link to all
three — that falsely claims it needs every one), parallel siblings, and cross-system "same idea".

## FACILITATOR: moderate, clearly-helpful only

Aim for a **sparse, defensible set (~10–12 per chapter is a good calibration)**. Every facilitator
should have a one-line, nameable reason that fits one of four categories:

- **[Typ/Analogie]** B is a typical property of A, or the same underlying principle (e.g.
  *Primärindex ~> Clustered*; *Hash Join ~> Unclustered Hash Index*).
- **[Zweck/Motiv]** B explains *what A is for* (e.g. *Batch-Layer ~> Volume*).
- **[Greifbar]** B makes the costs/options/structures behind A tangible (e.g. *Analyse des
  Ausführungsplans ~> Kostenfunktion*).
- **[Kontext]** B places A in a larger context (e.g. *Probleme verteilter DB-Systeme ~> Client-Server*).

The facilitator pass is exactly where the candidates you deferred during the PREREQUISITE pass
belong (e.g. cross-system "same idea" links, generic feature→overview links, the AND-semantics
distance-measure links, prevention-vs-correction sibling links). Keep `FACILITATOR` direction
specific→fundamental, same as PREREQUISITE, so the combined graph stays acyclic.

## Workflow per chapter

1. **Read the inputs:** the chapter's domain-model Cypher (Concept ids + names); earlier chapters'
   domain models for cross-chapter edges; for unclear edges, the chapter's slides Cypher
   (`Slide.title` + `COVERS`) and, if needed, the PDF (`pdftotext -f P -l P -layout file.pdf -`).
2. **Enumerate concepts topic by topic.** This surfaces the natural chains (definition→property,
   base→variant, pipeline stage N→N+1) and the parallel siblings (which stay unconnected).
3. **PREREQUISITE pass** (conservative), then **SAME_AS**, then **FACILITATOR pass** (moderate).
   Keep a one-line rationale per edge for the trailing `//` comment; for facilitators also record
   the category — these become the rationale `.txt` (see below).
4. **Write the Cypher** in the dedicated folder, one file per chapter per type
   (`NN-name_prerequisites.cypher`, `NN-name_facilitators.cypher`, shared `same_as.cypher`).
   Follow `references/file-format.md`.
5. **Maintain the facilitator rationale file** `facilitators_begruendung.txt` (or
   `_rationale.txt`): one entry per facilitator edge with its reason, category, and the
   "why facilitator, not prerequisite" note. Extend it per chapter.
6. **Verify programmatically** — never hand a chapter over until this prints `ALL CHECKS PASSED`.
   Run over the *whole* set each time so cross-chapter cycles and cross-file overlaps are caught:

   ```bash
   python scripts/verify_edges.py \
     --domain "CYPHER_Kapitel/*.cypher" \
     --prereq "CYPHER_Kanten/*_prerequisites.cypher" \
     --facilitator "CYPHER_Kanten/*_facilitators.cypher" \
     --sameas "CYPHER_Kanten/same_as.cypher"
   ```

7. **Present for verification, flag the soft calls** — cross-chapter links, slide-interpreted
   edges, and anything you weren't sure was prerequisite vs facilitator — and name what you left as
   entry points. Apply feedback, re-verify, offer the next chapter.

## References (read when relevant)
- `references/heuristics.md` — good vs bad edges, the four traps, PREREQUISITE-vs-FACILITATOR-vs-
  SAME_AS decisions, the facilitator categories, calibration, worked examples.
- `references/file-format.md` — exact Cypher statement format, file naming, header/summary blocks,
  the rationale `.txt` format, reset-file te