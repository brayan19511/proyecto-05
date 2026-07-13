import re
from decimal import Decimal, InvalidOperation
from typing import Any

import pdfplumber
from fastapi import APIRouter, File, HTTPException, UploadFile


router = APIRouter()


def obtener_valor(
    contenido: str,
    campo: str,
) -> str | None:
    """
    Obtiene el valor que se encuentra después de un campo.

    Ejemplo:
        Titular DARYZA S.A.C.

    Resultado:
        DARYZA S.A.C.
    """
    coincidencia = re.search(
        rf"^{re.escape(campo)}\s+(.+)$",
        contenido,
        flags=re.IGNORECASE | re.MULTILINE,
    )

    return coincidencia.group(1).strip() if coincidencia else None


def normalizar_texto(
    valor: str | None,
) -> str:
    """
    Normaliza textos para poder compararlos y agruparlos.

    Ejemplo:
        'Daryza S.A.C.'
        ' DARYZA S.A.C. '

    Ambos valores se convierten en:
        'DARYZA S.A.C.'
    """
    if not valor:
        return ""

    return re.sub(
        r"\s+",
        " ",
        valor,
    ).strip().upper()


def normalizar_moneda(
    moneda: str,
) -> str:
    """
    Convierte distintos símbolos o formatos a un código estándar.

    Ejemplos:
        S/       -> PEN
        S/.      -> PEN
        US$      -> USD
        USD      -> USD
        $        -> USD
    """
    moneda_normalizada = (
        moneda
        .strip()
        .upper()
        .replace(" ", "")
    )

    monedas = {
        "S/": "PEN",
        "S/.": "PEN",
        "PEN": "PEN",
        "SOLES": "PEN",
        "SOL": "PEN",
        "US$": "USD",
        "USD": "USD",
        "$": "USD",
        "DOLARES": "USD",
        "DÓLARES": "USD",
    }

    return monedas.get(
        moneda_normalizada,
        moneda_normalizada,
    )


def extraer_monto(
    valor: str | None,
) -> dict[str, Any] | None:
    """
    Extrae moneda y monto del texto original.

    Ejemplos soportados:
        S/ 4,372.79
        S/. 4,372.79
        US$ 1,200.50
        USD 1,200.50
        $ 500.00

    Resultado:
        {
            "texto": "S/ 4,372.79",
            "moneda_original": "S/",
            "moneda": "PEN",
            "monto": Decimal("4372.79")
        }
    """
    if not valor:
        return None

    coincidencia = re.match(
        r"^\s*"
        r"(?P<moneda>S\/\.?|US\$|USD|PEN|\$)"
        r"\s*"
        r"(?P<monto>[\d,]+(?:\.\d{1,2})?)"
        r"\s*$",
        valor,
        flags=re.IGNORECASE,
    )

    if not coincidencia:
        return None

    moneda_original = coincidencia.group("moneda")
    monto_texto = coincidencia.group("monto")

    try:
        monto_decimal = Decimal(
            monto_texto.replace(",", "")
        )
    except InvalidOperation:
        return None

    return {
        "texto": valor.strip(),
        "moneda_original": moneda_original,
        "moneda": normalizar_moneda(moneda_original),
        "monto": monto_decimal,
    }


