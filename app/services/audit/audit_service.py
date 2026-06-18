from app.core.db.db_postgres import SessionLocal # Importa tu generador de sesiones
from .audit_repository import AuditRepository

class AuditService:
    @staticmethod
    def save_audit(data: dict):
        """
        Este método es estático para que BackgroundTasks lo llame fácilmente
        sin instanciar el servicio previamente.
        """
        db = SessionLocal()
        try:
            repository = AuditRepository(db)
            repository.save_full_log(
                header_data=data["log_header"],
                detail_data=data["log_detail"],
                steps_data=data["steps"]
            )
        finally:
            db.close()
    @staticmethod
    def start_audit(data):

        db = SessionLocal()

        try:
            repository = AuditRepository(db)

            return repository.create_log(data)

        finally:
            db.close()
    @staticmethod
    def finish_audit(
        audit_id,
        header_updates,
        detail_data,
        steps_data
    ):

        db = SessionLocal()

        try:
            repository = AuditRepository(db)

            repository.finish_log(
                audit_id=audit_id,
                header_updates=header_updates,
                detail_data=detail_data,
                steps_data=steps_data
            )

        finally:
            db.close()