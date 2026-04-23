from pydantic import BaseModel, ConfigDict, Field


class TagRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    color: str
    ioc_count: int = 0


class TagCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    color: str = Field(default="#58a6ff", min_length=4, max_length=7)


class AddTagRequest(BaseModel):
    tag_name: str = Field(min_length=1, max_length=64)
