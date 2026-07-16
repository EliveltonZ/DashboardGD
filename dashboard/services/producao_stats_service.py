import logging
from typing import Dict, Literal, Tuple

import pandas as pd

from dashboard.data.producao_repository import ProducaoJoinRepository

logger = logging.getLogger(__name__)
if not logger.handlers:
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class ProducaoStatsService:
    """Calcula durações de etapas de produção e estatísticas agregadas por período (aba Estatística)."""

    COLUNAS_DATA = [
        'corteinicio', 'cortefim',
        'customizacaoinicio', 'customizacaofim',
        'coladeirainicio', 'coladeirafim',
        'usinageminicio', 'usinagemfim',
        'montageminicio', 'montagemfim',
        'paineisinicio', 'paineisfim',
        'embalageminicio', 'embalagemfim',
    ]

    def __init__(self) -> None:
        self._repository = ProducaoJoinRepository()

    # -------- CARGA / TRANSFORMAÇÕES --------
    def load_raw_data(self) -> pd.DataFrame:
        logger.info("Buscando dados de tblProjetos e tblProducao...")
        df = self._repository.fetch_joined()
        logger.info(f"Total de registros após JOIN: {len(df)}")
        return df

    def convert_datetime_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        for col in self.COLUNAS_DATA:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        return df

    def filtrar_periodo(self, df: pd.DataFrame, inicio: str, fim: str) -> pd.DataFrame:
        di = pd.to_datetime(inicio)
        df_ = pd.to_datetime(fim)
        mask = (
            (pd.to_datetime(df["corteinicio"]) >= di) &
            (pd.to_datetime(df["cortefim"]) <= df_)
        )
        df_filtrado = df[mask].copy()
        logger.info(f"Registros após filtro de período: {len(df_filtrado)}")
        return df_filtrado

    # -------- CÁLCULO DE DURAÇÃO --------
    @staticmethod
    def calcular_duracao_trabalhada(inicio, fim) -> float | Literal[0]:
        hour_inicio = 7
        min_inicio = 30
        hour_final = 16
        min_final = 30

        jornada_inicio = pd.Timestamp(1900, 1, 1, hour_inicio, min_inicio)
        jornada_fim = pd.Timestamp(1900, 1, 1, hour_final, min_final)

        def ajustar(data: pd.Timestamp):
            if pd.isnull(data):
                return None
            if data.weekday() >= 5:
                return None
            if data.time() < jornada_inicio.time():
                data = data.replace(hour=hour_inicio, minute=min_inicio)
            elif data.time() > jornada_fim.time():
                data = data.replace(hour=hour_final, minute=min_final)
            return data

        inicio = ajustar(inicio)
        fim = ajustar(fim)
        if not inicio or not fim:
            return 0

        horas = 0
        while inicio < fim:
            if inicio.weekday() < 5:
                fim_dia = inicio.replace(hour=hour_final, minute=min_final)
                horas += (min(fim, fim_dia) - inicio).total_seconds() / 3600
            inicio = (inicio + pd.DateOffset(days=1)).replace(
                hour=hour_inicio, minute=min_inicio
            )
        return horas

    @staticmethod
    def decimal_to_hours(decimal_hours):
        if pd.isna(decimal_hours):
            return None
        hours = int(decimal_hours)
        minutes = int((decimal_hours - hours) * 60)
        return f"{hours:02d}:{minutes:02d}"

    def calcular_duracoes(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Calculando duração trabalhada por etapa...")
        df["DuraçãocorteHoras"] = df.apply(
            lambda r: self.calcular_duracao_trabalhada(r.corteinicio, r.cortefim), axis=1
        )
        df["DuraçãocustomizacaoHoras"] = df.apply(
            lambda r: self.calcular_duracao_trabalhada(r.customizacaoinicio, r.customizacaofim), axis=1
        )
        df["DuraçãocoladeiraHoras"] = df.apply(
            lambda r: self.calcular_duracao_trabalhada(r.coladeirainicio, r.coladeirafim), axis=1
        )
        df["DuraçãousinagemHoras"] = df.apply(
            lambda r: self.calcular_duracao_trabalhada(r.usinageminicio, r.usinagemfim), axis=1
        )
        df["DuraçãomontagemHoras"] = df.apply(
            lambda r: self.calcular_duracao_trabalhada(r.montageminicio, r.montagemfim), axis=1
        )
        df["DuraçãopaineisHoras"] = df.apply(
            lambda r: self.calcular_duracao_trabalhada(r.paineisinicio, r.paineisfim), axis=1
        )
        df["DuraçãoembalagemHoras"] = df.apply(
            lambda r: self.calcular_duracao_trabalhada(r.embalageminicio, r.embalagemfim), axis=1
        )
        return df

    # -------- ESTATÍSTICAS --------
    def calcular_estatisticas(self, df: pd.DataFrame):
        total_projetos = df["ordemdecompra"].nunique() if "ordemdecompra" in df.columns else len(df)

        def _safe_mean(series: pd.Series) -> float:
            return series.sum() / total_projetos if total_projetos else 0.0

        medias_dec = {
            "corte": _safe_mean(df["DuraçãocorteHoras"]),
            "customizacao": _safe_mean(df["DuraçãocustomizacaoHoras"]),
            "coladeira": _safe_mean(df["DuraçãocoladeiraHoras"]),
            "usinagem": _safe_mean(df["DuraçãousinagemHoras"]),
            "montagem": _safe_mean(df["DuraçãomontagemHoras"]),
            "paineis": _safe_mean(df["DuraçãopaineisHoras"]),
            "embalagem": _safe_mean(df["DuraçãoembalagemHoras"]),
        }

        medias_hhmm = {k: self.decimal_to_hours(v) for k, v in medias_dec.items()}

        df_medias = pd.DataFrame(
            {"Etapa": list(medias_dec.keys()),
             "HorasDecimal": list(medias_dec.values())}
        )
        df_medias["Percentual"] = (
            df_medias["HorasDecimal"] / df_medias["HorasDecimal"].sum() * 100
        ).round(1)
        df_medias["%"] = df_medias["Percentual"].astype(str) + "%"
        df_medias["Media"] = df_medias["HorasDecimal"].apply(self.decimal_to_hours)

        logger.info("Estatísticas calculadas com sucesso.")
        return df_medias, medias_dec, medias_hhmm

    # -------- PIPELINE COMPLETO --------
    def run_pipeline(self, inicio: str, fim: str) -> Tuple[pd.DataFrame, pd.DataFrame, Dict, Dict]:
        """
        Executa o fluxo completo com dados SEMPRE atualizados:
        - lê Supabase
        - converte datas
        - filtra período
        - calcula durações
        - calcula estatísticas
        """
        df_raw = self.load_raw_data()
        df_raw = self.convert_datetime_columns(df_raw)
        df_filtrado = self.filtrar_periodo(df_raw, inicio, fim)
        df_filtrado = self.calcular_duracoes(df_filtrado)
        df_medias, medias_dec, medias_hhmm = self.calcular_estatisticas(df_filtrado)
        return df_filtrado, df_medias, medias_dec, medias_hhmm


if __name__ == "__main__":
    print(ProducaoStatsService.calcular_duracao_trabalhada('2026-01-01T07:30', '2026-01-01T07:31'))
