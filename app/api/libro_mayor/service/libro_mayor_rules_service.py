# app/api/libro_mayor/rules_engine.py
import pandas as pd
from datetime import datetime
from app.models.finance.libro_mayor_model import ReglasGastos


class LibroMayorRulesService:

    def aplicar(
        self,
        df: pd.DataFrame,
        reglas: list[ReglasGastos],
        user_id: str | None = None,
    ) -> pd.DataFrame:

        if df.empty:
            return df
        self._inicializar_columnas(df, user_id)
        for regla in reglas:
            self._aplicar_regla(df, regla)

        return df

    def _inicializar_columnas(self, df: pd.DataFrame, user_id: str | None):

        df["id_regla"] = None
        df["tiene_regla"] = False

        df["codigo"] = "SIN_CLASIFICAR"
        df["subcodigo"] = "OTROS"

        df["nombre_cuenta"] = df["nombre_cuenta_asociada"]

        # derivado de cuenta_asociada
        df["tipo_cuenta"] = df["cuenta_asociada"].astype(str).str[:2]

        df["created_by"] = user_id
        df["updated_by"] = user_id


    def _aplicar_regla(self, df: pd.DataFrame, regla: ReglasGastos):

        mask = self._build_mask(df, regla)

        mask &= df["id_regla"].isna()

        if not mask.any():
            return

        df.loc[mask, "id_regla"] = regla.id_regla
        df.loc[mask, "tiene_regla"] = True

        df.loc[mask, "codigo"] = regla.codigo
        df.loc[mask, "subcodigo"] = regla.subcodigo
        df.loc[mask, "nombre_cuenta"] = regla.nombre_cuenta

    def _build_mask(self, df: pd.DataFrame, regla: ReglasGastos):

        mask = pd.Series(True, index=df.index)

        if regla.cuenta:
            mask &= df["cuenta_asociada"] == regla.cuenta

        if regla.cuenta_contrapartida:
            mask &= df["cuenta_contrapartida"] == regla.cuenta_contrapartida

        if regla.centro_costo:
            mask &= df["centro_costo"] == regla.centro_costo

        if regla.filtro_texto:

            texto = regla.filtro_texto.lower()

            mask &= (
                df["descripcion"]
                .fillna("")
                .str.lower()
                .str.contains(texto, regex=False)
            )

        if regla.texto_excluido:

            texto = regla.texto_excluido.lower()

            mask &= ~(
                df["descripcion"]
                .fillna("")
                .str.lower()
                .str.contains(texto, regex=False)
            )

        if regla.monto_min is not None:
            mask &= df["cargo_abono_ml"] >= regla.monto_min

        if regla.monto_max is not None:
            mask &= df["cargo_abono_ml"] <= regla.monto_max

        return mask
