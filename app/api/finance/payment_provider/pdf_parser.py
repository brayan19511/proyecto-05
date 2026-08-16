import re
import unicodedata
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import UploadFile

from app.core.config import settings


def normalizar_para_busqueda(valor: str) -> str:
    sin_tildes = "".join(
        caracter
        for caracter in unicodedata.normalize("NFD", valor)
        if unicodedata.category(caracter) != "Mn"
    )
    return sin_tildes.upper()


def normalizar_texto(valor: str | None) -> str:
    if not valor:
        return ""
    return re.sub(r"\s+", " ", normalizar_para_busqueda(valor)).strip()


def clave_comparacion(valor: str | None) -> str:
    """Clave para comparar nombres de proveedor de forma tolerante.

    Ademas de quitar tildes/mayusculas/espacios (normalizar_texto), elimina la
    puntuacion (comas, puntos, etc.) para que "METEC CO., LIMITED" y
    "METEC CO. LIMITED" se consideren el mismo proveedor.
    """
    base = normalizar_texto(valor)
    base = re.sub(r"[^A-Z0-9 ]+", " ", base)
    return re.sub(r"\s+", " ", base).strip()


def clave_documento(valor: str | None) -> str:
    """Clave para comparar documentos (RUC/DNI): solo alfanumericos en mayuscula."""
    if not valor:
        return ""
    return re.sub(r"[^0-9A-Z]", "", valor.upper())


def obtener_valor(contenido: str, campo: str) -> str | None:
    contenido_busqueda = normalizar_para_busqueda(contenido)
    campo_busqueda = normalizar_para_busqueda(campo)
    coincidencia = re.search(
        rf"^\s*{re.escape(campo_busqueda)}:?[^\S\r\n]+(.+)$",
        contenido_busqueda,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    if not coincidencia:
        return None
    return contenido[coincidencia.start(1): coincidencia.end(1)].strip()


def normalizar_moneda(moneda: str) -> str:
    moneda_normalizada = moneda.strip().upper().replace(" ", "")
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
    }
    return monedas.get(moneda_normalizada, moneda_normalizada)


def extraer_monto(valor: str | None) -> dict[str, Any] | None:
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
        monto_decimal = Decimal(monto_texto.replace(",", ""))
    except InvalidOperation:
        return None

    return {
        "texto": valor.strip(),
        "moneda_original": moneda_original,
        "moneda": normalizar_moneda(moneda_original),
        "monto": monto_decimal,
    }


def extraer_importe_cargado(valor: str | None) -> dict[str, Any] | None:
    """Extrae montos con la moneda como palabra al final: "26,664.61 DOLARES"."""
    if not valor:
        return None

    coincidencia = re.match(
        r"^\s*(?P<monto>[\d.,]+)\s+(?P<moneda>[A-Za-z/.\$]+)\s*$",
        valor.strip(),
    )
    if not coincidencia:
        return None

    monto_texto = coincidencia.group("monto")
    moneda_original = coincidencia.group("moneda")
    try:
        monto_decimal = Decimal(monto_texto.replace(",", ""))
    except InvalidOperation:
        return None

    return {
        "texto": valor.strip(),
        "moneda_original": moneda_original,
        "moneda": normalizar_moneda(moneda_original),
        "monto": monto_decimal,
    }


