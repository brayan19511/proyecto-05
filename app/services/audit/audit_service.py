from app.core.db_postgres import SessionLocal # Importa tu generador de sesiones
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