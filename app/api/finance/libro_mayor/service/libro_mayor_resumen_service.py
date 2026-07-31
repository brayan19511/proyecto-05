# app\api\libro_mayor\service\libro_mayor_resumen_service.py

from app.api.finance.libro_mayor.repository.libro_mayor_repository import LibroMayorRepository


class LibroMayorResumenService:

    def __init__(
        self,
        db_local,
    ):
        self.repository = LibroMayorRepository(db_local)

    def get_resumen(
        self,
        start_date,
        end_date,
        account,
    ):

        rows = self.repository.get_resumen(
            start_date=start_date,
            end_date=end_date,
            account=account,
        )

        return [
            {
                "anio": int(row.anio),
                "mes": int(row.mes),
                "codigo": row.codigo,
                "subcodigo": row.subcodigo,
                "nombre_cuenta": row.nombre_cuenta,
                "proveedor": row.proveedor,
                "cantidad_registros": row.cantidad_registros,
                "importe_soles": float(row.importe_soles or 0),
                "importe_dolares": float(row.importe_dolares or 0),
            }
            for row in rows
        ]

    def get_detalle(
        self, start_date, end_date, account, codigo, subcodigo, proveedor, anio, mes
    ):

        return self.repository.get_resumen_detalle(
            start_date=start_date,
            end_date=end_date,
            account=account,
            codigo=codigo,
            subcodigo=subcodigo,
            proveedor=proveedor, anio=anio, mes= mes
        )
