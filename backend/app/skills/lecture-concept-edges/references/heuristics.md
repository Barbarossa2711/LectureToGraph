# Heuristics: deciding edges well

Read this when unsure whether an edge belongs, which type it is, or how conservative to be.
Examples come from a "Big-Data-Technologien" lecture but the patterns are general.

## Contents
1. Real PREREQUISITE vs not
2. Strong edge shapes
3. Entry points (when NOT to add a PREREQUISITE)
4. The four traps
5. PREREQUISITE vs FACILITATOR vs SAME_AS
6. FACILITATOR: the four categories
7. Cross-chapter edges
8. Slide content to resolve doubt
9. Calibration

---

## 1. Real PREREQUISITE vs not
Counterfactual test: *if a student had never seen B, would A be incomprehensible (not merely less
motivated)?* Only then is B a prerequisite of A.
- ✅ `B+-Baum -> B-Baum` (a B+-tree is defined as a variant of a B-tree)
- ✅ `Sort-Merge Join -> Externes Sortieren` (the algorithm runs an external sort as a step)
- ❌ `Datenverwaltung -> DBMS` as "be motivated by DBMS first" — that's facilitation.

## 2. Strong edge shapes (almost always safe PREREQUISITEs)
- **Definition → property/specialization:** `Snowflake -> Star Schema`, `KTable -> KStream`.
- **Composite → its parts:** `Serving-Layer -> Batch-Layer`/`Speed-Layer`; `Cube -> Fakten`/`Dimensionen`.
- **Pipeline stages:** `Relation-to-Relation -> Stream-to-Relation -> Data Stream`.
- **Mechanism → the structure it operates on:** `Token Ring -> Partition Key`; `Partitionierung -> RDD`.
- **Evaluation/metric → the thing evaluated:** `MAPE -> MAE`.

## 3. Entry points (no outgoing PREREQUISITE — this is correct, not lazy)
- Foundational definitions the chapter starts from (`Data Stream`, `Zeitreihe`, `RDD`).
- Parallel sibling options (four NoSQL models; time/tuple/event-driven; metadata types).
- Example systems & tools (`OpenRefine`, `FAISS/Milvus/Pinecone`, InfluxDB components).
- General math / primitives (distance measures, skip list).

## 4. The four traps
- **(a) Overview link.** `X -> SomethingÜberblick`/`Hadoop-Ökosystem` carries no sequencing info —
  almost everything "needs the intro". Anchor on the concrete concept X is built from. (→ facilitator.)
- **(b) AND-semantics.** A PREREQUISITE list means *all* targets required. `KNN -> Cosine/L2/Inner`
  falsely says KNN needs all three; it needs *a* measure (OR). Leave it, or make each a facilitator.
- **(c) Parallel siblings as a chain.** Two alternatives are rarely prerequisites of each other
  (e.g. *Proaktives DQ-Management* is the alternative to reactive cleaning, not built on it).
- **(d) Cross-system "same idea".** Spark `Hash-Partitioning` vs Mongo `Hashed Partitioning` — same
  concept, parallel application; the lecture even contrasts them. Don't force a prerequisite. (→ facilitator.)

## 5. PREREQUISITE vs FACILITATOR vs SAME_AS — decision order
1. **Same concept reappearing?** (identical/near-identical name & meaning) → `SAME_AS` (store once,
   later→earlier). A *specialization* of a known idea (e.g. *On-Demand Materialized Views ->
   Materialized Views*) is **not** SAME_AS — that's a PREREQUISITE.
2. **Truly required to understand?** → `PREREQUISITE`.
3. **Helpful / motivating / analogy / typical-pairing but not strictly needed?** → `FACILITATOR`.

The traps in §4 (a, b, d) are exactly the cases that become **facilitators**: the overview link,
the AND-semantics distance links, the cross-system "same idea" links, and the prevention-vs-correction
sibling links. The PREREQUISITE pass *defers* them; the FACILITATOR pass picks them up.

## 6. FACILITATOR: the four categories
Each facilitator should have a nameable reason in one of these buckets (use them as tags):
- **[Typ/Analogie]** typical property / same principle — `Primärindex ~> Clustered`, `Hash Join ~>
  Unclustered Hash Index`, `DStreams ~> RDD`, `Token Ring ~> Sharding`.
- **[Zweck/Motiv]** explains what A is for — `Batch-Layer ~> Volume`, `Materialized Views ~> Aggregationen`.
- **[Greifbar]** makes costs/options/structures tangible — `Externes Sortieren ~> Kostenfunktion`,
  `Optimierung auf physischer Ebene ~> Hash Join`.
- **[Kontext]** larger context — `Probleme verteilter DB-Systeme ~> Client-Server-Architekturen`,
  `Data Governance ~> Datenökosystem & Data Governance (CH01)`.
If a candidate fits none of these cleanly, it is probably too weak — drop it.

## 7. Cross-chapter edges
Allowed and often the most pedagogically important (a NoSQL `Skalierbarkeit`-limit builds on
`Horizontale Skalierung`). **Always later-chapter → earlier-chapter** — respects learning order and
prevents cycles. Flag every cross-chapter edge for the user; several get reclassified during review.

## 8. Slide content to resolve doubt
The hierarchy gives names; the slides give meaning. For an uncertain edge, read the chapter's slides
Cypher (`Slide.title` + `COVERS` show what each slide teaches and which concepts co-occur), and the
PDF page if needed. Worked examples where slides settled direction/necessity: *SEDAR -> Semantic
Model* (slide: "semantic query on the basis of a semantic model"); *Watermarking -> Event Time vs.
Processing Time* (slide defines watermarking via late events).

## 9. Calibration
No fixed number, but from real chapters: PREREQUISITE ~0.5–1.0 edges/concept with a healthy share of
entry points; FACILITATOR ~10–12 per chapter. Approaching ~2 PREREQUISITE edges/concept means you're
over-connecting — demote the weakest to facilitator. Final gut check: read the edge list back as a
study order — "learn B, then A" must sound right for every PREREQUISITE; "B helps with A, but A is
understandable without it" must hold for every FACILITATOR.
