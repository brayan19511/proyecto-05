from uuid import UUID

from sqlalchemy.orm import Session

from app.models.storage import Attachment


class AttachmentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, attachment_id: UUID):
        return self.db.get(Attachment, attachment_id)

    def get_by_entity(
        self,
        entity_type: str,
        entity_id: UUID,
    ):
        return (
            self.db.query(Attachment)
            .filter(
                Attachment.entity_type == entity_type,
                Attachment.entity_id == entity_id,
            )
            .all()
        )

    def create(self, attachment: Attachment):
        self.db.add(attachment)
        return attachment

    def update(self, attachment: Attachment, data: dict):
        for key, value in data.items():
            setattr(attachment, key, value)

        return attachment

    def delete(self, attachment: Attachment):
        self.db.delete(attachment)

    def delete_by_entity(
        self,
        entity_type: str,
        entity_id: UUID,
    ):
        attachments = self.get_by_entity(entity_type, entity_id)

        for attachment in attachments:
            self.db.delete(attachment)

        return len(attachments)

    def commit(self):
        self.db.commit()

    def rollback(self):
        self.db.rollback()

    def refresh(self, attachment: Attachment):
        self.db.refresh(attachment)
