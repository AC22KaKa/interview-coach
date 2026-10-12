"""Compatibility with the previous project's ResumeResult export."""
from pydantic import BaseModel, Field, field_validator, model_validator


class Bullet(BaseModel):
    star: str = Field(min_length=10)
    metric: str = Field(min_length=1)


class ResumeResult(BaseModel):
    project_name: str = Field(min_length=1)
    matched_keywords: list[str] = Field(default_factory=list)
    bullets: list[Bullet] = Field(min_length=2, max_length=5)
    interview_questions: list[str] = Field(min_length=3, max_length=8)
    needs_clarification: bool = False
    clarifying_questions: list[str] = Field(default_factory=list)

    @field_validator("matched_keywords", "interview_questions", "clarifying_questions")
    @classmethod
    def nonempty(cls, values):
        if any(not value.strip() for value in values):
            raise ValueError("列表不能包含空文本")
        return [value.strip() for value in values]

    @model_validator(mode="after")
    def clarification(self):
        if self.needs_clarification != bool(self.clarifying_questions):
            raise ValueError("澄清标记与问题列表不一致")
        return self


def import_resume(data: bytes) -> str:
    if len(data) > 1_000_000:
        raise ValueError("JSON 文件不能超过 1 MB")
    result = ResumeResult.model_validate_json(data)
    lines = [result.project_name]
    for bullet in result.bullets:
        lines.extend([f"- {bullet.star}", f"  指标（请核实）：{bullet.metric}"])
    if result.clarifying_questions:
        lines.append("待补充：" + "；".join(result.clarifying_questions))
    return "\n".join(lines)
