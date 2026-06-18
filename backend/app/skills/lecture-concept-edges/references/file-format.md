# File format & conventions

Match the style of the domain-model Cypher so edge files load the same way. Adapt the `BDT_CH0x_...`
id scheme to whatever the domain model uses. Use variable names `a` (dependent/specific) and `b`
(more fundamental) so the bundled verifier matches them.

## Edge statements

```cypher
// PREREQUISITE: A requires B
MATCH (a:Concept {id:'BDT_CH01_T04_C03'}), (b:Concept {id:'BDT_CH01_T04_C02'}) MERGE (a)-[:PREREQUISITE]->(b);  // Kostenfunktion -> Blockweiser Festplattenzugriff

// FACILITATOR: B helps with A but isn't required (note the ~> in comments to read it apart)
MATCH (a:Concept {id:'BDT_CH01_T04_S01_C01'}), (b:Concept {id:'BDT_CH01_T04_S01_C03'}) MERGE (a)-[:FACILITATOR]->(b);  // Primärindex ~> Clustered  [Typ/Analogie]

// SAME_AS: identical concept, stored once (later chapter as a, earlier as b)
MATCH (a:Concept {id:'BDT_CH05_T04_S03_C01'}), (b:Concept {id:'BDT_CH03_T04_C01'}) MERGE (a)-[:SAME_AS]->(b);  // RAG (CH05) == (CH03)
```

Query SAME_AS direction-agnostically (`(a)-[:SAME_AS]-(b)`); combine for full learning paths:
`MATCH p=(c)-[:PREREQUISITE|FACILITATOR|SAME_AS*]->(x) RETURN p`.

## One file per chapter per type

```
CYPHER_Kanten/
├── 01-...-_prerequisites.cypher
├── 01-...-_facilitators.cypher
├── 02-...-_prerequisites.cypher
├── 02-...-_facilitators.cypher
├── ...
├── same_as.cypher                  # all cross-chapter duplicates, one place
├── facilitators_begruendung.txt    # rationale for every facilitator edge (see below)
└── 00-reset_*.cypher               # optional delete + reload helper
```

## Header & summary blocks
Start each file with the semantics + assumptions, group edges by `// ===== Topic N =====`, and end
with a summary + checks. Facilitator summary should note overlap-freeness and combined-acyclicity:

```cypher
// FACILITATOR-Kanten für Kapitel N (...). Semantik: (A)-[:FACILITATOR]->(B) == "B hilft A, ist aber nicht nötig".
// Richtung: spezifisch -> grundlegend. Concept -> Concept. Sparsam. Kein Überlapp mit PREREQUISITE/SAME_AS; kombiniert azyklisch.
// ... edges ...
// FACILITATOR-Kanten: N (davon K kapitelübergreifend) | kein Überlapp mit PREREQUISITE/SAME_AS | kombiniert azyklisch
```

## Facilitator rationale `.txt`
A plain-text file documenting every facilitator edge — one entry per edge with the relationship, a
short reason, the category tag, and the "why facilitator, not prerequisite" note (which prerequisite
it sits next to). Group by chapter and topic; extend per chapter. Keep a header explaining the
semantics, the facilitator-vs-prerequisite test, and the four categories. Example entry:

```
4) Primärindex ~> Clustered                                  [Typ/Analogie]
   Ein Primärindex ist typischerweise clustered. Nicht zwingend: "clustered" ist keine
   definitorische Eigenschaft, nur die übliche Kombination.
```

## Reset / reload helper (optional)
Delete by id prefix so you only touch the intended chapter (safe because edges run later→earlier):

```cypher
MATCH (n) WHERE n.id STARTS WITH 'BDT_CHN' DETACH DELETE n;
// reload: domain-model -> slides -> *_prerequisites.cypher -> *_facilitators.cypher  (same_as.cypher unaffected)
```

Wipe only edges (before reloading a revised set), nodes untouched:
```cypher
MATCH ()-[r:PREREQUISITE]->() DELETE r;
MATCH ()-[r:FACILITATOR]->() DELETE r;
MATCH ()-[r:SAME_AS]->() DELETE r;
```
