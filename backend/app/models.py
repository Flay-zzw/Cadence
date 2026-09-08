from typing import Literal, Annotated
from pydantic import BaseModel, Field, ConfigDict, SecretStr


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Page(StrictModel):
    id: str = Field(min_length=1, max_length=80)
    role: Literal['cover', 'hook', 'concept', 'explain', 'example', 'myth', 'summary', 'cta']
    title: str = Field(min_length=1, max_length=60)
    body: str = Field(min_length=1, max_length=400)
    highlights: list[Annotated[str, Field(min_length=1, max_length=80)]] = Field(min_length=1, max_length=3)
    visual_direction: str = Field(max_length=300)
    narration: str = Field(max_length=600)
    review_flags: list[str]


class Content(StrictModel):
    title: str = Field(min_length=1, max_length=100)
    source_summary: str
    audience: str
    style: Literal['clear-science']
    pages: list[Page] = Field(min_length=4, max_length=12)
    closing_cta: str


class PlannedPage(StrictModel):
    role: Page.model_fields['role'].annotation
    title: str = Field(min_length=1, max_length=60)
    brief: str = Field(min_length=1, max_length=500)


class Outline(StrictModel):
    title: str = Field(min_length=1, max_length=100)
    source_summary: str
    audience: str
    pages: list[PlannedPage] = Field(min_length=4, max_length=12)
    closing_cta: str


class Generate(StrictModel):
    aspect_ratio: Literal['9:16', '16:9'] = '9:16'
    article: str = Field(min_length=100, max_length=20000)
    audience: str = Field(default='普通成年人', min_length=1, max_length=100)
    tone: str = Field(default='亲切、清晰、有好奇心', min_length=1, max_length=100)
    pace: int = Field(default=180, ge=120, le=240)


class Settings(StrictModel):
    base_url: str = Field(min_length=1, max_length=300)
    model: str = Field(max_length=120)
    api_key: SecretStr | None = Field(default=None, max_length=1024)


class Regenerate(StrictModel):
    instruction: str = Field(min_length=1, max_length=1000)
    revision: int


class Edit(StrictModel):
    page: Page
    revision: int
