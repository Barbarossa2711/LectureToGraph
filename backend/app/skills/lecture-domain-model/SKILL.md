---
name: lecture-domain-model
description: >-
  Extract the topic structure from lecture slide PDFs and turn it into a Neo4j
  Cypher domain model (Lecture > Chapter > Topic > Subtopic > Concept) for a
  tutoring system. Use whenever the user wants to build or update a domain
  model, knowledge graph, concept hierarchy or Cypher file from lecture slides,
  a course/chapter PDF, or an existing structure outline. Triggers include:
  "domain model", "Cypher", "Neo4j", "Vorlesung als Graph", "Kapitel-Struktur",
  "Konzept-Hierarchie", "tutoring system graph".
---

# Lecture Domain Model (PDF → Cypher)

Build a Neo4j domain model from lecture material in **two steps**:

1. **Extract structure → JSON** (human-reviewable intermediate)
2. **Generate Cypher** from the JSON with the bundled script

Always do Step 1 first and let the user confirm the JSON before Step 2.

---

## The model

Five node labels, parent → child only:

| Label    | Attributes                                   | Role                              |
|----------|----------------------------------------------|-----------------------------------|
| Lecture  | name, id, code, degreeType, term, PO, prof   | the course                        |
| Chapter  | name, index, id                              | one lecture unit / slide deck     |
| Topic    | name, index, id                              | agenda item within a chapter      |
| Subtopic | name, id                                     | grouping; **may nest recursively**|
| Concept  | name, id                                     | **leaf — smallest granularity**   |

Relationships:

```
(Lecture)-[:HAS_CHAPTER]->(Chapter)
(Chapter)-[:HAS_TOPIC]->(Topic)
(Topic|Subtopic)-[:HAS_SUBTOPIC]->(Subtopic)
(Topic|Subtopic)-[:HAS_CONCEPT]->(Concept)
```

A Subtopic can contain further Subtopics and/or Concepts. A node is a **Concept**
when it is a leaf (no meaningful sub-structure); it is a **Subtopic** when it
groups other nodes.

> Subtopics and Concepts deliberately have **no `index`**. Ordering and learning
> dependencies are expressed later via separate `prerequisite` / `facilitator`
> edges that the user adds — do not invent those edges here.

---

## Core rule: keep concepts, drop facts

The domain model is the **skeleton of named concepts**, not the explanatory
content. Keep the named headings/terms. **Drop** the sub-bullets that *define*,
*explain*, give *examples*, *formulas*, or *answers*.

Example (from a structure outline):

```
- Unterschied DBMS & Daten-Management-Systeme        ← KEEP (a Concept)
   - DBMS soll haben: Transaktionsmanagement, ...    ← DROP (explanatory fact)
   - DMS hat meist nie alle 3                         ← DROP (explanatory fact)
```

Also drop pure review/Q&A sections (e.g. "Wiederholungsfragen") — they are not
domain content.

If a sub-bullet is itself a distinct, named, learnable concept (e.g. the three
"V"s: Volume, Velocity, Variety), keep it as a Concept. When in doubt whether
something is a Concept or a droppable fact, **ask** (see below).

---

## Step 1 — Extract structure to JSON

1. Read the PDF with the `Read` tool (slide decks: read all pages; a clean
   outline PDF can be read directly).
2. Walk the agenda/sections top to bottom and build the hierarchy following the
   model and the keep/drop rule above.
3. Write the result to `<name>.structure.json` using the schema below and
   present it to the user for review. **Do not** generate Cypher yet.

### JSON schema

```json
{
  "lecture": {
    "name": "Big-Data-Technologien",
    "code": "BDT",
    "degreeType": "Master",
    "term": "2. Fachsemester",
    "PO": "2019",
    "prof": "Prof. Dr. Max Mustermann"
  },
  "chapter": { "name": "…", "index": 1 },
  "topics": [
    {
      "name": "…", "index": 1,
      "children": [
        { "type": "concept", "name": "…" },
        { "type": "subtopic", "name": "…", "children": [ /* concepts/subtopics */ ] }
      ]
    }
  ]
}
```

- `children` is recursive. Each child is either `{"type":"concept", ...}` (leaf)
  or `{"type":"subtopic", ..., "children":[...]}`.
- IDs are **not** required — the generator creates them. Add an `"id"` only to
  override a specific node.
- A Subtopic with no concepts yet is allowed: `"children": []`.

### When to ASK the user (don't guess)

Use the AskUserQuestion tool whenever:

- **Lecture metadata** is unknown or not on the slides: `code`, `degreeType`,
  `term`, `PO`, `prof`, `chapter.index`.
- **Granularity is ambiguous**: a heading could be a single Concept or a
  Subtopic with several Concepts (e.g. the "3 Vs", architecture layers).
- A block is **borderline concept vs. droppable fact**.
- A **list is flat but long** and could benefit from grouping into Subtopics
  (offer it, don't force it).
- Naming/spelling of a concept is unclear from the slides.

Prefer one batched question with concrete options over many small ones.

---

## Step 2 — Generate Cypher

Run the bundled script (no manual Cypher writing):

```bash
python3 scripts/json_to_cypher.py <name>.structure.json <name>.cypher
```

The script:

- auto-generates globally-unique IDs (scheme below),
- emits `CREATE CONSTRAINT` statements (idempotent load),
- emits `MERGE` for every node and relationship,
- prints node/relationship counts and fails on duplicate IDs.

### ID scheme

```
Lecture   <CODE>                 BDT
Chapter   <CODE>_CH<nn>          BDT_CH01
Topic     <CHAPTER>_T<nn>        BDT_CH01_T03
Subtopic  <PARENT>_S<nn>         BDT_CH01_T01_S02
Concept   <PARENT>_C<nn>         BDT_CH01_T01_S02_C01
```

`<nn>` is the zero-padded order within the parent, counted per node type.

### Verify before delivering

- Every non-Lecture node has exactly one incoming parent edge
  (child-edge count == node count − 1).
- No duplicate IDs (script aborts otherwise).
- Recursive subtopics present where expected.
- Then present the `.cypher` file to the user.

---

## Notes for re-use across chapters

- Keep the same `lecture.code` across chapters so all chapters share one Lecture
  node; bump `chapter.index` per deck.
- Keep one `.structure.json` per chapter; they are easy to diff and edit.
- See `examples/bdt_kapitel1.structure.json` for a complete reference input.
