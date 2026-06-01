from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from app.models.finance.libro_mayor_model import LibroMayor, ReglasGastos

class LibroMayorRepository:
    def __init__(self, db_local: Session):
        self.db = db_local

    # --- SECCIÓN: REGLAS DE GASTOS ---
    def get_reglas_activas(self) -> List[ReglasGastos]:
        """Trae las reglas contables locales ordenadas estrictamente por prioridad."""
        return (
            self.db.query(ReglasGastos)
            .filter(ReglasGastos.activo == True)
            .order_by(ReglasGastos.prioridad.asc())
            .all()
        )

    # --- SECCIÓN: LIBRO MAYOR (INDIVIDUAL) ---
    def get_libro_mayor_by_id(self, transaccion_id: int, linea: int) -> LibroMayor:
        return self.db.query(LibroMayor).filter_by(transaccion_id=transaccion_id, linea=linea).first()  

    # --- SECCIÓN: ALTA EFICIENCIA (BULK UPSERT MASIVO) ---
    def upsert_libro_mayor_masivo(self, lista_registros: List[Dict[str, Any]]):
        """
        Toma una lista de diccionarios (ya procesados por el motor de reglas en Python)
        y ejecuta un UPSERT masivo nativo en PostgreSQL en un único viaje a la BD.
        Evita duplicados usando la llave compuesta (transaccion_id, linea).
        """
        if not lista_registros:
            return

        # Construimos el statement nativo de Postgres para "INSERT ... ON CONFLICT DO UPDATE"
        stmt = insert(LibroMayor).values(lista_registros)
        
        # Definimos qué columnas se van a pisar si el registro de SAP ya existía localmente
        update_dict = {
            col.name: stmt.excluded[col.name]
            for col in LibroMayor.__table__.columns
            if col.name not in ["transaccion_id", "linea"] # La PK no se actualiza
        }

        upsert_stmt = stmt.on_conflict_do_update(
            index_elements=["transaccion_id", "linea"],
            set_=update_dict
        )

        self.db.execute(upsert_stmt)
        self.db.commit()

    def get_all_libro_mayor(self) -> List[LibroMayor]:
        return self.db.query(LibroMayor).all()