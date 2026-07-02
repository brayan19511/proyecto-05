from sqlalchemy.exc import IntegrityError

from app.api.master.master_service import MasterService
from app.api.provisions.concepts.concepts_repository import ConceptsRepository
from app.api.provisions.concepts.concepts_schema import (
    ConceptCreateRequest,
    ConceptUpdateRequest,
)
from app.core.db.integrity import raise_integrity_error
from app.core.exceptions import ConflictError, NotFoundError


class ConceptsService:
    def __init__(self, db):
        self.db = db
        self.repository = ConceptsRepository(db)

    def get_concepts(self, search: str | None = None):
        return self.repository.get_concepts(search=search)

    def get_concept_by_id(self, concept_id: int):
        return self._get_or_404(concept_id)

    def create_concept(
        self,
        concept_data: ConceptCreateRequest,
        current_user_id,
    ):
        self._validate_company(concept_data.company_id)
        data = concept_data.model_dump()
        data["code"] = data["code"].strip().upper()

        if self.repository.get_concept_by_company_and_code(
            data["company_id"],
            data["code"],
        ):
            raise ConflictError(
                "Ya existe un concepto con este codigo para la empresa"
            )

        try:
            concept = self.repository.create_concept(
                ConceptCreateRequest(**data),
                current_user_id,
            )
            self.repository.commit()
            return concept
        except IntegrityError as exc:
            self.repository.rollback()
            raise_integrity_error(
                exc,
                conflicts={
                    "provision_concepts_company_id_code_key": (
                        "Ya existe un concepto con este codigo para la empresa"
                    )
                },
                invalid_references={
                    "provision_concepts_company_id_fkey": (
                        "La empresa indicada no existe"
                    )
                },
            )

    def update_concept(
        self,
        concept_id: int,
        concept_data: ConceptUpdateRequest,
        current_user_id,
    ):
        concept = self._get_or_404(concept_id)
        data = concept_data.model_dump(exclude_unset=True)
        company_id = data.get("company_id", concept.company_id)
        code = data.get("code", concept.code)

        if "company_id" in data:
            self._validate_company(company_id)

        if code is not None:
            code = code.strip().upper()
            data["code"] = code
            existing = self.repository.get_concept_by_company_and_code(
                company_id,
                code,
            )
            if existing and existing.id != concept_id:
                raise ConflictError(
                    "Ya existe un concepto con este codigo para la empresa"
                )

        try:
            updated = self.repository.update_concept(
                concept_id,
                ConceptUpdateRequest(**data),
                current_user_id,
            )
            self.repository.commit()
            return updated
        except IntegrityError as exc:
            self.repository.rollback()
            raise_integrity_error(
                exc,
                conflicts={
                    "provision_concepts_company_id_code_key": (
                        "Ya existe un concepto con este codigo para la empresa"
                    )
                },
                invalid_references={
                    "provision_concepts_company_id_fkey": (
                        "La empresa indicada no existe"
                    )
                },
            )

    def delete_concept(self, concept_id: int, current_user_id):
        self._get_or_404(concept_id)
        deleted = self.repository.delete_concept(concept_id, current_user_id)
        self.repository.commit()
        return deleted

    def _validate_company(self, company_id: int):
        MasterService(self.db).get_company_by_id(company_id)

    def _get_or_404(self, concept_id: int):
        concept = self.repository.get_concept_by_id(concept_id)
        if not concept:
            raise NotFoundError("Concepto no encontrado")
        return concept