class PaymentProviderService:
    def __init__(
        self,
        files: list[UploadFile],
    ):
        self.files = files

    def process(self) -> dict[str, Any]:
        """
        Procesa todos los archivos y agrupa los pagos por proveedor.
        """
        pagos_procesados = []
        errores = []

        for file in self.files:
            resultado = self._process_file(file)

            if resultado["procesado"]:
                pagos_procesados.append(resultado)
            else:
                errores.append(resultado)

        proveedores = self._group_by_provider(
            pagos_procesados
        )

        return {
            "total_archivos": len(self.files),
            "total_procesados": len(pagos_procesados),
            "total_errores": len(errores),
            "total_proveedores": len(proveedores),
            "proveedores": proveedores,
            "errores": errores,
        }

    def _process_file(
        self,
        file: UploadFile,
    ) -> dict[str, Any]:
        """
        Procesa un archivo PDF individual.
        """
        resultado = {
            "archivo": file.filename,
            "procesado": False,
            "error": None,
        }

        try:
            self._validate_file(file)

            contenido = self._extract_pdf_text(file)

            datos_operacion = (
                self._extract_operation_data(contenido)
            )

            datos_destino = (
                self._extract_destination_data(contenido)
            )

            self._validate_extracted_data(
                datos_operacion=datos_operacion,
                datos_destino=datos_destino,
            )

            resultado.update(
                {
                    "procesado": True,
                    "datos_operacion": datos_operacion,
                    "datos_destino": datos_destino,
                }
            )

        except Exception as exc:
            resultado["error"] = str(exc)

        finally:
            # Permite volver a leer o adjuntar el archivo
            # posteriormente en el correo.
            try:
                file.file.seek(0)
            except Exception:
                pass

        return resultado

    @staticmethod
    def _validate_file(
        file: UploadFile,
    ) -> None:
        """
        Valida que el archivo recibido sea PDF.
        """
        content_type = (
            file.content_type or ""
        ).lower()

        filename = (
            file.filename or ""
        ).lower()

        if (
            content_type != "application/pdf"
            and not filename.endswith(".pdf")
        ):
            raise ValueError(
                "El archivo no es un PDF."
            )

    @staticmethod
    def _extract_pdf_text(
        file: UploadFile,
    ) -> str:
        """
        Extrae el texto de todas las páginas del PDF.
        """
        paginas = []

        with pdfplumber.open(file.file) as pdf:
            for pagina in pdf.pages:
                texto_pagina = (
                    pagina.extract_text() or ""
                )

                paginas.append(texto_pagina)

        contenido = "\n".join(paginas).strip()

        if not contenido:
            raise ValueError(
                "No se pudo extraer texto del PDF. "
                "Es posible que sea un documento escaneado."
            )

        return contenido

    @staticmethod
    def _extract_section(
        contenido: str,
        inicio: str,
        fin: str,
    ) -> str:
        """
        Extrae el contenido comprendido entre dos títulos.
        """
        coincidencia = re.search(
            rf"{re.escape(inicio)}"
            rf"(.*?)"
            rf"(?:{re.escape(fin)}|$)",
            contenido,
            flags=re.IGNORECASE | re.DOTALL,
        )

        if not coincidencia:
            return ""

        return coincidencia.group(1).strip()

    def _extract_operation_data(
        self,
        contenido: str,
    ) -> dict[str, str | None]:
        """
        Extrae la información de la operación.
        """
        seccion = self._extract_section(
            contenido=contenido,
            inicio="Datos de la operación",
            fin="Datos de la cuenta de origen",
        )

        return {
            "fecha_envio": obtener_valor(
                seccion,
                "Fecha de envío",
            ),
            "estado": obtener_valor(
                seccion,
                "Estado",
            ),
            "fecha_proceso": obtener_valor(
                seccion,
                "Fecha de proceso",
            ),
        }

    def _extract_destination_data(
        self,
        contenido: str,
    ) -> dict[str, Any]:
        """
        Extrae los datos de la cuenta de destino,
        incluyendo monto y moneda.
        """
        seccion = self._extract_section(
            contenido=contenido,
            inicio="Datos de la cuenta de destino",
            fin="Datos de envío de constancia",
        )

        monto_original = obtener_valor(
            seccion,
            "Monto",
        )

        monto_info = extraer_monto(
            monto_original
        )

        return {
            "monto_texto": (
                monto_info["texto"]
                if monto_info
                else monto_original
            ),
            "monto_decimal": (
                monto_info["monto"]
                if monto_info
                else None
            ),
            "moneda": (
                monto_info["moneda"]
                if monto_info
                else None
            ),
            "moneda_original": (
                monto_info["moneda_original"]
                if monto_info
                else None
            ),
            "titular": obtener_valor(
                seccion,
                "Titular",
            ),
            "cuenta": obtener_valor(
                seccion,
                "Cuenta",
            ),
            "tipo": obtener_valor(
                seccion,
                "Tipo",
            ),
            "referencia": obtener_valor(
                seccion,
                "Referencia",
            ),
        }

    @staticmethod
    def _validate_extracted_data(
        datos_operacion: dict,
        datos_destino: dict,
    ) -> None:
        """
        Valida los campos mínimos necesarios para procesar el pago.
        """
        campos_faltantes = []

        if not datos_destino.get("titular"):
            campos_faltantes.append("titular")

        if not datos_destino.get("cuenta"):
            campos_faltantes.append("cuenta")

        if not datos_destino.get("monto_texto"):
            campos_faltantes.append("monto")

        if datos_destino.get("monto_decimal") is None:
            campos_faltantes.append(
                "monto válido"
            )

        if not datos_destino.get("moneda"):
            campos_faltantes.append("moneda")

        if campos_faltantes:
            raise ValueError(
                "No se encontraron o no se pudieron "
                "interpretar los siguientes campos: "
                + ", ".join(campos_faltantes)
            )

    @staticmethod
    def _group_by_provider(
        pagos: list[dict],
    ) -> list[dict]:
        """
        Agrupa los pagos por proveedor.

        Dentro de cada proveedor, los totales se separan
        por moneda para no sumar PEN y USD.
        """
        proveedores: dict[str, dict] = {}

        for pago in pagos:
            datos_destino = pago["datos_destino"]
            datos_operacion = pago["datos_operacion"]

            titular = datos_destino["titular"]
            cuenta = datos_destino["cuenta"]
            moneda = datos_destino["moneda"]
            monto = datos_destino["monto_decimal"]

            # Agrupamos por titular.
            # Si necesitas distinguir cuentas del mismo proveedor,
            # puedes usar titular + cuenta.
            proveedor_key = normalizar_texto(
                titular
            )

            if proveedor_key not in proveedores:
                proveedores[proveedor_key] = {
                    "proveedor": titular,
                    "cantidad_pagos": 0,
                    "archivos": [],
                    "totales": {},
                    "pagos": [],
                }

            proveedor = proveedores[proveedor_key]

            if moneda not in proveedor["totales"]:
                proveedor["totales"][moneda] = Decimal(
                    "0.00"
                )

            proveedor["totales"][moneda] += monto
            proveedor["cantidad_pagos"] += 1

            proveedor["archivos"].append(
                pago["archivo"]
            )

            proveedor["pagos"].append(
                {
                    "archivo": pago["archivo"],
                    "monto_texto": datos_destino[
                        "monto_texto"
                    ],
                    "monto_decimal": monto,
                    "moneda": moneda,
                    "moneda_original": datos_destino[
                        "moneda_original"
                    ],
                    "titular": titular,
                    "cuenta": cuenta,
                    "tipo": datos_destino["tipo"],
                    "referencia": datos_destino[
                        "referencia"
                    ],
                    "fecha_envio": datos_operacion[
                        "fecha_envio"
                    ],
                    "fecha_proceso": datos_operacion[
                        "fecha_proceso"
                    ],
                    "estado": datos_operacion[
                        "estado"
                    ],
                }
            )

        resultado = []

        for proveedor in proveedores.values():
            # Convertimos los totales Decimal a string
            # para que la respuesta sea serializable a JSON.
            totales_formateados = []

            for moneda, total in proveedor[
                "totales"
            ].items():
                totales_formateados.append(
                    {
                        "moneda": moneda,
                        "total": str(
                            total.quantize(
                                Decimal("0.01")
                            )
                        ),
                    }
                )

            proveedor["totales"] = (
                totales_formateados
            )

            for pago in proveedor["pagos"]:
                pago["monto_decimal"] = str(
                    pago["monto_decimal"].quantize(
                        Decimal("0.01")
                    )
                )

            resultado.append(proveedor)

        return resultado


