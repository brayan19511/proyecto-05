from sqlalchemy.orm import Session
from app.models.audit import AuditLog, AuditLogDetail, AuditStep


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
        steps_data
    ):

        log = self.db.query(AuditLog).filter(
            AuditLog.id == audit_id
        ).first()

        if not log:
            return

        for key, value in header_updates.items():
            setattr(log, key, value)

        detail = AuditLogDetail(
            log_id=audit_id,
            **detail_data
        )

        self.db.add(detail)

        for step in steps_data:
            self.db.add(
                AuditStep(
                    log_id=audit_id,
                    **step
                )
            )

        self.db.commit()

    def save_full_log(self, header_data: dict, detail_data: dict, steps_data: list):
        try:
            # 1. Crear Cabecera
            db_log = AuditLog(**header_data)
            self.db.add(db_log)
            self.db.flush()  # Genera el ID para las relaciones

            # 2. Crear Detalle
            db_detail = AuditLogDetail(log_id=db_log.id, **detail_data)
            self.db.add(db_detail)

            # 3. Crear Pasos Internos
            for step in steps_data:
                db_step = AuditStep(log_id=db_log.id, **step)
                self.db.add(db_step)

            self.db.commit()
        except Exception as e:
            self.db.rollback()
            print(f"Error guardando auditoría: {e}")  # O usa logger
