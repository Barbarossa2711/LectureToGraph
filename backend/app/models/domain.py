from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class NodeType(str, Enum):
    LECTURE = "Lecture"
    CHAPTER = "Chapter"
    TOPIC = "Topic"
    SUBTOPIC = "Subtopic"
    CONCEPT = "Concept"
    REVIEW_QUESTION = "ReviewQuestion"


class EdgeType(str, Enum):
    HAS_CHAPTER = "HAS_CHAPTER"
    HAS_TOPIC = "HAS_TOPIC"
    HAS_SUBTOPIC = "HAS_SUBTOPIC"
    HAS_CONCEPT = "HAS_CONCEPT"
    RELATES_TO = "RELATES_TO"
    REQUIRES = "REQUIRES"
    HAS_REVIEW_QUESTION = "HAS_REVIEW_QUESTION"
    TESTS_UNDERSTANDING_OF = "TESTS_UNDERSTANDING_OF"


# ---------- Lecture ----------

class LectureCreate(BaseModel):
    title: str
    professor: str
    description: str | None = None
    semester: str | None = None


class LectureUpdate(BaseModel):
    title: str | None = None
    professor: str | None = None
    description: str | None = None
    semester: str | None = None


class LectureResponse(BaseModel):
    id: str
    title: str
    professor: str
    description: str | None = None
    semester: str | None = None


# ---------- Node ----------

class NodeProperties(BaseModel):
    title: str | None = None
    description: str | None = None
    order: int | None = None
    definition: str | None = None
    examples: str | None = None
    question: str | None = None
    answer: str | None = None
    difficulty: str | None = None


class NodeCreate(BaseModel):
    lecture_id: str
    node_type: NodeType
    properties: NodeProperties


class NodeUpdate(BaseModel):
    properties: NodeProperties


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


# ---------- Graph (für React Flow) ----------

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
