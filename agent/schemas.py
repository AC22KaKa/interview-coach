from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class Model(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class Question(Model):
    text: str = Field(min_length=5)
    topic: str = Field(min_length=1)
    action: Literal["new_topic", "follow_up"]


class Turn(Model):
    question: Question
    answer: str = Field(min_length=1)


class Evidence(Model):
    turn: int = Field(ge=1)
    quote: str = Field(min_length=1)


class Feedback(Model):
    dimension: Literal["相关性", "具体性", "技术解释", "表达结构"]
    assessment: str = Field(min_length=1)
    evidence: list[Evidence] = Field(min_length=1)
    suggestion: str = Field(min_length=1)


class Report(Model):
    feedback: list[Feedback] = Field(min_length=4, max_length=4)
    strengths: list[str]
    missing_facts: list[str]
    practice_questions: list[str] = Field(min_length=3, max_length=3)


class Session(Model):
    resume: str = Field(min_length=1)
    jd: str = Field(min_length=1)
    max_turns: int = Field(default=8, ge=1, le=20)
    status: Literal["active", "review", "complete"] = "active"
    current: Question | None = None
    followups: int = 0
    turns: list[Turn] = Field(default_factory=list)
    report: Report | None = None
