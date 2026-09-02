# app/api/security/user_scope/user_scope_schema.py

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UserAreaAccessRequest(BaseModel):
    """Asignacion de un usuario a un area de una empresa.

    ``area_id`` en None significa "todas las areas de esa empresa".
    """

    user_id: UUID
    company_id: int = Field(gt=0)
    area_id: int | None = Field(default=None, gt=0)


class UserScopeItemRequest(BaseModel):
    """Item de un reemplazo masivo del alcance de un usuario."""

    company_id: int = Field(gt=0)
    area_id: int | None = Field(default=None, gt=0)


class UserScopeReplaceRequest(BaseModel):
    """Reemplaza el alcance completo del usuario por esta lista."""

    items: list[UserScopeItemRequest] = Field(default_factory=list)


class UserAreaAccessResponse(BaseModel):
    id: int
    user_id: UUID
    company_id: int
    company_code: str | None = None
    company_name: str | None = None
    area_id: int | None = None
    area_code: str | None = None
    area_name: str | None = None
    active: bool

    model_config = ConfigDict(from_attributes=True)


class AreaRefResponse(BaseModel):
    id: int
    code: str
    name: str

    model_config = ConfigDict(from_attributes=True)


class CompanyScopeResponse(BaseModel):
    """Alcance del usuario dentro de una empresa (company > areas)."""

    company_id: int
    company_code: str
    company_name: str
    # True cuando el acceso cubre todas las areas de la empresa.
    all_areas: bool = False
    areas: list[AreaRefResponse] = Field(default_factory=list)


class UserScopeResponse(BaseModel):
    user_id: UUID
    # True para admin o para quien tiene permisos de "ver todo".
    unrestricted: bool = False
    companies: list[CompanyScopeResponse] = Field(default_factory=list)
