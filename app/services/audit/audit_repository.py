import logging

from sqlalchemy.orm import Session

from app.models.audit import AuditLog, AuditLogDetail, AuditStep


logger = logging.getLogger(__name__)


class AuditRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_log(self, data: dict):
        log = AuditLog(**data)
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log.id

    def finish_log(
        self,
        audit_id,
        header_updates,
        detail_data,
        steps_data,
    ):
        log = (
            self.db.query(AuditLog)
            .filter(AuditLog.id == audit_id)
            .first()
        )
        if not log:
            return

        for key, value in header_updates.items():
            setattr(log, key, value)

        self.db.add(AuditLogDetail(log_id=audit_id, **detail_data))
        self.db.add_all(
            AuditStep(log_id=audit_id, **step)
            for step in steps_data
        )
        self.db.commit()

    def save_full_log(
        self,
        header_data: dict,
        detail_data: dict,
        steps_data: list,
    ):
        try:
            db_log = AuditLog(**header_data)
            self.db.add(db_log)
            self.db.flush()

            self.db.add(AuditLogDetail(log_id=db_log.id, **detail_data))
            self.db.add_all(
                AuditStep(log_id=db_log.id, **step)
                for step in steps_data
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
            logger.exception("Error guardando auditoria")