class PaymentPdfParser:
    """Extrae datos relevantes desde constancias PDF de pago."""

    def parse(self, file: UploadFile) -> dict[str, Any]:
        resultado = {
            "archivo": file.filename,
            "procesado": False,
            "error": None,
        }
        try:
            self._validate_file(file)
            contenido = self._extract_pdf_text(file)
            datos_operacion = self._extract_operation_data(contenido)
            datos_destino = self._extract_payment_data(contenido)
            self._validate_extracted_data(datos_destino)
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
            try:
                file.file.seek(0)
            except Exception:
                pass
        return resultado

    @staticmethod
    def _validate_file(file: UploadFile) -> None:
        content_type = (file.content_type or "").lower()
        filename = (file.filename or "").lower()
        if content_type != "application/pdf" and not filename.endswith(".pdf"):
            raise ValueError("El archivo no es un PDF")

    def _extract_pdf_text(self, file: UploadFile) -> str:
        contenido = self._extract_pdf_text_with_pdfplumber(file)
        if self._has_enough_text(contenido):
            return contenido

        if settings.PAYMENT_PROVIDER_ENABLE_OCR:
            contenido_ocr = self._extract_pdf_text_with_ocr(file)
            if self._has_enough_text(contenido_ocr):
                return contenido_ocr

        raise ValueError(
            "No se pudo extraer texto del PDF. "
            "Es posible que sea un documento escaneado o ilegible."
        )

    @staticmethod
    def _extract_pdf_text_with_pdfplumber(file: UploadFile) -> str:
        try:
            import pdfplumber
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Falta instalar pdfplumber para leer archivos PDF"
            ) from exc

        paginas = []
        file.file.seek(0)
        with pdfplumber.open(file.file) as pdf:
            for pagina in pdf.pages:
                paginas.append(pagina.extract_text() or "")

        file.file.seek(0)
        return "\n".join(paginas).strip()

    @staticmethod
    def _extract_pdf_text_with_ocr(file: UploadFile) -> str:
        try:
            from pdf2image import convert_from_bytes
            import pytesseract
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Falta instalar pdf2image/pytesseract para aplicar OCR"
            ) from exc

        file.file.seek(0)
        contenido_pdf = file.file.read()
        file.file.seek(0)

        try:
            imagenes = convert_from_bytes(
                contenido_pdf,
                dpi=settings.PAYMENT_PROVIDER_OCR_DPI,
            )
        except Exception as exc:
            raise RuntimeError(
                "No se pudo convertir el PDF a imagen para OCR. "
                "Verifica que poppler-utils este instalado en Docker."
            ) from exc

        paginas = []
        for imagen in imagenes:
            paginas.append(
                pytesseract.image_to_string(
                    imagen,
                    lang=settings.PAYMENT_PROVIDER_OCR_LANG,
                )
            )
        return "\n".join(paginas).strip()

    @staticmethod
    def _has_enough_text(contenido: str | None) -> bool:
        return bool(
            contenido
            and len(contenido.strip()) >= settings.PAYMENT_PROVIDER_MIN_TEXT_LENGTH
        )

    @staticmethod
    def _extract_section(contenido: str, inicio: str, fin: str) -> str:
        contenido_busqueda = normalizar_para_busqueda(contenido)
        inicio_busqueda = normalizar_para_busqueda(inicio)
        fin_busqueda = normalizar_para_busqueda(fin)
        coincidencia = re.search(
            rf"{re.escape(inicio_busqueda)}(.*?)(?:{re.escape(fin_busqueda)}|$)",
            contenido_busqueda,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not coincidencia:
            return ""
        return contenido[coincidencia.start(1): coincidencia.end(1)].strip()

    def _extract_operation_data(self, contenido: str) -> dict[str, str | None]:
        seccion = self._extract_section(
            contenido=contenido,
            inicio="Datos de la operacion",
            fin="Datos de la cuenta de origen",
        )
        if not seccion:
            seccion = self._extract_section(
                contenido=contenido,
                inicio="Datos de la operacion",
                fin="Datos de procesos de la operacion",
            )
        if not seccion:
            seccion = self._extract_section(
                contenido=contenido,
                inicio="Datos de operacion",
                fin="Datos de orinen",
            )
        # Formato BBVA "Consulta de Operaciones": no tiene secciones, es una
        # lista plana de Etiqueta Valor.
        if not seccion and self._es_consulta_operaciones(contenido):
            return self._extract_consulta_operaciones_operation(contenido)
        column_values = self._extract_operation_column_values(seccion)
        return {
            "fecha_envio": (obtener_valor(seccion, "Fecha de envio") or obtener_valor(seccion, "Fecha de operacion")),
            "estado": obtener_valor(seccion, "Estado") or column_values.get("estado"),
            "tipo_operacion": (
                obtener_valor(seccion, "Tipo de operacion")
                or column_values.get("tipo_operacion")
            ),
            "fecha_proceso": (
                obtener_valor(seccion, "Fecha de proceso")
                or obtener_valor(seccion, "Fecha de operacion")
                or column_values.get("fecha_proceso")
            ),
            "numero_operacion": (
                obtener_valor(seccion, "Numero de operacion")
                or obtener_valor(seccion, "Número de operación")
                or column_values.get("numero_operacion")
            ),
        }

    @staticmethod
    def _extract_operation_column_values(seccion: str) -> dict[str, str | None]:
        lines = [line.strip() for line in seccion.splitlines() if line.strip()]
        normalized_lines = [normalizar_para_busqueda(line) for line in lines]
        label_indexes = [
            index
            for index, line in enumerate(normalized_lines)
            if line in {
                "TIPO DE OPERACION",
                "ESTADO",
                "NUMERO DE OPERACION",
                "FECHA DE PROCESO",
            }
        ]
        if not label_indexes:
            return {}

        values = lines[max(label_indexes) + 1:]
        if len(values) < 4:
            return {}

        return {
            "tipo_operacion": values[0],
            "estado": values[1].replace("•", "").replace("e ", "").strip(),
            "numero_operacion": values[2],
            "fecha_proceso": values[3],
        }

    def _extract_payment_data(self, contenido: str) -> dict[str, Any]:
        # Formato BBVA "Consulta de Operaciones" (lista plana Etiqueta Valor).
        consulta_data = self._extract_consulta_operaciones_data(contenido)
        if self._has_minimum_payment_data(consulta_data):
            return consulta_data

        destination_data = self._extract_destination_data(contenido)
        if self._has_minimum_payment_data(destination_data):
            return destination_data

        transfer_data = self._extract_transfer_data(contenido)
        if self._has_minimum_payment_data(transfer_data):
            return transfer_data

        service_payment_data = self._extract_service_payment_data(contenido)
        if self._has_minimum_payment_data(service_payment_data):
            return service_payment_data

        beneficiario_data = self._extract_beneficiario_data(contenido)
        if self._has_minimum_payment_data(beneficiario_data):
            return beneficiario_data

        banco_beneficiario_data = self._extract_banco_beneficiario_data(
            contenido)
        if self._has_minimum_payment_data(banco_beneficiario_data):
            return banco_beneficiario_data

        # Devolvemos el primer intento para que el error liste los campos
        # faltantes habituales de la constancia.
        return destination_data

    @staticmethod
    def _es_consulta_operaciones(contenido: str) -> bool:
        return "CONSULTA DE OPERACIONES" in normalizar_para_busqueda(contenido)

    def _extract_consulta_operaciones_data(self, contenido: str) -> dict[str, Any]:
        if not self._es_consulta_operaciones(contenido):
            return {}

        beneficiario = obtener_valor(
            contenido, "Cuenta / Tarjeta / Servicio Beneficiario"
        )
        cuenta, nombre = self._split_cuenta_beneficiario(beneficiario)
        ruc = self._extraer_documento(
            obtener_valor(contenido, "Doc. Identidad")
        )
        monto_original = obtener_valor(contenido, "Importe Cargado")
        monto_info = extraer_importe_cargado(monto_original)
        return {
            "monto_texto": monto_info["texto"] if monto_info else monto_original,
            "monto_decimal": monto_info["monto"] if monto_info else None,
            "moneda": monto_info["moneda"] if monto_info else None,
            "moneda_original": (
                monto_info["moneda_original"] if monto_info else None
            ),
            # Formato (3): trae nombre del beneficiario. Formato (4): solo RUC.
            "titular": nombre,
            "cuenta": cuenta,
            "tipo": obtener_valor(contenido, "Tipo de Operacion"),
            "referencia": obtener_valor(contenido, "Referencia"),
            "ruc": ruc,
            "source_section": "CONSULTA_OPERACIONES",
        }

    @staticmethod
    def _split_cuenta_beneficiario(valor: str | None) -> tuple[str | None, str | None]:
        """Separa "00110716810100023566 BUSINESS IT PERU SAC" en cuenta y nombre.

        En el formato (4) solo viene la cuenta, sin nombre.
        """
        if not valor:
            return None, None
        coincidencia = re.match(
            r"^\s*(?P<cuenta>\d+)\s*(?P<nombre>.*)$",
            valor.strip(),
        )
        if not coincidencia:
            texto = valor.strip()
            return None, (texto or None)
        cuenta = coincidencia.group("cuenta") or None
        nombre = coincidencia.group("nombre").strip() or None
        return cuenta, nombre

    @staticmethod
    def _extraer_documento(valor: str | None) -> str | None:
        """Extrae el numero de documento (RUC/DNI) de "R - 20609307235"."""
        if not valor:
            return None
        coincidencia = re.search(r"(\d{8,15})", valor)
        return coincidencia.group(1) if coincidencia else None

    def _extract_consulta_operaciones_operation(
        self, contenido: str
    ) -> dict[str, str | None]:
        fecha = self._normalizar_fecha(obtener_valor(contenido, "Fecha / Hora"))
        estado = (
            "Realizada"
            if "SU OPERACION HA SIDO REALIZADA"
            in normalizar_para_busqueda(contenido)
            else None
        )
        return {
            "fecha_envio": fecha,
            "estado": estado,
            "tipo_operacion": obtener_valor(contenido, "Tipo de Operacion"),
            "fecha_proceso": fecha,
            "numero_operacion": obtener_valor(contenido, "Numero de Operacion"),
        }

    @staticmethod
    def _normalizar_fecha(valor: str | None) -> str | None:
        """Convierte "2026-08-14 16:31:03" a "14/08/2026" (para el nombre)."""
        if not valor:
            return None
        coincidencia = re.search(r"(\d{4})[-/](\d{2})[-/](\d{2})", valor)
        if coincidencia:
            return (
                f"{coincidencia.group(3)}/"
                f"{coincidencia.group(2)}/"
                f"{coincidencia.group(1)}"
            )
        return valor

    def _extract_destination_data(self, contenido: str) -> dict[str, Any]:
        seccion = self._extract_section(
            contenido=contenido,
            inicio="Datos de la cuenta de destino",
            fin="Datos de envio de constancia",
        )
        monto_original = obtener_valor(seccion, "Monto")
        monto_info = extraer_monto(monto_original)
        return {
            "monto_texto": monto_info["texto"] if monto_info else monto_original,
            "monto_decimal": monto_info["monto"] if monto_info else None,
            "moneda": monto_info["moneda"] if monto_info else None,
            "moneda_original": (
                monto_info["moneda_original"] if monto_info else None
            ),
            "titular": obtener_valor(seccion, "Titular"),
            "cuenta": obtener_valor(seccion, "Cuenta"),
            "tipo": obtener_valor(seccion, "Tipo"),
            "referencia": obtener_valor(seccion, "Referencia"),
            "ruc": None,
            "source_section": "DESTINATION_ACCOUNT",
        }

    def _extract_transfer_data(self, contenido: str) -> dict[str, Any]:
        seccion = self._extract_section(
            contenido=contenido,
            inicio="Datos de la transferencia",
            fin="Datos de envio de constancia",
        )
        monto_original = (
            obtener_valor(seccion, "Monto total")
            or obtener_valor(seccion, "Monto")
            or obtener_valor(seccion, "Importe")
        )
        monto_info = extraer_monto(monto_original)
        return {
            "monto_texto": monto_info["texto"] if monto_info else monto_original,
            "monto_decimal": monto_info["monto"] if monto_info else None,
            "moneda": monto_info["moneda"] if monto_info else None,
            "moneda_original": (
                monto_info["moneda_original"] if monto_info else None
            ),
            "titular": (
                obtener_valor(seccion, "Titular")
                or obtener_valor(seccion, "Beneficiario")
                or obtener_valor(seccion, "Razon social")
                or obtener_valor(seccion, "Razon social beneficiario")
            ),
            "cuenta": (
                obtener_valor(seccion, "Cuenta")
                or obtener_valor(seccion, "Cuenta destino")
                or obtener_valor(seccion, "Cuenta beneficiario")
            ),
            "tipo": obtener_valor(seccion, "Tipo"),
            "referencia": (
                obtener_valor(seccion, "Referencia")
                or obtener_valor(seccion, "Nro. operacion")
                or obtener_valor(seccion, "Numero de operacion")
                or obtener_valor(seccion, "Operacion")
            ),
            "ruc": (
                obtener_valor(seccion, "RUC")
                or obtener_valor(seccion, "Ruc")
                or obtener_valor(seccion, "Documento")
            ),
            "source_section": "TRANSFER",
        }

    def _extract_service_payment_data(self, contenido: str) -> dict[str, Any]:
        seccion = self._extract_section(
            contenido=contenido,
            inicio="Datos del pago",
            fin="Datos de la cuenta de cargo",
        )
        monto_original = (
            obtener_valor(seccion, "Monto a pagar")
            or obtener_valor(seccion, "Monto pagado")
        )
        column_values = self._extract_service_payment_column_values(seccion)
        monto_info = extraer_monto(monto_original)
        if not monto_info:
            monto_original = column_values.get("monto")
            monto_info = extraer_monto(monto_original)
        empresa_proveedora = (
            obtener_valor(seccion, "Empresa proveedora")
            or obtener_valor(seccion, "EM. PROVEEDORA")
            or column_values.get("empresa_proveedora")
        )
        codigo_servicio = (
            obtener_valor(seccion, "Codigo de servicio")
            or obtener_valor(seccion, "Código de servicio")
            or obtener_valor(seccion, "Cod. servicio")
            or column_values.get("codigo_servicio")
        )
        servicio = (
            obtener_valor(seccion, "Servicio a pagar")
            or obtener_valor(seccion, "Servico a pagar")
            or column_values.get("servicio")
        )
        return {
            "monto_texto": monto_info["texto"] if monto_info else monto_original,
            "monto_decimal": monto_info["monto"] if monto_info else None,
            "moneda": monto_info["moneda"] if monto_info else None,
            "moneda_original": (
                monto_info["moneda_original"] if monto_info else None
            ),
            "titular": empresa_proveedora,
            "cuenta": codigo_servicio,
            "tipo": servicio or obtener_valor(seccion, "Tipo"),
            "referencia": (
                codigo_servicio
                or obtener_valor(seccion, "N° DOC. PAGO")
                or obtener_valor(seccion, "N DOC. PAGO")
            ),
            "ruc": None,
            "source_section": "SERVICE_PAYMENT",
        }

    def _extract_banco_beneficiario_data(self, contenido: str) -> dict[str, Any]:
        seccion = self._extract_section(
            contenido=contenido,
            inicio="Datos del banco beneficiario",
            fin="Datos de la cuenta de cargo",
        )
        monto_original = (
            obtener_valor(seccion, "Monto total")
            or obtener_valor(seccion, "Monto pagado")
        )
        column_values = self._extract_service_payment_column_values(seccion)
        monto_info = extraer_monto(monto_original)
        if not monto_info:
            monto_original = column_values.get("monto")
            monto_info = extraer_monto(monto_original)
        empresa_proveedora = (
            obtener_valor(seccion, "Nombre del beneficiario")
            or column_values.get("empresa_proveedora")
        )
        codigo_servicio = (
            obtener_valor(seccion, "Referencia")
            or obtener_valor(seccion, "Código de servicio")
            or obtener_valor(seccion, "Cod. servicio")
            or column_values.get("codigo_servicio")
        )
        servicio = (
            obtener_valor(seccion, "Servicio a pagar")
            or obtener_valor(seccion, "Servico a pagar")
            or column_values.get("servicio")
        )
        return {
            "monto_texto": monto_info["texto"] if monto_info else monto_original,
            "monto_decimal": monto_info["monto"] if monto_info else None,
            "moneda": monto_info["moneda"] if monto_info else None,
            "moneda_original": (
                monto_info["moneda_original"] if monto_info else None
            ),
            "titular": empresa_proveedora,
            "cuenta": codigo_servicio,
            "tipo": servicio or obtener_valor(seccion, "Tipo"),
            "referencia": (
                codigo_servicio
                or obtener_valor(seccion, "N° DOC. PAGO")
                or obtener_valor(seccion, "N DOC. PAGO")
            ),
            "ruc": None,
            "source_section": "SERVICE_PAYMENT",
        }

    def _extract_beneficiario_data(self, contenido: str) -> dict[str, Any]:
        seccion = self._extract_section(
            contenido=contenido,
            inicio="Datos del beneficiario",
            fin="Datos de la cuenta de cargo",
        )
        monto_original = (
            obtener_valor(seccion, "Monto")
            or obtener_valor(seccion, "Monto pagado")
        )
        column_values = self._extract_service_payment_column_values(seccion)
        monto_info = extraer_monto(monto_original)
        if not monto_info:
            monto_original = column_values.get("monto")
            monto_info = extraer_monto(monto_original)
        beneficiario = (
            obtener_valor(seccion, "Beneficiario")
            or obtener_valor(seccion, "EM. PROVEEDORA")
            or column_values.get("beneficiario")
        )
        codigo_servicio = (
            obtener_valor(seccion, "Codigo de servicio")
            or "Transferencia a cuentas de terceros BCP local"
        )
        servicio = (
            obtener_valor(seccion, "Servicio a pagar")
            or "Transferencia a cuentas de terceros BCP local"
        )
        return {
            "monto_texto": monto_info["texto"] if monto_info else monto_original,
            "monto_decimal": monto_info["monto"] if monto_info else None,
            "moneda": monto_info["moneda"] if monto_info else None,
            "moneda_original": (
                monto_info["moneda_original"] if monto_info else None
            ),
            "titular": beneficiario,
            "cuenta": codigo_servicio,
            "tipo": servicio or obtener_valor(seccion, "Tipo"),
            "referencia": (
                codigo_servicio
                or obtener_valor(seccion, "N° DOC. PAGO")
                or obtener_valor(seccion, "N DOC. PAGO")
            ),
            "ruc": None,
            "source_section": "SERVICE_PAYMENT",
        }

    @staticmethod
    def _extract_service_payment_column_values(seccion: str) -> dict[str, str | None]:
        """Lee constancias OCR donde etiquetas y valores salen en columnas.

        En algunos PDFs escaneados el OCR devuelve primero todas las etiquetas
        del bloque "Datos del pago" y luego sus valores. Este fallback toma los
        valores cercanos al codigo de servicio y al monto, sin afectar PDFs que
        ya vienen en texto normal.
        """

        lines = [line.strip() for line in seccion.splitlines() if line.strip()]
        normalized_lines = [normalizar_para_busqueda(line) for line in lines]
        label_indexes = [
            index
            for index, line in enumerate(normalized_lines)
            if line in {
                "BENEFICIARIO",
                "SERVICIO A PAGAR",
                "SERVICO A PAGAR",
                "TITULAR DEL SERVICIO",
                "CODIGO DE SERVICIO",
                "MONTO A PAGAR",
            }
        ]
        search_start = max(label_indexes) + 1 if label_indexes else 0

        amount_index = None
        amount_value = None
        for index in range(search_start, len(lines)):
            amount_info = extraer_monto(lines[index])
            if amount_info:
                amount_index = index
                amount_value = amount_info["texto"]
                break

        search_end = amount_index if amount_index is not None else len(lines)
        code_index = None
        code_value = None
        for index in range(search_end - 1, search_start - 1, -1):
            if re.search(r"\b\d{6,}[A-Z0-9]*\b", normalized_lines[index]):
                code_index = index
                code_value = lines[index]
                break

        if code_index is None:
            return {"empresa_proveedora": None, "servicio": None, "codigo_servicio": None, "monto": amount_value}

        candidate_lines = [
            line
            for line in lines[search_start:code_index]
            if not PaymentPdfParser._looks_like_noise_service_value(line)
        ]
        value_block = candidate_lines[-3:]

        return {
            "empresa_proveedora": value_block[0] if value_block else None,
            "servicio": value_block[1] if len(value_block) > 1 else None,
            "codigo_servicio": code_value,
            "monto": amount_value,
        }

    @staticmethod
    def _looks_like_noise_service_value(value: str) -> bool:
        normalized = normalizar_para_busqueda(value)
        if re.search(r"\d{1,2}/\d{1,2}/\d{2,4}", normalized):
            return True
        if re.fullmatch(r"\d+", normalized):
            return True
        return False

    @staticmethod
    def _has_minimum_payment_data(data: dict) -> bool:
        # El proveedor se identifica por nombre (titular) O por documento (ruc).
        return bool(
            (data.get("titular") or data.get("ruc"))
            and data.get("monto_texto")
            and data.get("monto_decimal") is not None
            and data.get("moneda")
        )

    @staticmethod
    def _validate_extracted_data(datos_destino: dict) -> None:
        campos_faltantes = []
        if not datos_destino.get("titular") and not datos_destino.get("ruc"):
            campos_faltantes.append("titular o documento")
        if not datos_destino.get("monto_texto"):
            campos_faltantes.append("monto")
        if datos_destino.get("monto_decimal") is None:
            campos_faltantes.append("monto valido")
        if not datos_destino.get("moneda"):
            campos_faltantes.append("moneda")

        if campos_faltantes:
            raise ValueError(
                "No se encontraron o no se pudieron interpretar los campos: "
                + ", ".join(campos_faltantes)
            )
