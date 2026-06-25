from sqlalchemy.orm import Session, joinedload

from app.api.provisions.concepts.concepts_schema import (
    ConceptCreateRequest,
    ConceptUpdateRequest,
)
from app.models.finance.provision_model import ProvisionConcept


class ConceptsRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_concepts(self, search: str | None = None):
        # Placeholder for fetching concepts from the database
        query = self.db.query(ProvisionConcept).options(
            joinedload(ProvisionConcept.company)
        )
        if search:
            query = query.filter(ProvisionConcept.name.contains(search))
        return query.all()

    def get_concept_by_id(self, concept_id: int):
        return (
            self.db.query(ProvisionConcept)
            .options(joinedload(ProvisionConcept.company))
            .filter(ProvisionConcept.id == concept_id)
            .first()
        )

    def get_concept_by_company_and_code(
        self,
        company_id: int,
        code: str,
    ):
        return (
            self.db.query(ProvisionConcept)
            .filter(
                ProvisionConcept.company_id == company_id,
                ProvisionConcept.code == code,
            )
            .first()
        )

    def create_concept(self, concept_data: ConceptCreateRequest, current_user_id: int):
        new_concept = ProvisionConcept(
            **concept_data.model_dump(), created_by=current_user_id
        )
        self.db.add(new_concept)
        return new_concept

    def update_concept(
        self, concept_id: int, concept_data: ConceptUpdateRequest, current_user_id: int
    ):
        concept = self.get_concept_by_id(concept_id)
        if concept:
            concept.updated_by = current_user_id
            update_data = concept_data.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(concept, key, value)
            return concept
        return None

    def delete_concept(self, concept_id: int, current_user_id: int):
        concept = self.get_concept_by_id(concept_id)
        if concept:
            concept.active = False
            concept.updated_by = current_user_id
            return True
        return False

    def commit(self):
        self.db.commit()

    def rollback(self):
        self.db.rollback()
