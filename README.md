# LectureToGraph

**AI-assisted construction of a lecture's domain model, from slide PDFs to a Neo4j
knowledge graph.** An LLM agent reads the lecture slides and builds the graph chapter
by chapter in three stages. After every stage the lecturer reviews the result,
edits it and approves it before the tool continues.

LectureToGraph was developed as part of the master's thesis *Lernfortschrittsmodellierung
und adaptive Empfehlungen in einem KI-basierten Multi-Agenten-Tutoring-System*
(Hochschule Niederrhein, 2026). It produces the domain model that the tutoring system
GRAPHIT uses for learner modelling and learning path recommendations. The tool runs
upstream of that system and does not touch any other part of the graph.

Building such a domain model by hand is not practical: a lecture like *Big-Data-Technologien*
has seven chapters and several hundred concepts, and deciding whether and how two concepts
depend on each other requires domain expertise. LectureToGraph therefore does not aim at
full automation. It follows the principle of **AI-assisted construction under expert
supervision**: the model proposes, the lecturer decides.

---

## Contents

- [Features](#features)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Graph schema](#graph-schema)
- [How it works](#how-it-works)
- [Architecture](#architecture)
- [Visualisation and editing](#visualisation-and-editing)
- [Export and Neo4j upload](#export-and-neo4j-upload)
- [Configuration](#configuration)
- [API overview](#api-overview)
- [Runtime and cost](#runtime-and-cost)
- [Limitations](#limitations)
- [Project structure](#project-structure)
- [Tech stack](#tech-stack)

---

## Features

- **Provider-agnostic.** Works with Anthropic (Claude), OpenAI and any OpenAI-compatible
  endpoint such as the university cluster. The model dropdown is filled live with the
  models that are actually available for the configured key or endpoint.
- **Multimodal PDF reading.** Slides are passed to the model as extracted text
  (pdfplumber) *and* as rendered page images (PyMuPDF), in batches of fixed size.
  Outline levels, highlights and figures cannot be recovered reliably from text alone.
- **Three stages per chapter:** lecture structure (with slides), concept edges and
  review questions.
- **Chapter by chapter.** Works with one comprehensive PDF (the agent proposes the chapter
  breakdown and asks for confirmation) or with one PDF per chapter. Approved chapters stay
  untouched when another chapter is added.
- **Validation gates.** After each stage the graph is shown in a Neo4j-Browser-like view.
  Nodes and edges can be added, edited or deleted before the stage is approved, or the
  stage can be re-run with textual feedback.
- **Formal properties are enforced by scripts, not by the model.** Verification scripts
  check that edges reference existing concepts and that the dependency graph is acyclic;
  a stage cannot finish until they pass.
- **Cypher is the source of truth.** Every stage writes idempotent `.cypher` files (`MERGE`
  only). Manual edits can be written back to a Cypher file at any time.
- **Neo4j upload.** Load the graph into the bundled Neo4j or into your own instance
  (Neo4j Desktop, your own Docker) with a credentials form.
- **German or English.** The agent asks its questions in German by default; switchable.
- **Resumable.** Jobs run asynchronously; progress arrives via server-sent events and a
  reconnecting browser restores the current state.

---

## Quick start

Requirements: Docker with Docker Compose.

### 1 · Configure providers

Create a `.env` in the project root (it is git-ignored). Set at least one provider:

```dotenv
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# Optional: private OpenAI-compatible endpoint (e.g. an OpenWebUI gateway).
# Leave CLUSTER_BASE_URL empty to hide this provider.
CLUSTER_BASE_URL=https://<host>:<port>/api/v1
CLUSTER_API_KEY=...
CLUSTER_MODEL=ultrabrain
# For a self-signed certificate: put the .pem into ./certs (see certs/README.md)
CLUSTER_CA_BUNDLE=/certs/cluster_ca.pem
```

### 2 · Start the stack

```bash
docker compose up --build
```

| Service | URL | Login |
|---|---|---|
| **App (frontend)** | http://localhost:5173 | – |
| Backend API / OpenAPI docs | http://localhost:8000/docs | – |
| Neo4j Browser | http://localhost:7474 | `neo4j` / `password` |
| Neo4j Bolt | `bolt://localhost:7687` | `neo4j` / `password` |

The bundled Neo4j is the staging database that also feeds the visualisation. Its data
lives in the Docker volume `neo4j_data` and survives restarts; `docker compose down -v`
deletes it.

> **Test PDF:** `Beispiel-Vorlesung.pdf` in the project root is a short two-page sample
> lecture (*Einführung in Datenbanksysteme*) that can be uploaded right away.

---

## Workflow

```
            re-run with textual feedback
        ┌───────────────┬────────────────┬──────────────────┐
        ▼               │                │                  │
 Stage 1 ──▶ Gate ──▶ Stage 2 ──▶ Gate ──▶ Stage 3 ──▶ Gate ──▶ next chapter / finish
 structure            concept            review
 + slides             edges              questions
              (verification script of the stage runs before every gate)
```

1. **Create a job.** Choose provider, model and language, upload the lecture PDF(s) and
   start.
2. **Stage 1 · Lecture structure.** The agent reads the slides. For a comprehensive PDF it
   proposes the chapter breakdown with page ranges and asks for confirmation. It builds
   exactly one chapter: the hierarchy of topics, subtopics and concepts, and a `Slide` node
   per slide that presents at least one concept, linked via `COVERS`. While the deck is
   open it also captures the chapter's review questions verbatim for stage 3.
3. **Validate.** Check the graph, edit it if needed, then approve or re-run.
4. **Stage 2 · Concept edges.** `PREREQUISITE`, `FACILITATOR` and `SAME_AS` between the
   chapter's concepts. Validate.
5. **Stage 3 · Review questions.** `Question` nodes with `HAS_QUESTION` and `TESTS`.
   Validate.
6. **Chapter done.** Add another chapter (optionally upload a new chapter PDF; otherwise the
   agent continues with the next chapter of the comprehensive PDF) or finish the lecture.

Whenever a modelling decision is ambiguous, for example the granularity of concepts or
missing lecture metadata, the agent pauses and asks. The question appears on the right;
the pipeline continues once it is answered.

A re-run is limited to the current stage of the current chapter: the tool deletes what this
stage created in the chapter and starts the agent with a fresh conversation, with the
feedback as additional instruction. Approved chapters and earlier stages are not affected.

---

## Graph schema

The domain model is a labeled property graph. The lecture structure forms a hierarchy;
typed edges between concepts express their didactic order.

### Nodes

| Label | Properties | Meaning |
|---|---|---|
| `Lecture` | `id` (= `code`), `name`, `code`, `degreeType`, `PO`, `ECTS`, `prof`, `term` | Root of a course. `code` is the official abbreviation (e.g. `BDT`), `degreeType` Bachelor or Master, `PO` the examination regulations, `ECTS` the credit points of the module (used by the learner model), `term` the semester. |
| `Chapter` | `id`, `index`, `name` | One lecture unit, in table-of-contents order. |
| `Topic` | `id`, `index`, `name` | A topic within a chapter. |
| `Subtopic` | `id`, `name` | Optional grouping below a topic; may nest recursively. |
| `Concept` | `id`, `name` | Finest granularity: a concept or fact students should learn. Concepts carry **no** `index`; their order is defined only by the concept edges. |
| `Slide` | `id`, `title`, `pageNr`, `source`, `lecture`, `chapter`, `chapterIndex`, `chapterName` | A slide that presents at least one concept. `source` is the PDF file name. Used for retrieval of the slide content. |
| `Question` | `id`, `text`, `index`, `chapter`, `pageNr`, `source`, `note` (optional) | A review question of the lecture, verbatim, with its position in the slides. |

### Edges

| Edge | Direction | Meaning |
|---|---|---|
| `HAS_CHAPTER` | Lecture → Chapter | hierarchy |
| `HAS_TOPIC` | Chapter → Topic | hierarchy |
| `HAS_SUBTOPIC` | Topic/Subtopic → Subtopic | hierarchy |
| `HAS_CONCEPT` | Topic/Subtopic → Concept | hierarchy |
| `HAS_QUESTION` | Chapter → Question | the question belongs to this chapter |
| `TESTS` | Question → Concept | the question tests this concept |
| `COVERS` | Slide → Concept | the slide presents this concept |
| `PREREQUISITE` | Concept → Concept | **A requires B** (necessity) |
| `FACILITATOR` | Concept → Concept | **B helps with A** but is not required (usefulness) |
| `SAME_AS` | Concept → Concept | the same concept reappearing in another chapter |

### Concept dependencies

The concept edges distinguish two readings of "A comes after B":

- **`PREREQUISITE`** encodes necessity and acts as a hard condition: the tutoring system
  does not recommend A before B is mastered. Several incoming `PREREQUISITE` edges are
  evaluated conjunctively. The relation is asymmetric, irreflexive and transitive, so the
  subgraph is acyclic. Only **direct** prerequisites are stored; indirect ones follow from
  graph traversal (minimal educational knowledge graph).
- **`FACILITATOR`** encodes usefulness and acts as a soft preference that only affects the
  ranking of recommendations. It is kept acyclic but not transitively closed, since
  usefulness does not chain.
- A third reading, pure convention ("usually taught first"), is deliberately not modelled:
  the presentation order is already given by the chapter hierarchy and `index`.

Edges point from the dependent concept to the more fundamental one. The combined
`PREREQUISITE` + `FACILITATOR` graph must be acyclic as well, and no pair of concepts may
carry two edge types at once. Edges between chapters are allowed but always point from the
later to the earlier chapter, which respects the learning order and rules out cycles across
chapters.

### ID scheme

IDs are hierarchical and start with the lecture code, so every operation can be scoped to
one lecture (`n.id STARTS WITH '<code>'`) or one chapter (`'<code>_CHnn'`):

```
BDT                          Lecture
BDT_CH01                     Chapter
BDT_CH01_T03                 Topic
BDT_CH01_T01_S02             Subtopic
BDT_CH01_T01_S02_C01         Concept
BDT_CH06_SL34                Slide    (<CODE>_CHnn_SL<pageNr>)
BDT_CH01_Q12                 Question
```

---

## How it works

### Agent and providers

An LLM gets access to the lecture material through a small set of tools and runs in a loop
until it asks the user a question or completes the stage. Internally the conversation uses
one message format (typed text, image, tool-use and tool-result blocks); adapters map it to
the Anthropic Messages API and to OpenAI-compatible chat completions, including their
differences in tool calls and images in tool results.

### Skills

The domain-specific rules of each stage are not in the program code. They live in
declarative **skill definitions** modelled after Anthropic's Agent Skills: a `SKILL.md` with
a front matter naming and describing the skill, instructions in natural language, and
optionally scripts, reference documents and examples.

| Stage | Skill | Verification script |
|---|---|---|
| 1 · Structure + slides | `lecture-domain-model` | `json_to_cypher.py` (generates the Cypher), `verify_slides.py` |
| 2 · Concept edges | `lecture-concept-edges` | `verify_edges.py` |
| 3 · Review questions | `lecture-review-questions` | `verify_questions.py` |

At run time the skill of the current stage becomes the agent's system prompt. Unlike with
Anthropic's skills, the agent does not choose the skill itself; the running stage decides.
An addendum maps the tools the skill mentions onto the tools of LectureToGraph. This makes it
possible to change the didactic modelling decisions without touching the implementation.

### Tools and sandbox

| Tool | Purpose |
|---|---|
| `read_pdf(path, pages?)` | text and rendered page images of an uploaded PDF, a few pages per call |
| `read_file`, `write_file`, `list_dir` | text files in the job workspace |
| `run_script(script, args)` | run a verification or generation script of the current stage |
| `ask_user(questions)` | pause and ask the lecturer |
| `stage_complete(summary, artifacts)` | finish the stage and hand over to the validation gate |

All file access is resolved against a workspace created per job and rejected if the path
leaves it. `run_script` only runs the scripts whitelisted for the current stage.

### Verification

The formal properties of the graph are enforced by scripts. The agent may call
`stage_complete` only once the script of its stage passes:

- `verify_slides.py`: unique slide ids, every `COVERS` target is a defined concept, every
  slide has all required properties, and every concept of the chapter is covered by at
  least one slide.
- `verify_edges.py`: every endpoint is a defined concept, no duplicates or self-loops, the
  `PREREQUISITE` graph is acyclic, the combined `PREREQUISITE` + `FACILITATOR` graph is
  acyclic, and no pair is both `PREREQUISITE` and `SAME_AS`, or `FACILITATOR` and another
  type. Cross-chapter edges must point from a later to an earlier chapter, never forward;
  their number is reported for review.
- `verify_questions.py`: unique question ids, every `TESTS` target is a defined concept,
  and every chapter with questions has its `HAS_QUESTION` edges.

After stage 1, slides without a `COVERS` edge (table of contents, agenda, dividers) are
removed automatically.

---

## Architecture

LectureToGraph consists of three components, deployed with Docker Compose:

```
 Lecturer ──▶ Frontend (React, TypeScript)
               job setup · questions · validation gates · graph view (neovis.js)
                   │ REST                ▲ server-sent events        │ Bolt (display)
                   ▼                     │                           ▼
               Backend (FastAPI, async) ─┘                     Neo4j (staging)
               ├─ pipeline runner   stages and chapters              ▲
               ├─ agent loop ──▶ provider adapters ──▶ Anthropic / OpenAI / cluster
               │     └─ tools ──▶ job workspace (PDFs, .cypher files)
               ├─ skills        SKILL.md + scripts per stage
               └─ Cypher loader ─────────────────────────────────────┘
                     └─ upload ──▶ production Neo4j
```

- **Frontend** – lets the lecturer provide the lecture material, answer the agent's
  questions and review and approve each stage.
- **Backend** – runs the agent with its tools and loads the generated Cypher into the
  staging database. Processing a chapter takes several minutes and waits for the lecturer at
  every gate, so it runs asynchronously; a job survives a lost browser connection.
- **Neo4j** – the staging database holds the graph until it is exported or uploaded.

Backend modules (`backend/app/`):

- `ai/` – agent loop, provider adapters, tool schemas and execution, PDF reading.
- `pipeline/` – `runner.py` drives stages and chapters, `stages.py` holds the
  chapter-aware kickoff prompts, `cypher_loader.py` loads Cypher and provides the
  lecture- and chapter-scoped delete and export functions.
- `skills/` – the three skills and `registry.py`, which builds the system prompt
  (`SKILL.md` + environment addendum + language directive).
- `jobs/` – in-memory job store, per-job event bus for SSE, workspace handling.
- `api/routes/` – REST endpoints.

---

## Visualisation and editing

- Colours per node and edge type; `PREREQUISITE` is red, `FACILITATOR` yellow,
  review questions purple with dashed `TESTS` edges.
- **Right-click a node** to see all its properties and edit or delete it.
- The editor panel at the gate adds, changes or deletes nodes and edges by id.
- **Filter** menu: hide individual node types, edge types or chapters; "structure only"
  hides all semantic edges. Semantic edges never take part in the physics simulation, so
  they do not distort the tree layout.
- **Only latest changes** shows just what the last stage created in the current chapter,
  including the endpoints of new edges.
- **Hierarchical layout** arranges the nodes as a tree by level.

---

## Export and Neo4j upload

- **Per-chapter Cypher.** When a chapter is finished, its stage files are consolidated into
  one self-contained `<CODE>_CHnn.cypher` (constraints, lecture node, all chapter nodes and
  edges), read back from Neo4j so it includes manual edits.
- **Save manual changes to Cypher** writes the complete current graph as
  `<CODE>_full.cypher`; **Current graph** downloads it directly.
- **Bundled Neo4j** – shows the connection data and a sample query; "load again" makes sure
  the database matches the exported Cypher.
- **Own Neo4j** – enter URI, user, password and optionally the database to upload the
  graph. `localhost` / `127.0.0.1` is rewritten to `host.docker.internal` so the container
  reaches your host. Note that port `7687` is already taken by the bundled database.

All statements use `MERGE`, so loading a file twice yields the same graph.

---

## Configuration

All settings come from environment variables (pydantic-settings, see
`backend/app/config.py`). Docker Compose passes the provider variables from `.env`.

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | – | Anthropic access |
| `ANTHROPIC_MODEL` / `ANTHROPIC_MODEL_FAST` | `claude-opus-4-8` / `claude-sonnet-4-6` | preselected model / fallback entries if the model list cannot be fetched |
| `OPENAI_API_KEY` | – | OpenAI access |
| `OPENAI_MODEL` / `OPENAI_MODEL_FAST` | `gpt-5.4` / `gpt-5.4-mini` | as above |
| `CLUSTER_BASE_URL` | – | OpenAI-compatible endpoint; empty hides the provider. For OpenWebUI it must end in `/api/v1`. |
| `CLUSTER_API_KEY` | – | key for the endpoint |
| `CLUSTER_LABEL` | `Hochschul-Cluster` | name shown in the UI |
| `CLUSTER_MODEL` / `CLUSTER_MODEL_FAST` | `ultrabrain` / – | preselected model / fallback entries |
| `CLUSTER_CA_BUNDLE` | – | server certificate for a self-signed endpoint (path inside the container, e.g. `/certs/cluster_ca.pem`) |
| `CLUSTER_VERIFY_SSL` | `true` | last resort: disable certificate checks |
| `NEO4J_URI` | `bolt://neo4j:7687` (Compose) | staging database for the backend |
| `NEO4J_BROWSER_URI` | `bolt://localhost:7687` | Bolt URL used by the browser (neovis.js) |
| `WORKSPACE_DIR` | `/work` (Compose) | job workspaces |
| `PDF_RENDER_DPI` | `110` | render resolution |
| `PDF_MAX_PAGES_PER_BATCH` | `5` | pages per `read_pdf` call |
| `PDF_IMAGE_MAX_EDGE` | `1568` | longest image edge in pixels |
| `AGENT_MAX_TURNS` | `60` | safety limit of model calls per stage |
| `AGENT_MAX_TOKENS` | `8192` | output tokens per model call |

For the cluster, the model list is fetched live from `GET <CLUSTER_BASE_URL>/models`, so
every model the endpoint offers appears in the dropdown.

> Neo4j 5 Community has no role-based access control, so the browser uses the standard
> credentials (`neo4j` / `password`). This is fine for a local single-user tool.

---

## API overview

All routes are under `/api`; the interactive documentation is at
http://localhost:8000/docs.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/config/providers` | providers with availability and live model list |
| `POST` | `/jobs` | create a job (`provider`, `model`, `language`) |
| `POST` | `/jobs/{id}/pdfs` | upload PDFs |
| `POST` | `/jobs/{id}/start` | start the pipeline |
| `GET` | `/jobs/{id}` | job state |
| `GET` | `/jobs/{id}/events` | SSE stream (status, log, tool, question, gate, error) |
| `POST` | `/jobs/{id}/answer` | answer `ask_user` and resume |
| `POST` | `/jobs/{id}/gate/approve` | approve the stage |
| `POST` | `/jobs/{id}/stage/rerun` | re-run the stage with optional feedback |
| `POST` | `/jobs/{id}/add-chapter` | continue with the next chapter |
| `POST` | `/jobs/{id}/finish` | finish the lecture |
| `POST` | `/jobs/{id}/language` | switch language (`de` / `en`) |
| `GET` | `/jobs/{id}/viz-config` | neovis.js configuration incl. "latest changes" query |
| `GET` | `/jobs/{id}/artifact?path=` | download a workspace file |
| `GET` | `/jobs/{id}/full-cypher` | download the complete graph as Cypher |
| `POST` | `/jobs/{id}/save-cypher` | save the complete graph as workspace file |
| `GET` | `/jobs/{id}/bundled-access` | connection data of the bundled Neo4j |
| `POST` | `/jobs/{id}/load-bundled` | load the graph into the bundled Neo4j again |
| `POST` | `/jobs/{id}/upload-neo4j` | upload the graph into an external Neo4j |
| `GET` | `/lectures`, `/lectures/{code}/graph` | list lectures, lecture subgraph |
| `DELETE` | `/lectures/{code}` | delete a lecture |
| `POST` / `PUT` / `DELETE` | `/nodes`, `/nodes/{id}`, `/edges` | manual graph editing |

---

## Runtime and cost

Measured in the thesis (section 4.2.5) on chapter 6 of *Big-Data-Technologien* over all three
stages, with a script answering every question immediately and approving every stage without
re-runs:

| Model | Slides | Duration | Cached input | Cost | Concepts / edges / questions | Est. cost per chapter | Est. cost for 7 chapters |
|---|---|---|---|---|---|---|---|
| Kimi-K2.7 (cluster) | 20 | 6 min | – | – | 38 / 37 / 0 | – | – |
| Kimi-K2.7 (cluster) | 67 | 28 min | – | – | 76 / 83 / 10 | – | – |
| gpt-5.4 | 20 | 3 min | 77 % | $0.89 | 30 / 28 / 0 | ≈ $4.39 | ≈ $30.70 |
| gpt-5.4-mini | 20 | 4 min | 93 % | $0.27 | 27 / 0 / 8 | ≈ $1.24 | ≈ $8.65 |

- Each model call resends the whole conversation including all rendered slide images, so
  the input grows with every call (1.17 M tokens for 20 slides, 5.76 M for the full chapter
  with Kimi-K2.7). Provider prompt caching absorbs a large part of this.
- The estimates are lower bounds: re-runs at the gates add further calls, and the input
  grows more than linearly with the number of slides.
- gpt-5.4-mini went through stage 2 without writing a single edge and created 8 review
  questions that are not on the slides. Use a stronger model for graph generation.
- The cluster does not bill per token. Kimi-K2.7 is no longer offered there.

---

## Limitations

- Jobs are kept in memory; restarting the backend loses running jobs. The staged graph in
  Neo4j and the workspace files remain.
- A re-run regenerates the whole stage of the chapter instead of applying a targeted
  correction, which costs additional tokens.
- The counts above say nothing about the correctness of the generated nodes and edges;
  that is what the validation gates are for.

---

## Project structure

```
backend/
  app/
    ai/           agent loop, provider adapters, tools, PDF reading
    api/routes/   jobs, config_meta, nodes, edges, graph, lectures
    db/           Neo4j driver lifecycle
    jobs/         job store, event bus (SSE), workspace
    models/       pydantic models: domain, ai, jobs
    pipeline/     runner, stages, cypher_loader
    skills/       the three skills (SKILL.md, scripts, references, examples) + registry
    config.py     settings
    main.py       FastAPI app
  Dockerfile, requirements.txt
frontend/
  src/
    components/   JobSetup, PipelineStepper, ProgressLog, GraphView, NodeInfoPopup,
                  QuestionPanel, ValidationPanel, NodeEditForm, EdgeEditForm,
                  NextChapterPanel, ExportButtons, Neo4jUploadForm, LanguageToggle
    api/client.ts, store/pipelineStore.ts, types/graph.ts
  Dockerfile, nginx.conf, package.json
certs/            server certificate for a self-signed cluster endpoint (git-ignored)
docker-compose.yml
Beispiel-Vorlesung.pdf
```

---

## Tech stack

**Backend:** Python 3.11 · FastAPI · async Neo4j driver · pydantic-settings · sse-starlette ·
anthropic · openai · httpx · PyMuPDF · pdfplumber

**Frontend:** React 18 · TypeScript · Vite · zustand · neovis.js · axios

**Infrastructure:** Docker Compose · Neo4j 5 Community · nginx (static frontend and reverse proxy)

Source code: https://github.com/Barbarossa2711/LectureToGraph
