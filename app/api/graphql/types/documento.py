"""Tipos GraphQL del documento de venta de ICG.

El grafo que modela este archivo (equivale a la consulta con 14 JOIN):

    DocumentoVenta            ALBVENTACAB
    |- tipoDoc                LEFT JOIN TIPOSDOC
    |- tesoreria []           INNER JOIN TESORERIA
    |- camposLibres           LEFT JOIN ALBVENTACAMPOSLIBRES
    |- camposLibresFactura    LEFT JOIN FACTURASVENTACAMPOSLIBRES
    |- lineas []              INNER JOIN ALBVENTALIN
       |- articulo            INNER JOIN ARTICULOS
          |- marca / seccion / familia / subfamilia   (ver articulo.py)

Ver articulo.py para la explicacion del patron (@strawberry.type,
@strawberry.field, desde_fila, strawberry.Private).
"""

from datetime import date, datetime
from typing import Any

import strawberry
from strawberry.scalars import JSON

from app.api.graphql.converters import (
    a_booleano,
    a_entero,
    a_fecha,
    a_fecha_hora,
    a_float,
    a_hora,
    a_json,
    a_texto,
)
from app.api.graphql.repository import Fila
from app.api.graphql.types.articulo import Articulo


@strawberry.type(description="Tipo de documento (tabla TIPOSDOC)")
class TipoDoc:
    tipodoc: int
    descripcion: str | None

    @classmethod
    def desde_fila(cls, fila: Fila) -> "TipoDoc":
        return cls(
            tipodoc=int(fila["tipodoc"]),
            descripcion=a_texto(fila.get("descripcion")),
        )


@strawberry.type(description="Cuota de cobro del documento (tabla TESORERIA)")
class Tesoreria:
    codformapago: str | None
    importe: float

    @classmethod
    def desde_fila(cls, fila: Fila) -> "Tesoreria":
        return cls(
            codformapago=a_texto(fila.get("codformapago")),
            importe=a_float(fila.get("importe")),
        )


@strawberry.type(description="Campos libres del albaran (ALBVENTACAMPOSLIBRES)")
class CamposLibresAlbaran:
    pedido_vtex: str | None

    @classmethod
    def desde_fila(cls, fila: Fila) -> "CamposLibresAlbaran":
        return cls(pedido_vtex=a_texto(fila.get("pedidovtex")))


@strawberry.type(
    description="Campos libres de la factura (FACTURASVENTACAMPOSLIBRES)"
)
class CamposLibresFactura:
    tipo_facturacion: str | None
    tipo_nc: str | None
    nro_pedido: str | None
    canal_venta: str | None

    @classmethod
    def desde_fila(cls, fila: Fila) -> "CamposLibresFactura":
        return cls(
            tipo_facturacion=a_texto(fila.get("tipofact")),
            tipo_nc=a_texto(fila.get("tipo_nc")),
            nro_pedido=a_texto(fila.get("nro_pedido")),
            canal_venta=a_texto(fila.get("canal_venta")),
        )


# ICG guarda un punto en COLOR y TALLA cuando el articulo no tiene ese atributo.
ATRIBUTOS_VACIOS = (".",)


