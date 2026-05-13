# LectureToGraph

Werkzeug zur Modellierung von Vorlesungsstrukturen als Wissensgraph in Neo4j.
Professoren können Kapitel, Themen, Konzepte und Wiederholungsfragen manuell
im Browser-Editor anlegen und Abhängigkeiten (inkl. kapitelübergreifender
Voraussetzungen) als Kanten definieren. Der Graph dient als Domain-Model für
ein späteres adaptives Lernsystem.

---

## Voraussetzungen

| Komponente | Version | Hinweis |
|---|---|---|
| Python | 3.11 | venv liegt unter `.venv/` |
| Node.js | ≥ 18 | Installation siehe unten |
| Docker | beliebig | für Neo4j |

---

## Starten (Entwicklung)

### 1 · Neo4j via Docker

```bash
docker run -d --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:3.5
```

> Neo4j Browser ist anschließend unter http://localhost:7474 erreichbar
> (Login: `neo4j` / `password`).

Falls der Container bereits existiert und gestoppt ist:

```bash
docker start neo4j
```

---

### 2 · Backend (FastAPI)

```bash
cd backend
cp .env.example .env          # nur beim ersten Mal nötig
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API läuft auf **http://localhost:8000**  
Interaktive Docs: http://localhost:8000/docs

---

### 3 · Frontend (React + Vite)

Node.js muss installiert sein. Falls nicht vorhanden, einmalig via nvm:

```bash
curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
# Terminal neu starten, dann:
nvm install --lts
```

Frontend starten:

```bash
cd frontend
npm install        # nur beim ersten Mal nötig
npm run dev
```

App läuft auf **http://localhost:5173**

---

## Starten via Docker Compose (alternativ)

Startet Neo4j, Backend und Frontend in einem Schritt:

```bash
docker-compose up --build
```

| Dienst | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000/docs |
| Neo4j Browser | http://localhost:7474 |

---

## Graph-Schema

### Knotentypen

| Label | Felder |
|---|---|
| `Lecture` | title, professor, description, semester |
| `Chapter` | title, description, order |
| `Topic` | title, description, order |
| `Subtopic` | title, description, order |
| `Concept` | title, definition, examples |
| `ReviewQuestion` | question, answer |

### Kantentypen

| Beziehung | Richtung | Bedeutung |
|---|---|---|
| `HAS_CHAPTER` | Lecture → Chapter | Kapitel gehört zur Vorlesung |
| `HAS_TOPIC` | Chapter → Topic | Thema gehört zu Kapitel |
| `HAS_SUBTOPIC` | Topic → Subtopic | Unterthema gehört zu Thema |
| `HAS_CONCEPT` | Topic/Subtopic → Concept | Konzept gehört zu Thema |
| `HAS_REVIEW_QUESTION` | Chapter → ReviewQuestion | Frage gehört zu Kapitel |
| `TESTS_UNDERSTANDING_OF` | ReviewQuestion → Concept/Topic | Frage testet dieses Konzept |
| `REQUIRES` | Node → Node | Voraussetzung (A→B: um A zu lernen braucht man B) |
| `RELATES_TO` | Node → Node | Inhaltliche Verwandtschaft |

---

## Bedienung

**Toolbar** (über dem Canvas):

| Werkzeug | Funktion |
|---|---|
| ↖ Auswählen | Knoten anklicken um Details zu bearbeiten, verschieben per Drag |
| ⊕ Knoten hinzufügen | Auf den Canvas klicken → Dialog mit Typ und Titel |
| ✕ Löschen | Knoten oder Kante anklicken zum Löschen |
| ↺ Layout zurücksetzen | Hierarchisches Auto-Layout (Dagre) neu berechnen |

**Kanten erstellen:** Vom unteren Ankerpunkt eines Knotens zur oberen
Markierung eines anderen Knotens ziehen → Kantentyp-Dialog erscheint mit
intelligentem Vorschlag basierend auf den Knotentypen.

**Kanten bearbeiten:** Kante anklicken → Typ ändern oder löschen.
