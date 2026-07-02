# app/api/provisions/concepts/concepts_router.py
from fastapi import APIRouter, Depends
from app.api.provisions.concepts.concepts_schema import (
    ConceptCreateRequest,
    ConceptResponse,
    ConceptUpdateRequest,
)
from app.api.provisions.concepts.concepts_service import ConceptsService
from app.core.db.db_postgres import get_db
from app.core.security import PermissionChecker, get_current_user

router = APIRouter(
    tags=["Provisions Concepts"],
)


@router.get("/", response_model=list[ConceptResponse])
async def get_concepts(
    search: str | None = None,
    db=Depends(get_db),
    current_user=Depends(PermissionChecker("provisions.concepts.view")),
):
    concepts_service = ConceptsService(db)
    return concepts_service.get_concepts(search=search)


@router.post("/")
async def create_concept(
    concept_data: ConceptCreateRequest,
    db=Depends(get_db),
    current_user=Depends(PermissionChecker("provisions.concepts.edit")),
):
    concepts_service = ConceptsService(db)
    return concepts_service.create_concept(concept_data, current_user.id)


@router.get("/{concept_id}", response_model=ConceptResponse)
async def get_concept(
    concept_id: int,
    db=Depends(get_db),
    current_user=Depends(PermissionChecker("provisions.concepts.view")),
):
    concepts_service = ConceptsService(db)
    return concepts_service.get_concept_by_id(concept_id)


@router.put("/{concept_id}", response_model=ConceptResponse)
async def update_concept(
    concept_id: int,
    concept_data: ConceptUpdateRequest,
    db=Depends(get_db),
    current_user=Depends(PermissionChecker("provisions.concepts.edit")),
):
    concepts_service = ConceptsService(db)
    return concepts_service.update_concept(concept_id, concept_data, current_user.id)


@router.delete("/{concept_id}")
async def delete_concept(
    concept_id: int,
    db=Depends(get_db),
    current_user=Depends(PermissionChecker("provisions.concepts.edit")),
):
    concepts_service = ConceptsService(db)
    return concepts_service.delete_concept(concept_id, current_user.id)
