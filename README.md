# LectureToGraph

**KI-gestützte Pipeline, die aus Vorlesungs-PDFs ein Wissensgraph-Domainmodell in
Neo4j erzeugt.** Ein provider-unabhängiger Agent (Anthropic *oder* OpenAI) liest die
Folien, baut Schritt für Schritt einen Cypher-Wissensgraphen auf und lässt dich
zwischen jedem Schritt das Ergebnis visuell prüfen, manuell bearbeiten und freigeben.
Verarbeitet wird **kapitelweise** — sowohl ein großes Gesamt-Dokument als auch
einzelne Kapitel-PDFs.

Der Graph dient als Domain-Model für ein späteres adaptives Lernsystem.

---

## Inhaltsverzeichnis

- [Funktionsumfang](#funktionsumfang)
- [Schnellstart (Docker Compose)](#schnellstart-docker-compose)
- [Ablauf / Bedienung](#ablauf--bedienung)
- [Graph-Schema](#graph-schema)
- [Architektur](#architektur)
- [Visualisierung](#visualisierung)
- [Export & Neo4j-Upload](#export--neo4j-upload)
- [Konfiguration](#konfiguration)
- [API-Überblick](#api-überblick)
- [Projektstruktur](#projektstruktur)
- [Tech-Stack](#tech-stack)

---

## Funktionsumfang

- **Provider-unabhängig** – Anthropic (Claude) oder OpenAI (GPT). Das Modell-Dropdown
  wird **live** aus den mit dem API-Key tatsächlich verfügbaren Modellen befüllt.
- **PDF-Vision** – die Folien werden als Text *und* gerenderte Seitenbilder gelesen
  (PyMuPDF + pdfplumber), seitenweise in Batches.
- **3-stufige Pipeline pro Kapitel** – Domainmodell → Konzept-Kanten →
  Wiederholungsfragen, jeweils mit Validierungs-Gate.
- **Kapitel-inkrementell** – ein Gesamt-PDF wird kapitelweise iteriert (die KI erkennt
  die Kapitel und lässt sie bestätigen); bei einzelnen Kapitel-PDFs kann am Ende ein
  weiteres Kapitel hinzugefügt werden.
- **Live-Validierung** – nach jedem Schritt wird der Graph in einem Neo4j-Browser-Look
  (neovis.js) angezeigt. Knoten/Kanten lassen sich manuell hinzufügen, per Rechtsklick
  ansehen/bearbeiten/löschen.
- **Cypher als Quelle der Wahrheit** – jeder Schritt erzeugt `.cypher`-Dateien;
  manuelle Änderungen lassen sich jederzeit in eine Cypher-Datei speichern.
- **Neo4j-Upload** – in die mitgelieferte Docker-Neo4j (neu) laden oder in eine
  **eigene** Neo4j (Desktop / eigener Docker) per Zugangsdaten-Formular hochladen.
- **Deutsch/English** – die KI-Rückfragen sind standardmäßig auf Deutsch, umschaltbar.
- **Resumierbar** – Jobs laufen asynchron, der Fortschritt kommt per SSE live an;
  ein Reconnect rehydriert den Zustand.

---

## Schnellstart (Docker Compose)

### 1 · API-Key(s) hinterlegen

Im Projekt-Root eine `.env` anlegen (ist über `.gitignore` ausgeschlossen):

```dotenv
# mindestens einen der beiden Keys setzen
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
```

### 2 · Stack starten

```bash
docker compose up --build
```

| Dienst | URL | Login |
|---|---|---|
| **App (Frontend)** | http://localhost:5173 | – |
| Backend-API / Docs | http://localhost:8000/docs | – |
| Neo4j Browser | http://localhost:7474 | `neo4j` / `password` |
| Neo4j Bolt | `bolt://localhost:7687` | `neo4j` / `password` |

Die mitgelieferte Neo4j-Datenbank ist die Staging-DB, die auch die Visualisierung
speist. Die Daten liegen im Docker-Volume `neo4j_data` und überleben Neustarts
(`docker compose down -v` löscht das Volume).

> **Test-PDF:** `Beispiel-Vorlesung.pdf` (eine kurze 2-seitige Beispiel-Vorlesung
> „Einführung in Datenbanksysteme") liegt im Root und kann direkt hochgeladen werden.

---

## Ablauf / Bedienung

1. **Job anlegen** – Anbieter, Modell und Sprache wählen, ein oder mehrere
   Vorlesungs-PDF(s) hochladen, „KI-Modus starten".
2. **Kapitel 1 · Domainmodell** – die KI liest die Folien. Bei einem Gesamt-PDF
   schlägt sie die Kapitelstruktur vor und fragt nach Bestätigung; sie verarbeitet
   genau **ein** Kapitel und schreibt das `.cypher`. Eventuelle Rückfragen erscheinen
   rechts.
3. **Validieren** – der Graph wird angezeigt. Du kannst Knoten/Kanten manuell
   anpassen und dann **freigeben** oder den Schritt mit Feedback **neu generieren**.
4. **Konzept-Kanten** – `PREREQUISITE` / `FACILITATOR` / `SAME_AS` für die Konzepte
   des Kapitels (mit Verifikations-Gate). → validieren.
5. **Wiederholungsfragen** – `Question`-Knoten + `HAS_QUESTION`/`TESTS`. → validieren.
6. **Kapitel fertig** – „**+ Weiteres Kapitel hinzufügen**" (optional neues PDF
   hochladen, sonst nimmt die KI das nächste Kapitel aus dem Gesamt-Dokument) oder
   „**Vorlesung abschließen**".

Reruns sind kapitel-gescopt: ein Neu-Generieren von Kapitel 2 betrifft nur Kapitel 2.

---

## Graph-Schema

Standardisiert auf das Skill-Schema (vgl. `backend/app/models/domain.py`).

### Knoten

| Label | wichtige Properties |
|---|---|
| `Lecture` | `id` (= `code`), `name`, `degreeType`, `term`, `PO`, `prof` |
| `Chapter` | `id`, `name`, `index` |
| `Topic` | `id`, `name`, `index` |
| `Subtopic` | `id`, `name`, `index` |
| `Concept` | `id`, `name`, `index` |
| `Question` | `id`, `text`, `index`, `chapter`, `pageNumber`, `source`, `note?` |

### Kanten

| Beziehung | Richtung | Bedeutung |
|---|---|---|
| `HAS_CHAPTER` | Lecture → Chapter | strukturelle Hierarchie |
| `HAS_TOPIC` | Chapter → Topic | strukturelle Hierarchie |
| `HAS_SUBTOPIC` | Topic → Subtopic | strukturelle Hierarchie |
| `HAS_CONCEPT` | Topic/Subtopic → Concept | strukturelle Hierarchie |
| `PREREQUISITE` | Concept → Concept | setzt voraus |
| `FACILITATOR` | Concept → Concept | erleichtert |
| `SAME_AS` | Concept → Concept | inhaltlich gleich (Deduplizierung) |
| `HAS_QUESTION` | Chapter → Question | Frage gehört zum Kapitel |
| `TESTS` | Question → Concept | Frage testet dieses Konzept |

### ID-Schema (Scoping-Schlüssel)

```
BDT                          Lecture (code)
BDT_CH01                     Chapter
BDT_CH01_T01                 Topic
BDT_CH01_T01_S01             Subtopic
BDT_CH01_T01_C01             Concept
BDT_CH01_Q01                 Question
```

Alles wird über das `code`-Präfix einer Vorlesung gescopt (`n.id STARTS WITH <code>`).
Alle Statements nutzen `MERGE` → idempotent und neu-ladbar.

---

## Architektur

```
PDF(s) ──▶ Agent-Loop ──▶ .cypher ──▶ Neo4j (Staging) ──▶ neovis.js (Visualisierung)
            │  (provider-agnostisch)            ▲                    │
            │  Tools: read_pdf, read_file,      │ manuelle Edits     │
            │  write_file, list_dir,            └────────────────────┘
            │  run_script, ask_user, stage_complete
            ▼
       Skills (SKILL.md + Scripts) pro Stage
```

### Backend (FastAPI, async)

- **Provider-agnostischer Agent-Loop** (`app/ai/`) mit einem normalisierten,
  Anthropic-förmigen Nachrichtenformat (Text/Image/ToolUse/ToolResult). Adapter
  übersetzen zu/von Anthropic und OpenAI (inkl. der Unterschiede bei Tool-Calls und
  Bildern in Tool-Results).
- **Tools** (`app/ai/tools.py`, `tool_exec.py`) – sandboxed auf den Job-Workspace,
  `run_script` nur für die je Stage erlaubten Skill-Scripts.
- **PDF** (`app/ai/pdf.py`) – PyMuPDF rendert Seiten, pdfplumber extrahiert Text;
  als multimodale Blöcke, seitenweise gebatcht.
- **Pipeline** (`app/pipeline/`) – `runner.py` steuert die Stages/Kapitel,
  `stages.py` enthält die kapitel-bewussten Kickoff-Prompts, `cypher_loader.py` lädt
  Cypher atomar und scope-gebunden in Neo4j.
- **Skills** (`app/skills/`) – drei vendored Claude-Skills (`lecture-domain-model`,
  `lecture-concept-edges`, `lecture-review-questions`) inkl. ihrer Verify-Scripts;
  `registry.py` baut den System-Prompt = `SKILL.md` + Umgebungs-Addendum + Sprache.
- **Jobs** (`app/jobs/`) – In-Memory-Store, per-Job Pub/Sub für SSE, Workspace-Handling.

### Frontend (React + Vite + TypeScript)

- `pipelineStore` (zustand) hält Job, Log und Viz-State; SSE-Anbindung über `EventSource`.
- `GraphView` mountet **neovis.js** direkt per Bolt an die App-Neo4j.
- Validierungs-Panel mit manueller Bearbeitung, Rechtsklick-Knoten-Popup,
  Kapitel-Loop-Panel, Export- und Neo4j-Upload-Optionen.

---

## Visualisierung

- **Farben** je Knoten- und Kantentyp; Beschriftungen dunkel und gut lesbar.
- **Knotengröße** nimmt mit der Hierarchie-Ebene ab (Lecture am größten, Question am
  kleinsten).
- **Rechtsklick auf einen Knoten** öffnet ein Popup mit allen Attributen → direkt
  editieren oder löschen (kein ID-Raten nötig).
- **„Nur Struktur"** (Schalter unten links) blendet die semantischen Kanten
  (`PREREQUISITE`/`FACILITATOR`/`SAME_AS`/`TESTS`) aus; diese beeinflussen ohnehin das
  Kräfte-Layout nicht (`physics: false`), damit die Hierarchie übersichtlich bleibt.
- **„Nur letzte Änderungen"** zeigt ausschließlich das, was der zuletzt gelaufene
  Schritt für das aktuelle Kapitel erzeugt hat (inkl. der Endknoten neuer Kanten).

---

## Export & Neo4j-Upload

- **Cypher-Export** – pro Schritt erzeugte `.cypher`-Dateien als Download.
- **„Manuelle Änderungen in Cypher speichern"** – serialisiert den **kompletten
  aktuellen Graphen** (inkl. manueller Edits) idempotent als `<code>_full.cypher`.
- **Mitgelieferte Neo4j (Docker)** – Zugangsdaten + Beispiel-Query werden angezeigt;
  „erneut laden" stellt sicher, dass die DB dem exportierten Cypher entspricht.
- **Eigene Neo4j (Desktop / eigener Docker)** – URI/Benutzer/Passwort eintragen und
  direkt hochladen. `localhost`/`127.0.0.1` wird automatisch auf `host.docker.internal`
  umgeschrieben, damit der Container den Host erreicht.

---

## Konfiguration

Alle Einstellungen via Environment (pydantic-settings, siehe `backend/app/config.py`).
Die wichtigsten Variablen (Defaults in Klammern):

| Variable | Default | Zweck |
|---|---|---|
| `ANTHROPIC_API_KEY` | – | Anthropic-Zugang |
| `OPENAI_API_KEY` | – | OpenAI-Zugang |
| `ANTHROPIC_MODEL` | `claude-opus-4-8` | Standard-Claude-Modell |
| `OPENAI_MODEL` | `gpt-5.4` | Standard-OpenAI-Modell |
| `NEO4J_URI` | `bolt://neo4j:7687` | Staging-DB (im Compose-Netz) |
| `NEO4J_BROWSER_URI` | `bolt://localhost:7687` | Bolt-URL für den Browser/neovis |
| `WORKSPACE_DIR` | `/work` (Compose) | Job-Workspace |
| `PDF_RENDER_DPI` | `110` | Render-Auflösung |
| `PDF_MAX_PAGES_PER_BATCH` | `5` | Seiten pro `read_pdf`-Aufruf |
| `AGENT_MAX_TURNS` | `60` | Sicherheitslimit pro Stage |
| `AGENT_MAX_TOKENS` | `8192` | Output-Tokens pro Modellaufruf |

> Neo4j 5 Community hat kein RBAC – der Browser/neovis nutzt daher die Standard-
> Zugangsdaten (`neo4j`/`password`). Für ein lokales Einzelplatz-Tool ist das in Ordnung.

---

## API-Überblick

Alle Routen unter `/api`. Auswahl der Job-/Pipeline-Endpoints:

| Methode | Pfad | Zweck |
|---|---|---|
| `GET` | `/config/providers` | verfügbare Anbieter + (live) Modelle |
| `POST` | `/jobs` | Job anlegen (`provider`, `model`, `language`) |
| `POST` | `/jobs/{id}/pdfs` | PDF(s) hochladen |
| `POST` | `/jobs/{id}/start` | Pipeline starten |
| `GET` | `/jobs/{id}/events` | SSE-Stream (Status/Log/Frage/Gate/Fehler) |
| `POST` | `/jobs/{id}/answer` | `ask_user` beantworten (Resume) |
| `POST` | `/jobs/{id}/gate/approve` | Schritt freigeben |
| `POST` | `/jobs/{id}/stage/rerun` | Schritt neu generieren (mit Feedback) |
| `POST` | `/jobs/{id}/add-chapter` | weiteres Kapitel hinzufügen |
| `POST` | `/jobs/{id}/finish` | Vorlesung abschließen |
| `POST` | `/jobs/{id}/language` | Sprache umschalten (`de`/`en`) |
| `GET` | `/jobs/{id}/viz-config` | neovis-Konfiguration (inkl. „letzte Änderungen") |
| `GET` | `/jobs/{id}/full-cypher` | kompletten Graphen als Cypher herunterladen |
| `POST` | `/jobs/{id}/save-cypher` | aktuellen Graphen als Artefakt speichern |
| `POST` | `/jobs/{id}/load-bundled` | in die mitgelieferte Neo4j (neu) laden |
| `POST` | `/jobs/{id}/upload-neo4j` | in eine externe Neo4j hochladen |
| `GET`/`POST`/`PUT`/`DELETE` | `/nodes`, `/edges` | manuelle Graph-Bearbeitung |

---

## Projektstruktur

```
backend/
  app/
    ai/          Agent-Loop, Provider-Adapter, Tools, PDF-Handling
    api/routes/  jobs, config_meta, nodes, edges, graph, lectures
    db/          Neo4j-Treiber-Lifecycle
    jobs/        Job-Store, Event-Bus (SSE), Workspace
    models/      domain, ai, jobs (pydantic)
    pipeline/    runner, stages, cypher_loader
    skills/      die 3 vendored Skills + registry
    config.py    Settings
    main.py      FastAPI-App
  Dockerfile, requirements.txt
frontend/
  src/
    components/  JobSetup, PipelineStepper, GraphView, ValidationPanel,
                 NodeEditForm/EdgeEditForm, NodeInfoPopup, NextChapterPanel,
                 ExportButtons, Neo4jUploadForm, LanguageToggle, ProgressLog,
                 QuestionPanel
    api/client.ts, store/pipelineStore.ts, types/graph.ts
  Dockerfile, nginx.conf, package.json
docker-compose.yml
Beispiel-Vorlesung.pdf
```

---

## Tech-Stack

**Backend:** FastAPI · async neo4j-Treiber · pydantic-settings · sse-starlette ·
anthropic · openai · PyMuPDF · pdfplumber

**Frontend:** React 18 · Vite · TypeScript · zustand · neovis.js · axios

**Infra:** Docker Compose · Neo4j 5 Community · nginx (Frontend + Reverse-Proxy)
