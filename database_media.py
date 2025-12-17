from typing import Literal, Tuple, Dict
import pandas as pd
import streamlit as st
from supabase import create_client, Client
from dash_projetos import data_inicial, data_final
import logging

# -------------------------------------------------------------------
# LOGGING BÁSICO
# -------------------------------------------------------------------
logger = logging.getLogger(__name__)
if not logger.handlers:
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)


# -------------------------------------------------------------------
# SERVIÇO PRINCIPAL
# -------------------------------------------------------------------
class ProducaoService:
    def __init__(self):
        # Aqui você pode injetar configs depois, se quiser
        self.cli = self._create_supabase_client()

    # -------- SUPABASE --------
    def _create_supabase_client(self) -> Client:
        sb = st.secrets.get("supabase", {})
        url = sb.get("url")
        key = sb.get("key")

        if not url or not key:
            raise RuntimeError("Configure SUPABASE_URL e SUPABASE_KEY em st.secrets['supabase'].")

        logger.info("Conectando ao Supabase...")
        return create_client(url, key)

    def load_raw_data(self) -> pd.DataFrame:
        """Lê dados crus do Supabase e faz o JOIN."""
        cols_proj = [
            "ordemdecompra","cliente","contrato","datacontrato","dataassinatura",
            "chegoufabrica","dataentrega","iniciado","pronto","entrega",
            "valorbruto","valornegociado"
        ]
        cols_prod = [
            "ordemdecompra",
            "corteinicio","cortefim",
            "customizacaoinicio","customizacaofim",
            "coladeirainicio","coladeirafim",
            "usinageminicio","usinagemfim",
            "montageminicio","montagemfim",
            "paineisinicio","paineisfim",
            "embalageminicio","embalagemfim"
        ]

        logger.info("Buscando dados de tblProjetos e tblProducao...")
        df_proj = pd.DataFrame(
            self.cli.table("tblProjetos").select(",".join(cols_proj)).execute().data or []
        )
        df_prod = pd.DataFrame(
            self.cli.table("tblProducao").select(",".join(cols_prod)).execute().data or []
        )

        if df_proj.empty or df_prod.empty:
            logger.warning("Alguma das tabelas voltou vazia.")
            return pd.DataFrame(columns=cols_proj + cols_prod[1:])

        df = df_prod.merge(df_proj, on="ordemdecompra", how="inner")

        # Mantém compatibilidade com 'OrdemdeCompra' se o restante do código usar
        if "ordemdecompra" in df.columns and "OrdemdeCompra" not in df.columns:
            df["OrdemdeCompra"] = df["ordemdecompra"]

        logger.info(f"Total de registros após JOIN: {len(df)}")
        return df

    # -------- TRANSFORMAÇÕES --------
    def convert_datetime_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        cols_data = [
            'corteinicio','cortefim',
            'customizacaoinicio','customizacaofim',
            'coladeirainicio','coladeirafim',
            'usinageminicio','usinagemfim',
            'montageminicio','montagemfim',
            'paineisinicio','paineisfim',
            'embalageminicio','embalagemfim',
        ]
        for col in cols_data:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        return df

    def filtrar_periodo(self, df: pd.DataFrame, inicio: str, fim: str) -> pd.DataFrame:
        di = pd.to_datetime(inicio)
        df_ = pd.to_datetime(fim)
        mask = (
            (pd.to_datetime(df["corteinicio"]) >= di) &
            (pd.to_datetime(df["cortefim"])   <= df_)
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
        jornada_fim    = pd.Timestamp(1900, 1, 1, hour_final, min_final)

        def ajustar(data: pd.Timestamp):
            if pd.isnull(data): return None
            if data.weekday() >= 5: return None
            if data.time() < jornada_inicio.time():
                data = data.replace(hour=hour_inicio, minute=min_inicio)
            elif data.time() > jornada_fim.time():
                data = data.replace(hour=hour_final, minute=min_final)
            return data

        inicio = ajustar(inicio)
        fim    = ajustar(fim)
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
    def calcular_estatisticas(self, df: pd.DataFrame) :
        total_projetos = df["ordemdecompra"].nunique() if "ordemdecompra" in df.columns else len(df)

        def _safe_mean(series: pd.Series) -> float:
            return series.sum() / total_projetos if total_projetos else 0.0

        medias_dec = {
            "corte":        _safe_mean(df["DuraçãocorteHoras"]),
            "customizacao": _safe_mean(df["DuraçãocustomizacaoHoras"]),
            "coladeira":    _safe_mean(df["DuraçãocoladeiraHoras"]),
            "usinagem":     _safe_mean(df["DuraçãousinagemHoras"]),
            "montagem":     _safe_mean(df["DuraçãomontagemHoras"]),
            "paineis":      _safe_mean(df["DuraçãopaineisHoras"]),
            "embalagem":    _safe_mean(df["DuraçãoembalagemHoras"]),
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
    def run_pipeline(
        self,
        inicio: str,
        fim: str,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, Dict, Dict]:
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


def main():
    st.title("Dashboard de Produção")

    service = ProducaoService()

    # Exemplo usando as datas do módulo dash_projetos
    df, df_medias, medias_dec, medias_hhmm = service.run_pipeline(
        data_inicial, data_final
    )

    st.subheader("Dados filtrados")
    st.dataframe(df)

    st.subheader("Médias por etapa")
    st.dataframe(df_medias)

    st.write("Médias em decimal:", medias_dec)
    st.write("Médias em hh:mm:", medias_hhmm)


if __name__ == "__main__":
    main()
