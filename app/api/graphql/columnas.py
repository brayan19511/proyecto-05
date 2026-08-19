"""Catalogo de columnas de las tablas de ICG.

Este archivo resuelve el problema de "como expongo las 100+ columnas de una
tabla sin escribirlas dos veces". Cada tabla tiene un catalogo con dos niveles:

NIVEL 1 - `base`
    Las columnas que alimentan los campos con nombre y tipo del type. Este
    tuple ES el SELECT del repositorio, asi que agregar una columna al SELECT
    es agregar una palabra aqui.

NIVEL 2 - `todas`
    El catalogo completo de la tabla. El cliente puede pedir cualquiera de
    estas por el argumento `columnas` y la recibe dentro del campo JSON
    `camposExtra`, sin tocar codigo.

Por que existe el catalogo y no un SELECT *: los nombres que llegan del cliente
se validan contra esta lista blanca antes de entrar al SQL. Nunca se concatena
al SQL un texto que venga de afuera.

Cuando una columna de camposExtra se vuelve importante (se usa seguido, se
quiere tipada y con autocompletado), se "promueve" al nivel 1: se agrega al
tuple `base` y se le hace su campo en el type.

PARA AGREGAR UNA TABLA NUEVA: se declaran sus dos tuplas de columnas y se crea
su `CatalogoColumnas` al final del archivo. Nada mas.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogoColumnas:
    """Las columnas de una tabla de ICG, en sus dos niveles."""

    tabla: str
    base: tuple[str, ...]
    todas: frozenset[str]

    def disponibles(self) -> list[str]:
        """Columnas que se pueden pedir por el argumento `columnas`.

        Excluye las del nivel 1: esas ya tienen su campo propio y tipado.
        """
        return sorted(self.todas - set(self.base))

    def validar(self, nombres: list[str]) -> list[str]:
        """Valida los nombres contra la lista blanca y los normaliza.

        Devuelve los nombres en mayuscula, sin repetidos y sin los que ya
        vienen en `base`. Levanta ValueError si alguno no existe en la tabla:
        es lo que impide que un nombre inventado llegue al SQL.
        """
        normalizadas: list[str] = []
        desconocidas: list[str] = []

        for nombre in nombres:
            limpio = nombre.strip().upper()
            if limpio in self.todas:
                if limpio not in self.base and limpio not in normalizadas:
                    normalizadas.append(limpio)
            else:
                desconocidas.append(nombre)

        if desconocidas:
            raise ValueError(
                f"Columnas desconocidas en {self.tabla}: "
                + ", ".join(sorted(desconocidas))
            )

        return normalizadas


# =========================================================================
# ALBVENTACAB - NIVEL 1: columnas con campo propio en DocumentoVenta
# =========================================================================
COLUMNAS_BASE: tuple[str, ...] = (
    # Identificacion del documento
    "NUMSERIE",
    "NUMALBARAN",
    "N",
    "TIPODOC",
    "IDESTADO",
    "SUALBARAN",
    # Facturacion
    "FACTURADO",
    "NUMSERIEFAC",
    "NUMFAC",
    "NFAC",
    "TIPODOCFAC",
    "TIQUET",
    "ESDEVOLUCION",
    "REGIMFACT",
    "CORREUNICO",
    # Fechas
    "FECHA",
    "HORA",
    "FECHACREACION",
    "FECHAMODIFICADO",
    # Cliente, vendedor, tienda
    "CODCLIENTE",
    "CODVENDEDOR",
    "CAJA",
    "SERIE",
    "Z",
    # Importes
    "TOTALBRUTO",
    "TOTALIMPUESTOS",
    "TOTALNETO",
    "TOTALCOSTE",
    "DTOCOMERCIAL",
    "TOTDTOCOMERCIAL",
    "TOTALCARGOSDTOS",
    # Moneda y tarifa
    "CODMONEDA",
    "FACTORMONEDA",
    "IVAINCLUIDO",
    "CODTARIFA",
    # Enlace contable
    "TRASPASADO",
    "FECHATRASPASO",
    "ENLACE_EMPRESA",
    "ENLACE_EJERCICIO",
    "ENLACE_ASIENTO",
    "ENLACE_USUARIO",
)


# =========================================================================
# ALBVENTACAB - NIVEL 2: catalogo completo de la tabla
# =========================================================================
COLUMNAS_ALBVENTACAB: frozenset[str] = frozenset(
    {
        "NUMSERIE",
        "NUMALBARAN",
        "N",
        "FACTURADO",
        "NUMSERIEFAC",
        "NUMFAC",
        "NFAC",
        "TIQUET",
        "ESUNPRESTAMO",
        "ESDEVOLUCION",
        "CODCLIENTE",
        "CODVENDEDOR",
        "FECHA",
        "HORA",
        "ENVIOPOR",
        "PORTESPAG",
        "DTOCOMERCIAL",
        "TOTDTOCOMERCIAL",
        "DTOPP",
        "TOTDTOPP",
        "TOTALBRUTO",
        "TOTALIMPUESTOS",
        "TOTALNETO",
        "TOTALCOSTE",
        "SELECCIONADO",
        "SUALBARAN",
        "CODMONEDA",
        "FACTORMONEDA",
        "IVAINCLUIDO",
        "CODTARIFA",
        "VIENEDEFO",
        "FECHAENTRADA",
        "PORC",
        "TOTPORC",
        "TIPODOC",
        "TIPODOCFAC",
        "SALA",
        "MESA",
        "HORAFIN",
        "NUMCOMENSALES",
        "IMPRESIONES",
        "FO",
        "SERIE",
        "Z",
        "IDESTADO",
        "FECHAMODIFICADO",
        "AUTOMATICO",
        "CAJA",
        "TOTALCOSTEIVA",
        "ESBARRA",
        "NBULTOS",
        "TRANSPORTE",
        "CODENVIO",
        "PUNTOSACUM",
        "IDTARJETA",
        "TOTALCARGOSDTOS",
        "SERIEASUNTO",
        "NUMEROASUNTO",
        "NUMROLLO",
        "NORECIBIDO",
        "PUNTOSCANJEADOS",
        "TOTALPUNTOS",
        "ENTRANSITO",
        "TRASPASADO",
        "ENLACE_EMPRESA",
        "ENLACE_EJERCICIO",
        "ENLACE_ASIENTO",
        "ENLACE_USUARIO",
        "FECHATRASPASO",
        "TOTALCOSTE2",
        "TOTALCOSTEIVA2",
        "FECHARECEPCION",
        "DESCARGAR",
        "FECHACREACION",
        "IDMOTIVODTO",
        "NUMIMPRESIONES",
        "HORATOTAL",
        "HORACOCINA",
        "FECHAINI",
        "FECHAFIN",
        "ESTADODELIVERY",
        "HORAELABORADO",
        "HORAASIGNADO",
        "HORAENTREGADO",
        "PUNTOSCANJEOPORDTOCOM",
        "DTOCOMANTESCANJEOPUNTOS",
        "NUMEROSERIAL",
        "MMFIJADO",
        "MODIFIEDTOTALES",
        "DTOANTESPROMOCIONAENA",
        "CARGOSERVART",
        "DTOSERVART",
        "IMPORTECARGOSERVART",
        "IMPORTEDTOSERVART",
        "CARGOANTESSERVART",
        "IDMOTIVODTOANTESSERVART",
        "IDHOTEL",
        "CORREUNICO",
        "CODCLIENTEPENDIENTE",
        "REGIMFACT",
        "ABONOCORREUNICO",
        "NUMSERVICIO",
        "FECHAPORTALREST",
        "MOTIVODTOOBSERVACIONES",
        "CODVENDEDORXML",
        "IDMOTIVOABONO",
    }
)


# =========================================================================
# ALBVENTALIN - NIVEL 1: columnas con campo propio en LineaVenta
# =========================================================================
COLUMNAS_LINEA_BASE: tuple[str, ...] = (
    # Identificacion de la linea
    "NUMSERIE",
    "NUMALBARAN",
    "N",
    "NUMLIN",
    "TIPO",
    "HORA",
    "LINEAOCULTA",
    # Articulo (la linea guarda su propia copia de referencia y descripcion,
    # asi que para el nombre del producto no hace falta unir con ARTICULOS)
    "CODARTICULO",
    "REFERENCIA",
    "DESCRIPCION",
    "COLOR",
    "TALLA",
    # Unidades
    "UNIDADESTOTAL",
    "UNIDADESPAGADAS",
    "UDSABONADAS",
    "STOCK",
    # Precios y descuento
    "PRECIO",
    "PRECIOIVA",
    "PRECIODEFECTO",
    "DTO",
    "TOTAL",
    # Costos
    "COSTE",
    "COSTEIVA",
    # Impuestos
    "TIPOIMPUESTO",
    "IVA",
    "PORCRETENCION",
    "TIPORETENCION",
    # Contexto comercial
    "CODALMACEN",
    "CODTARIFA",
    "CODVENDEDOR",
    "COMISION",
    "PRESTAMO",
    "SUPEDIDO",
    # Promocion
    "IDPROMOCION",
    "IMPORTEANTESPROMOCION",
    "IMPORTEPROMOCION",
    # Documento de origen (notas de credito)
    "ABONODE_NUMSERIE",
    "ABONODE_NUMALBARAN",
    "ABONODE_N",
    "ABONODE_NUMLIN",
    # Fechas
    "FECHAENTREGA",
    "FECHACADUCIDAD",
)


# =========================================================================
# ALBVENTALIN - NIVEL 2: catalogo completo de la tabla
# =========================================================================
COLUMNAS_ALBVENTALIN: frozenset[str] = frozenset(
    {
        "NUMSERIE",
        "NUMALBARAN",
        "N",
        "NUMLIN",
        "CODARTICULO",
        "REFERENCIA",
        "DESCRIPCION",
        "COLOR",
        "TALLA",
        "UNID1",
        "UNID2",
        "UNID3",
        "UNID4",
        "UNIDADESTOTAL",
        "UNIDADESPAGADAS",
        "PRECIO",
        "DTO",
        "TOTAL",
        "COSTE",
        "PRECIODEFECTO",
        "TIPOIMPUESTO",
        "IVA",
        "REQ",
        "CODTARIFA",
        "CODALMACEN",
        "LINEAOCULTA",
        "NUMKG",
        "PRESTAMO",
        "CODVENDEDOR",
        "SUPEDIDO",
        "CONTACTO",
        "PRECIOIVA",
        "CODFORMATO",
        "CODMACRO",
        "UDSEXPANSION",
        "EXPANDIDA",
        "TOTALEXPANSION",
        "COSTEIVA",
        "TIPO",
        "FECHAENTREGA",
        "COMISION",
        "NUMKGEXPANSION",
        "CARGO1",
        "CARGO2",
        "HORA",
        "UDSABONADAS",
        "ABONODE_NUMSERIE",
        "ABONODE_NUMALBARAN",
        "ABONODE_N",
        "FECHACADUCIDAD",
        "UDMEDIDA2",
        "UDMEDIDA2EXPANSION",
        "IDPROMOCION",
        "IMPORTEANTESPROMOCION",
        "IMPORTEANTESPROMOCIONIVA",
        "IMPORTEPROMOCION",
        "IMPORTEPROMOCIONIVA",
        "PORCRETENCION",
        "DTOANTESPROMOCION",
        "STOCK",
        "COSTE2",
        "COSTEIVA2",
        "IDMOTIVODTO",
        "DETALLEMODIF",
        "DETALLEDENUMLINEA",
        "TIPODELIVERY",
        "FAMILIAAENA",
        "TIPORETENCION",
        "ABONODELINEA",
        "HORACOCINA",
        "IDMOTIVOABONO",
        "ISPRECIO2",
        "TARIFAANTESPROMOCION",
        "MMPEDIDO",
        "IMPORTETESORERIAMIXMATCH",
        "OMNICHANNEL",
        "PUNTOSMIXMATCH",
        "ABONODE_PUNTOSMIXMATCH",
        "DTOANTESPROMOCIONAENA",
        "IMPORTEANTESPROMOCIONAENA",
        "IMPORTEIVAANTESPROMOCIONAENA",
        "ABONODE_DOCUMENTOEXTERNO",
        "ABONODE_NUMLIN",
        "ABONODE_CLAVEPRIVADA",
        "ABONODE_FECHA",
        "CARGO3",
        "CARGO4",
        "CARGO5",
        "CARGO6",
        "TIPORETENCIONICA",
        "PORCRETENCIONICA",
        "IMPORTEMASCARGOS",
        "IMPORTEIVAMASCARGOS",
        "TFSERIE",
        "TFNUMERO",
        "TFN",
        "MOTIVODTOOBSERVACIONES",
        "IMPUESTOCOMPRA",
        "IVACOMPRA",
        "REQCOMPRA",
    }
)


# =========================================================================
# CATALOGOS
# =========================================================================
CABECERA = CatalogoColumnas(
    tabla="ALBVENTACAB",
    base=COLUMNAS_BASE,
    todas=COLUMNAS_ALBVENTACAB,
)

LINEA = CatalogoColumnas(
    tabla="ALBVENTALIN",
    base=COLUMNAS_LINEA_BASE,
    todas=COLUMNAS_ALBVENTALIN,
)