@strawberry.type(description="Linea de venta (tabla ALBVENTALIN)")
class LineaVenta:
    # --- Identificacion ---
    numlin: int
    n: str | None
    tipo: str | None
    hora: str | None
    linea_oculta: bool

    # --- Articulo ---
    # La linea guarda su propia copia de la referencia y la descripcion, asi
    # que para mostrar el nombre del producto NO hace falta pedir `articulo`
    # (que si dispara la consulta a ARTICULOS).
    codarticulo: str | None
    referencia: str | None
    descripcion: str | None
    color: str | None
    talla: str | None

    # --- Unidades ---
    unidades: float
    unidades_pagadas: float
    unidades_abonadas: float
    stock: float

    # --- Precios y descuento ---
    precio: float
    precio_con_igv: float
    precio_defecto: float
    dto: float
    total: float

    # --- Costos ---
    coste: float
    coste_con_igv: float

    # --- Impuestos ---
    tipo_impuesto: str | None
    iva: float
    porc_retencion: float
    tipo_retencion: str | None

    # --- Contexto comercial ---
    tienda: str | None
    codtarifa: str | None
    codvendedor: str | None
    comision: float
    prestamo: bool
    su_pedido: str | None

    # --- Promocion ---
    idpromocion: int | None
    importe_antes_promocion: float
    importe_promocion: float

    # --- Documento de origen (notas de credito) ---
    documento_origen_serie: str | None
    documento_origen_numero: int | None
    documento_origen_n: str | None
    documento_origen_linea: int | None

    # --- Fechas ---
    fecha_entrega: date | None
    fecha_caducidad: date | None

    # Columnas pedidas con el argumento `columnasLinea`, ya listas para JSON.
    extras: strawberry.Private[dict]

    @classmethod
    def desde_fila(
        cls,
        fila: Fila,
        *,
        columnas_extra: list[str] | None = None,
    ) -> "LineaVenta":
        return cls(
            numlin=int(fila.get("numlin") or 0),
            n=a_texto(fila.get("n")),
            tipo=a_texto(fila.get("tipo")),
            hora=a_hora(fila.get("hora")),
            linea_oculta=a_booleano(fila.get("lineaoculta")),
            codarticulo=a_texto(fila.get("codarticulo")),
            referencia=a_texto(fila.get("referencia")),
            descripcion=a_texto(fila.get("descripcion")),
            color=a_texto(fila.get("color"), vacios=ATRIBUTOS_VACIOS),
            talla=a_texto(fila.get("talla"), vacios=ATRIBUTOS_VACIOS),
            unidades=a_float(fila.get("unidadestotal")),
            unidades_pagadas=a_float(fila.get("unidadespagadas")),
            unidades_abonadas=a_float(fila.get("udsabonadas")),
            stock=a_float(fila.get("stock")),
            precio=a_float(fila.get("precio")),
            precio_con_igv=a_float(fila.get("precioiva")),
            precio_defecto=a_float(fila.get("preciodefecto")),
            dto=a_float(fila.get("dto")),
            total=a_float(fila.get("total")),
            coste=a_float(fila.get("coste")),
            coste_con_igv=a_float(fila.get("costeiva")),
            tipo_impuesto=a_texto(fila.get("tipoimpuesto")),
            iva=a_float(fila.get("iva")),
            porc_retencion=a_float(fila.get("porcretencion")),
            tipo_retencion=a_texto(fila.get("tiporetencion")),
            tienda=a_texto(fila.get("codalmacen")),
            codtarifa=a_texto(fila.get("codtarifa")),
            codvendedor=a_texto(fila.get("codvendedor")),
            comision=a_float(fila.get("comision")),
            prestamo=a_booleano(fila.get("prestamo")),
            su_pedido=a_texto(fila.get("supedido")),
            idpromocion=a_entero(fila.get("idpromocion")),
            importe_antes_promocion=a_float(fila.get("importeantespromocion")),
            importe_promocion=a_float(fila.get("importepromocion")),
            documento_origen_serie=a_texto(fila.get("abonode_numserie")),
            documento_origen_numero=a_entero(fila.get("abonode_numalbaran")),
            documento_origen_n=a_texto(fila.get("abonode_n")),
            documento_origen_linea=a_entero(fila.get("abonode_numlin")),
            fecha_entrega=a_fecha(fila.get("fechaentrega")),
            fecha_caducidad=a_fecha(fila.get("fechacaducidad")),
            extras={
                columna: a_json(fila.get(columna.lower()))
                for columna in (columnas_extra or [])
            },
        )

    @strawberry.field(
        description=(
            "Columnas de ALBVENTALIN pedidas con el argumento `columnasLinea` "
            "de documentosVenta, como objeto JSON."
        )
    )
    def campos_extra(self) -> JSON:
        return self.extras

    @strawberry.field(
        description=(
            "INNER JOIN ARTICULOS. Solo hace falta para los maestros "
            "(marca, seccion, familia): la descripcion y la referencia ya "
            "vienen en la propia linea."
        )
    )
    async def articulo(self, info: strawberry.Info) -> Articulo | None:
        if not self.codarticulo:
            return None

        fila = await info.context["loaders"].articulo.load(self.codarticulo)
        return Articulo.desde_fila(fila) if fila else None


