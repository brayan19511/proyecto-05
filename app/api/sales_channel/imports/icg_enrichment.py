"""Enriquecimiento de SKUs con el nombre del articulo desde ICG.

El SKU de canal (Rappi/Peya) coincide con ARTICULOS.REFPROVEEDOR en ICG, y el
nombre a mostrar esta en ARTICULOS.DESCRIPCION. El catalogo de SKU vive en
Postgres/Ofisis, asi que no hay JOIN entre servidores: se consulta ICG por esos
REFPROVEEDOR y se une en memoria.

La base ICG se elige por pais del canal (Peru y Mexico estan en el mismo
servidor, distinta base). Quien construye el lookup ya recibe la sesion de la
base correcta; aca solo se consulta.
"""

import logging

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session


logger = logging.getLogger(__name__)

# SQL Server permite hasta 2100 parametros por consulta; se consulta en lotes.
CHUNK_SIZE = 900


class IcgDescriptionLookup:
    def __init__(self, db_icg: Session):
        self.db_icg = db_icg

    def descripciones_por_sku(self, skus: list[str]) -> dict[str, str]:
        """Devuelve {sku_normalizado: descripcion} para los SKUs encontrados.

        La clave se normaliza a mayusculas y sin espacios extremos, para que el
        llamador la busque igual (`sku.strip().upper()`). Ante cualquier fallo de
        ICG devuelve lo que haya alcanzado a resolver, sin romper el preview.
        """
        # Se envia el SKU sin espacios extremos; SQL Server compara sin distinguir
        # mayusculas ni espacios finales, asi que el IN usa el indice de REFPROVEEDOR.
        referencias = list({sku.strip() for sku in skus if sku and sku.strip()})
        resultado: dict[str, str] = {}

        for inicio in range(0, len(referencias), CHUNK_SIZE):
            lote = referencias[inicio : inicio + CHUNK_SIZE]
            try:
                filas = self._consultar_lote(lote)
            except Exception:
                logger.exception("Fallo al consultar descripciones en ICG")
                break

            for fila in filas:
                referencia = fila.get("ref")
                descripcion = fila.get("descripcion")
                if not referencia or not descripcion:
                    continue
                clave = str(referencia).strip().upper()
                # Primer match gana (REFPROVEEDOR puede repetirse entre articulos).
                resultado.setdefault(clave, str(descripcion).strip())

        return resultado

    def _consultar_lote(self, referencias: list[str]) -> list[dict]:
        consulta = text(
            """
            SELECT a.REFPROVEEDOR AS ref, a.DESCRIPCION AS descripcion
            FROM ARTICULOS a WITH (NOLOCK)
            WHERE a.REFPROVEEDOR IN :refs
            """
        ).bindparams(bindparam("refs", expanding=True))
        resultado = self.db_icg.execute(consulta, {"refs": referencias})
        return [
            {columna.lower(): valor for columna, valor in fila.items()}
            for fila in resultado.mappings()
        ]
