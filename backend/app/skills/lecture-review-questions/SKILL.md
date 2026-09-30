---
name: lecture-review-questions
description: >-
  Extract a lecture's review/repetition questions ("Wiederholungsfragen", recap questions, quiz
  questions, Kontrollfragen) from the slide PDFs and add them to a Neo4j lecture knowledge graph as
  :Question nodes, linked to their Chapter via HAS_QUESTION and to the concept(s) they test via
  TESTS. Use this whenever the user wants to integrate review/exam/recap questions into the graph,
  attach questions to concepts, build an assessment/quiz layer, or asks to "add the
  Wiederholungsfragen", "do the questions for the next chapter", "map questions to concepts", or
  "create the Question nodes". Assumes an existing Lecture / Chapter / Topic / Subtopic / Concept domain
  model (e.g. from the lecture-domain-model skill). Produces one Cypher file per chapter.
---

# Lecture review questions (assessment layer)

Add the lecture's review questions as a queryable layer over an existing concept graph. Each
question becomes a `:Question` node, tied to its chapter and to the concept(s) it checks — so a
tutoring system can pull "questions for concept X", "questions for chapter Y", or "which concepts
does this question cover".

Work **one chapter at a time** and let the user verify the concept mapping before moving on — the
mapping is the part that needs human judgement.

## Model

```
(:Chapter)-[:HAS_QUESTION]->(:Question)        // the question belongs to this chapter
(:Question)-[:TESTS]->(:Concept)               // the question checks this concept (1..n)
```

- `:Question` properties: `id` (`BDT_CHNN_Qmm`), `text` (verbatim question), `index` (number within
  the chapter), `chapter`, `pageNr`, `source` (pdf filename). Mirror your `:Slide` node style.
- A question may have **several** TESTS edges when it is compound (e.g. "explain BNL-, Sort-Merge-
  and Hash-Join" → all three join concepts; "explain DW, Data Lake, Fabric, Lakehouse, Mesh" → five
  architecture concepts). Map to the genuinely-fitting concept(s), usually 1–4.

## Default rule and the documented exception

- **TESTS stays within the question's own chapter by default.** If a question mentions content that
  lives in another chapter (e.g. "partitioning in MongoDB *and* Spark" inside the Spark chapter),
  map only to the in-chapter concept(s) unless the user has approved a cross-chapter exception.
- **Cross-chapter TESTS is allowed only as an explicit, documented exception.** The clearest case:
  a topic was deduplicated out of this chapter into another (so there is no in-chapter concept to
  map to). Record the exception in a `// comment` and a `note` property on the question, and flag it
  to the user.

## Workflow per chapter

1. **Find the question slides.** Grep the chapter's slides Cypher for the recap-slide titles
   (e.g. `Wiederholung`, `Kontrollfrag`, `Quiz`, `Repetition`) to get the slide ids + `pageNr`s.
   A chapter may have several (e.g. "Wiederholungsfragen (1/2)" + "(2/2)", or split by sub-topic).
2. **Extract the verbatim question text** from those PDF pages:
   `pdftotext -f P -l P -layout chapter.pdf -`. Each bullet is one question. Keep the wording exact
   (fix only obvious OCR splits/typos). German quotes `„ "` and umlauts are fine inside single-quoted
   Cypher strings; escape any literal ASCII apostrophe `'` in the text.
3. **Map each question to concept(s).** Read the question, find the best-fitting `:Concept`(s) by
   name in the same chapter's domain model. Prefer the central concept(s); add more only for
   genuinely compound questions. For a vague/structural question, pick the closest representative
   concept(s) and flag it. Keep a one-line rationale for the trailing `//` comment.
4. **Write the Cypher** (`CYPHER_Fragen/NN-name_questions.cypher`), following `references/file-format.md`:
   a `Question` id constraint, the `MERGE` question nodes, one `HAS_QUESTION` block, then the `TESTS`
   edges grouped by question.
5. **Verify programmatically** before handing over:

   ```bash
   python scripts/verify_questions.py \
     --domain "CYPHER_Kapitel/*.cypher" \
     --questions "CYPHER_Fragen/*_questions.cypher"
   ```

   Hard checks (must pass): unique ids, all TESTS targets defined, every chapter has its
   HAS_QUESTION block. Reported as INFO: questions without a TESTS edge (should be empty or only the
   approved exceptions) and the list of cross-chapter TESTS (should match the documented exceptions).
6. **Present for verification** — show the question→concept mapping grouped by question, and flag
   the interpretive mappings, the multi-concept ones, and any cross-chapter exceptions. Apply
   feedback, re-verify, offer the next chapter.

## Notes
- Files load with `MERGE`, so they are idempotent and order-independent (after the domain model).
- Reset a chapter's questions: `MATCH (q:Question) WHERE q.chapter='BDT_CHN' DETACH DELETE q;`
- See `references/file-format.md` for the exact statement format and a per-question e