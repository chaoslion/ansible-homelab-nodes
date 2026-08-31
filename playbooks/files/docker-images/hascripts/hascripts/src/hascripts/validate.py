from typing import Annotated, TypeAlias

import pydantic


class ConfigModel(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(
        extra="forbid",
        frozen=True,
    )


FieldNonEmptyString: TypeAlias = Annotated[
    str,
    pydantic.Field(min_length=1),
]
FieldNonEmptyOptionalString: TypeAlias = Annotated[
    str | None,
    pydantic.Field(min_length=1),
]
FieldPositiveInt: TypeAlias = Annotated[
    int,
    pydantic.Field(gt=0),
]
FieldPositiveOptionalInt: TypeAlias = Annotated[
    int | None,
    pydantic.Field(gt=0),
]
FieldUrl: TypeAlias = pydantic.HttpUrl
