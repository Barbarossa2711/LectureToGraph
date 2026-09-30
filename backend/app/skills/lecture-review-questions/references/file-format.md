# File format & conventions

One Cypher file per chapter in a dedicated folder (`CYPHER_Fragen/`, parallel to `CYPHER_Folien/`),
named after the domain model: `01-arch-rel-anfragen_questions.cypher`, etc. Adapt the `BDT_CHNN_...`
id scheme to whatever the domain model uses.

## Structure of a file

```cypher
// Wiederholungsfragen für Kapitel N (BDT_CHN). Modell: (Chapter)-[:HAS_QUESTION]->(:Question)-[:TESTS]->(:Concept).
// TESTS nur auf CHN-Konzepte (Ausnahmen explizit dokumentieren). Quelle: <chapter>.pdf, Folie(n) X(-Y).

CREATE CONSTRAINT question_id IF NOT EXISTS FOR (n:Question) REQUIRE n.id IS UNIQUE;

// --- Frage-Knoten ---
MERGE (n:Question {id:'BDT_CHN_Q01'}) SET n.text='<verbatim question text>', n.index=1, n.chapter='BDT_CHN', n.pageNr=75, n.source='<chapter>.pdf';
// ... one MERGE per question ...

// --- HAS_QUESTION (one block links every question of this chapter to the chapter) ---
MATCH (ch:Chapter {id:'BDT_CHN'}), (q:Question) WHERE q.chapter='BDT_CHN' MERGE (ch)-[:HAS_QUESTION]->(q);

// --- TESTS (question -> concept(s)) ---
MATCH (q:Question {id:'BDT_CHN_Q01'}), (c:Concept {id:'BDT_CHN_T0..._C..'}) MERGE (q)-[:TESTS]->(c);  // <concept name>
// ... grouped by question; compound questions get several lines ...

// --- Zusammenfassung --- Questions: N | HAS_QUESTION: N | TESTS: M
```

Use the variable names `n` (question node), `ch`/`q` (HAS_QUESTION), `q`/`c` (TESTS) so
`verify_questions.py` matches them.

## Worked example (compound question, multiple TESTS)

```cypher
MERGE (n:Question {id:'BDT_CH01_Q12'}) SET n.text='Wie funktioniert Block-Nested-Loop-Join, Sort-Merge-Join, Hash-Join? Wie hoch sind die Aufwände?', n.index=12, n.chapter='BDT_CH01', n.pageNr=76, n.source='01-arch-rel-anfragen.pdf';
...
MATCH (q:Question {id:'BDT_CH01_Q12'}), (c:Concept {id:'BDT_CH01_T05_S01_C02'}) MERGE (q)-[:TESTS]->(c);  // Block Nested Loop Join
MATCH (q:Question {id:'BDT_CH01_Q12'}), (c:Concept {id:'BDT_CH01_T05_S01_C03'}) MERGE (q)-[:TESTS]->(c);  // Sort-Merge Join
MATCH (q:Question {id:'BDT_CH01_Q12'}), (c:Concept {id:'BDT_CH01_T05_S01_C04'}) MERGE (q)-[:TESTS]->(c);  // Hash Join
```

## Documented cross-chapter exception

When a question must point outside its chapter (approved exception), add a `note` property and a
clear comment:

```cypher
MERGE (n:Question {id:'BDT_CH07_Q11'}) SET n.text='Welche Herausforderungen gibt es bei Vektordatenbank-Systemen?', n.index=11, n.chapter='BDT_CH07', n.pageNr=72, n.source='07-data-engineering.pdf', n.note='Vektor-Topic in CH07 entfernt; TESTS verweisen kapitelübergreifend auf CH03';
...
MATCH (q:Question {id:'BDT_CH07_Q11'}), (c:Concept {id:'BDT_CH03_T03_S04_C02'}) MERGE (q)-[:TESTS]->(c);  // Curse of Dimensionality (CH03) [kapitelübergreifend]
```

## Useful checks (put in the file footer)
```cypher
// Fragen eines Kapitels:
MATCH (:Chapter {id:'BDT_CHN'})-[:HAS_QUESTION]->(q:Question) RETURN q.index, q.text ORDER BY q.index;
// Konzepte je Frage:
MATCH (q:Question)-[:TESTS]->(c:Concept) WHERE q.chapter='BDT_CHN' RETURN q.index, collect(c.name);
// Fragen ohne TESTS (sollte leer sein, außer dokumentierte Ausnahmen):
MATCH (q:Question) WHERE q.chapter='BDT_CHN' AND NOT (q)-[:TESTS]->() RETURN q.id;
// Fragen, die ein bestimmtes Konzept prüfen:
MATCH (q:Question)-[:TESTS]->(:Concept {id:'...'}) RETURN q.text;
```