@strawberry.type(description="Cabecera del documento de venta (ALBVENTACAB)")
class DocumentoVenta:
    # --- Identificacion ---
    numserie: str
    numalbaran: int
    # N es un caracter en ICG ('B'), no un numero. Lo mismo NFAC.
    n: str | None
    tipodoc: int
    idestado: str | None
    su_albaran: str | None

    # --- Facturacion ---
    facturado: bool
    numserie_fac: str | None
    numfac: str | None
    nfac: str | None
    tipodoc_fac: int | None
    tiquet: bool
    es_devolucion: bool
    regimen_facturacion: str | None
    correlativo_unico: str | None

    # --- Fechas ---
    fecha: date
    hora: str | None
    fecha_creacion: datetime | None
    fecha_modificado: datetime | None

    # --- Cliente, vendedor, caja ---
    codcliente: str | None
    codvendedor: str | None
    caja: str | None
    serie_caja: str | None
    z: str | None

    # --- Importes ---
    total_bruto: float
    total_impuestos: float
    total_neto: float
    total_coste: float
    dto_comercial: float
    total_dto_comercial: float
    total_cargos_dtos: float

    # --- Moneda y tarifa ---
    codmoneda: str | None
    factor_moneda: float
    iva_incluido: bool
    codtarifa: str | None

    # --- Enlace contable ---
    traspasado: bool
    fecha_traspaso: date | None
    enlace_empresa: str | None
    enlace_ejercicio: str | None
    enlace_asiento: str | None
    enlace_usuario: str | None

    # Valor original de NUMFAC, necesario como clave para unir con TESORERIA y
    # FACTURASVENTACAMPOSLIBRES. No aparece en el schema (ver Private).
    numfac_valor: strawberry.Private[Any]
    # Columnas pedidas por el argumento `columnas`, ya convertidas a JSON.
    extras: strawberry.Private[dict]

    @classmethod
    def desde_fila(
        cls,
        fila: Fila,
        *,
        columnas_extra: list[str] | None = None,
    ) -> "DocumentoVenta":
        return cls(
            numserie=a_texto(fila.get("numserie")) or "",
            numalbaran=int(fila.get("numalbaran") or 0),
            n=a_texto(fila.get("n")),
            tipodoc=int(fila.get("tipodoc") or 0),
            idestado=a_texto(fila.get("idestado")),
            su_albaran=a_texto(fila.get("sualbaran")),
            facturado=a_booleano(fila.get("facturado")),
            numserie_fac=a_texto(fila.get("numseriefac")),
            numfac=a_texto(fila.get("numfac")),
            nfac=a_texto(fila.get("nfac")),
            tipodoc_fac=(
                int(fila["tipodocfac"])
                if fila.get("tipodocfac") is not None
                else None
            ),
            tiquet=a_booleano(fila.get("tiquet")),
            es_devolucion=a_booleano(fila.get("esdevolucion")),
            regimen_facturacion=a_texto(fila.get("regimfact")),
            correlativo_unico=a_texto(fila.get("correunico")),
            fecha=fila["fecha"],
            hora=a_hora(fila.get("hora")),
            fecha_creacion=a_fecha_hora(fila.get("fechacreacion")),
            fecha_modificado=a_fecha_hora(fila.get("fechamodificado")),
            codcliente=a_texto(fila.get("codcliente")),
            codvendedor=a_texto(fila.get("codvendedor")),
            caja=a_texto(fila.get("caja")),
            serie_caja=a_texto(fila.get("serie")),
            z=a_texto(fila.get("z")),
            total_bruto=a_float(fila.get("totalbruto")),
            total_impuestos=a_float(fila.get("totalimpuestos")),
            total_neto=a_float(fila.get("totalneto")),
            total_coste=a_float(fila.get("totalcoste")),
            dto_comercial=a_float(fila.get("dtocomercial")),
            total_dto_comercial=a_float(fila.get("totdtocomercial")),
            total_cargos_dtos=a_float(fila.get("totalcargosdtos")),
            codmoneda=a_texto(fila.get("codmoneda")),
            factor_moneda=a_float(fila.get("factormoneda")),
            iva_incluido=a_booleano(fila.get("ivaincluido")),
            codtarifa=a_texto(fila.get("codtarifa")),
            traspasado=a_booleano(fila.get("traspasado")),
            fecha_traspaso=a_fecha(fila.get("fechatraspaso")),
            enlace_empresa=a_texto(fila.get("enlace_empresa")),
            enlace_ejercicio=a_texto(fila.get("enlace_ejercicio")),
            enlace_asiento=a_texto(fila.get("enlace_asiento")),
            enlace_usuario=a_texto(fila.get("enlace_usuario")),
            numfac_valor=fila.get("numfac"),
            extras={
                columna: a_json(fila.get(columna.lower()))
                for columna in (columnas_extra or [])
            },
        )

    @strawberry.field(
        description=(
            "Columnas de ALBVENTACAB pedidas con el argumento `columnas`, "
            "como objeto JSON. Sirve para las columnas que no tienen campo "
            "propio todavia. Vacio si no se pidio ninguna."
        )
    )
    def campos_extra(self) -> JSON:
        return self.extras

    @property
    def _clave_albaran(self) -> tuple[str, int]:
        return (self.numserie, self.numalbaran)

    @property
    def _clave_factura(self) -> tuple[str, Any]:
        return (self.numserie, self.numfac_valor)

    # -----------------------------------------------------------------
    # RELACIONES
    # -----------------------------------------------------------------
    @strawberry.field(description="INNER JOIN ALBVENTALIN")
    async def lineas(self, info: strawberry.Info) -> list[LineaVenta]:
        filas = await info.context["loaders"].lineas.load(self._clave_albaran)
        columnas = info.context.get("columnas_linea") or []
        return [
            LineaVenta.desde_fila(fila, columnas_extra=columnas)
            for fila in filas
        ]

    @strawberry.field(description="INNER JOIN TESORERIA por SERIE / NUMFAC")
    async def tesoreria(self, info: strawberry.Info) -> list[Tesoreria]:
        if self.numfac_valor is None:
            return []

        filas = await info.context["loaders"].tesoreria.load(self._clave_factura)
        return [Tesoreria.desde_fila(fila) for fila in filas]

    @strawberry.field(description="LEFT JOIN TIPOSDOC")
    async def tipo_doc(self, info: strawberry.Info) -> TipoDoc | None:
        fila = await info.context["loaders"].tipo_doc.load(self.tipodoc)
        return TipoDoc.desde_fila(fila) if fila else None

    @strawberry.field(description="LEFT JOIN ALBVENTACAMPOSLIBRES")
    async def campos_libres(
        self,
        info: strawberry.Info,
    ) -> CamposLibresAlbaran | None:
        loader = info.context["loaders"].campos_libres_albaran
        fila = await loader.load(self._clave_albaran)
        return CamposLibresAlbaran.desde_fila(fila) if fila else None

    @strawberry.field(description="LEFT JOIN FACTURASVENTACAMPOSLIBRES")
    async def campos_libres_factura(
        self,
        info: strawberry.Info,
    ) -> CamposLibresFactura | None:
        if self.numfac_valor is None:
            return None

        loader = info.context["loaders"].campos_libres_factura
        fila = await loader.load(self._clave_factura)
        return CamposLibresFactura.desde_fila(fila) if fila else None
