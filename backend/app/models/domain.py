from enum import Enum
from typing import Any
from pydantic import BaseModel


# Node labels and edge types match the vendored skills' Cypher output exactly.

class NodeType(str, Enum):
    LECTURE = "Lecture"
    CHAPTER = "Chapter"
    TOPIC = "Topic"
    SUBTOPIC = "Subtopic"
    CONCEPT = "Concept"
    QUESTION = "Question"


class EdgeType(str, Enum):
    # hierarchy
    HAS_CHAPTER = "HAS_CHAPTER"
    HAS_TOPIC = "HAS_TOPIC"
    HAS_SUBTOPIC = "HAS_SUBTOPIC"
    HAS_CONCEPT = "HAS_CONCEPT"
    # concept dependency edges
    PREREQUISITE = "PREREQUISITE"
    FACILITATOR = "FACILITATOR"
    SAME_AS = "SAME_AS"
    # review questions
    HAS_QUESTION = "HAS_QUESTION"
    TESTS = "TESTS"


NODE_LABELS = [t.value for t in NodeType]

# Which edge points from a parent to this node type (used when creating a node
# manually at a validation gate). TESTS is not a parent edge (Question->Concept).
PARENT_EDGE: dict[NodeType, EdgeType] = {
    NodeType.CHAPTER: EdgeType.HAS_CHAPTER,
    NodeType.TOPIC: EdgeType.HAS_TOPIC,
    NodeType.SUBTOPIC: EdgeType.HAS_SUBTOPIC,
    NodeType.CONCEPT: EdgeType.HAS_CONCEPT,
    NodeType.QUESTION: EdgeType.HAS_QUESTION,
}


# ---------- Node ----------

class NodeCreate(BaseModel):
    id: str
    node_type: NodeType
    parent_id: str | None = None
    properties: dict[str, Any] = {}


class NodeUpdate(BaseModel):
    properties: dict[str, Any]


class NodeResponse(BaseModel):
    id: str
    node_type: NodeType
    properties: dict[str, Any]


# ---------- Edge ----------

class EdgeCreate(BaseModel):
    source_id: str
    target_id: str
    edge_type: EdgeType


class EdgeResponse(BaseModel):
    source_id: str
    target_id: str
    edge_type: EdgeType


# ---------- Graph (for neovis.js / vis-network fallback) ----------

class GraphNode(BaseModel):
    id: str
    node_type: NodeType
    properties: dict[str, Any]


class GraphEdge(BaseModel):
    source_id: str
    target_id: str
    edge_type: EdgeType


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


# ---------- Lecture summary (derived from staged Lecture nodes) ----------

class LectureSummary(BaseModel):
    id: str
    code: str
    name: str | None = None
    prof: str | None = None
    term: str | None = None
