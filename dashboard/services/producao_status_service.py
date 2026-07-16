from datetime import datetime
from typing import Literal

import pandas as pd

from dashboard.core.time_generator import Generator
from dashboard.data.producao_repository import ProducaoSqlRepository

STATUS_CASE = """
CASE
  WHEN p."pendencia" = TRUE THEN 'PENDENCIA'
  WHEN p."entrega" IS NOT NULL THEN 'ENTREGUE'
  WHEN p."iniciado" IS NOT NULL AND p."urgente" = TRUE AND p."pronto" IS NOT NULL THEN 'PRONTO'
  WHEN p."iniciado" IS NOT NULL AND p."urgente" = TRUE THEN 'URGENTE'
  WHEN p."dataentrega"::date < :proj::date AND p."pronto" IS NOT NULL THEN 'PRONTO'
  WHEN p."dataentrega"::date < :proj::date THEN 'ATRASADO'
  WHEN (p."dataentrega"::date - INTERVAL '9 day') < :proj::date AND p."pronto" IS NOT NULL THEN 'PRONTO'
  WHEN (p."dataentrega"::date - INTERVAL '9 day') < :proj::date THEN 'A VENCER'
  WHEN p."pronto" IS NOT NULL THEN 'PRONTO'
  WHEN p."iniciado" IS NOT NULL THEN 'INICIADO'
  ELSE 'AGUARDANDO'
END
"""


class ProducaoStatusService:
    """Consultas SQL e transformações de dados do dashboard de Produção (status por etapa e previsões)."""

    STATUS_ABERTOS = ('INICIADO', 'ATRASADO', 'A VENCER', 'URGENTE', 'PENDENCIA')
    STATUS_COLUMNS = ['SCorte', 'SCustom', 'SColadeira', 'SPaineis', 'SUsinagem', 'SMontagem', 'SEmbalagem']
    COLUNAS_PREVISOES_DATA = [
        'corteinicio', 'cortefim', 'customizacaoinicio', 'customizacaofim',
        'coladeirainicio', 'coladeirafim', 'usinageminicio', 'usinagemfim',
        'montageminicio', 'montagemfim', 'paineisinicio', 'paineisfim',
        'embalageminicio', 'embalagemfim',
    ]
    COLUNAS_PREENCHIMENTO = [
        'corteinicio', 'customizacaoinicio', 'coladeirainicio', 'usinageminicio',
        'paineisinicio', 'montageminicio', 'embalageminicio',
    ]
    COL_ORDER_PREVISOES = [
        'codcc', 'cliente', 'ambiente', 'contrato', 'Status', 'Prazo',
        'corteinicio', 'cortefim', 'customizacaoinicio', 'customizacaofim',
        'coladeirainicio', 'coladeirafim', 'usinageminicio', 'usinagemfim',
        'montageminicio', 'montagemfim', 'paineisinicio', 'paineisfim',
        'embalageminicio', 'embalagemfim', 'urgente', 'dataentrega', 'previsao',
    ]

    def __init__(self) -> None:
        self._repository = ProducaoSqlRepository()

    @staticmethod
    def _etapa_case(prefixo: str) -> str:
        return f"""
        CASE
          WHEN pr."{prefixo}fim" IS NOT NULL THEN 'FINALIZADO'
          WHEN pr."{prefixo}inicio" IS NOT NULL THEN 'INICIADO'
          ELSE 'AGUARDE'
        END
        """

    @staticmethod
    def _iso(data) -> str:
        return getattr(data, "isoformat", lambda: str(data))()

    def carregar_status(self, projecao) -> pd.DataFrame:
        """Carrega os projetos com status de produção em aberto, na data de projeção informada."""
        query = f"""
        WITH dados AS (
          SELECT
            CASE WHEN EXISTS (
              SELECT 1 FROM "tblAcessorios" a
              WHERE a."ordemdecompra" = p."ordemdecompra"
            ) THEN '*' ELSE '' END AS "A",
            p."ordemdecompra",
            p."pedido",
            p."etapa",
            p."codcc",
            c."name" AS "cliente",
            p."contrato",
            p."ambiente",
            {STATUS_CASE} AS "Status",
            (p."dataentrega"::date - :proj::date) AS "Prazo",
            {self._etapa_case("corte")}           AS "SCorte",
            {self._etapa_case("customizacao")}    AS "SCustom",
            {self._etapa_case("coladeira")}       AS "SColadeira",
            {self._etapa_case("usinagem")}        AS "SUsinagem",
            {self._etapa_case("paineis")}         AS "SPaineis",
            {self._etapa_case("montagem")}        AS "SMontagem",
            {self._etapa_case("embalagem")}       AS "SEmbalagem",
            CASE
              WHEN pr."separacao" IS NOT NULL THEN 'FINALIZADO'
              WHEN pr."embalagemfim" IS NOT NULL THEN 'INICIADO'
              ELSE 'AGUARDE'
            END AS "SSeparacao",
            p."dataentrega",
            p."previsao",
            p."urgente",
            CASE WHEN p."pronto" IS NOT NULL THEN 'Certo' END AS "Teste",
            pr."observacoes"
          FROM "tblProjetos" p
          INNER JOIN "tblProducao" pr
            ON p."ordemdecompra" = pr."ordemdecompra"
          INNER JOIN "tblClientes" c
            ON p."id_cliente" = c."id"
          WHERE p."ordemdecompra" > 0
        )
        SELECT * FROM dados
        WHERE "Status" IN ('INICIADO','ATRASADO','A VENCER','URGENTE','PENDENCIA')
        ORDER BY "previsao", "urgente", "Prazo", "cliente", "codcc";
        """
        return self._repository.query(query, params={"proj": self._iso(projecao)})

    def carregar_previsoes(self, projecao) -> pd.DataFrame:
        """Carrega os dados brutos de etapas de produção para a aba de Previsões."""
        sql = f"""
        WITH dados AS (
          SELECT
            p."codcc",
            c."name" AS "cliente",
            p."contrato",
            p."ambiente",
            {STATUS_CASE} AS "Status",
            (p."dataentrega"::date - :proj::date) AS "Prazo",

            pr."corteinicio", pr."cortefim",
            pr."customizacaoinicio", pr."customizacaofim",
            pr."coladeirainicio", pr."coladeirafim",
            pr."usinageminicio", pr."usinagemfim",
            pr."paineisinicio", pr."paineisfim",
            pr."montageminicio", pr."montagemfim",
            pr."embalageminicio", pr."embalagemfim",

            p."dataentrega",
            p."previsao",
            p."urgente"
          FROM "tblProjetos" p
          INNER JOIN "tblProducao" pr
            ON p."ordemdecompra" = pr."ordemdecompra"
          INNER JOIN "tblClientes" c
            ON p."id_cliente" = c."id"
          WHERE p."ordemdecompra" > 0
        )
        SELECT * FROM dados
        WHERE "Status" IN ('INICIADO','ATRASADO','A VENCER','URGENTE','PENDENCIA')
        ORDER BY "previsao", "urgente", "Prazo", "cliente", "codcc";
        """
        return self._repository.query(sql, params={"proj": self._iso(projecao)})

    def montar_status_melted(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transforma as colunas de status por etapa em formato longo, para o gráfico de barras empilhado."""
        title_mapping = {col: col[1:] for col in self.STATUS_COLUMNS}
        melted_df = df.melt(
            id_vars=['ordemdecompra'],
            value_vars=title_mapping,
            var_name='Etapa',
            value_name='Status_Producao',
        )
        melted_df['Etapa_Titulo'] = melted_df['Etapa'].map(title_mapping)

        order_map = {col: i for i, col in enumerate(self.STATUS_COLUMNS)}
        melted_df["Etapa_Ordem"] = melted_df["Etapa"].map(order_map)
        return melted_df

    # -------- Formatação / preenchimento (aba Previsões) --------
    @staticmethod
    def _convert_to_str(df: pd.DataFrame, coluna: str) -> None:
        df[coluna] = df[coluna].astype(str).str.rstrip('0').str.rstrip('.')

    @staticmethod
    def _convert_to_date(df: pd.DataFrame, column: str) -> None:
        df[column] = pd.to_datetime(df[column], errors='coerce')

    @staticmethod
    def _format_date(df: pd.DataFrame, column: str) -> None:
        df[column] = df[column].dt.strftime("%d/%m/%Y %H:%M:%S")

    @staticmethod
    def _check_date(date_str) -> bool:
        date_parsed = datetime.strptime(date_str, "%d/%m/%Y %H:%M:%S")
        hoje = datetime.today().replace(microsecond=0)
        return date_parsed < hoje

    @classmethod
    def _cell_color(cls, val, lista: list) -> Literal['color: yellow', 'color: red', '']:
        if val in lista and cls._check_date(val):
            return 'color: red'
        elif val in lista:
            return 'color: yellow'
        return ''

    def preparar_previsoes(self, dfp: pd.DataFrame):
        """Formata datas/códigos e preenche horários ausentes com médias de duração por etapa."""
        dfp = dfp.copy()
        self._convert_to_str(dfp, 'codcc')
        self._convert_to_str(dfp, 'contrato')

        dfp['dataentrega'] = pd.to_datetime(dfp['dataentrega']).dt.strftime('%d/%m/%Y')
        dfp['previsao'] = pd.to_datetime(dfp['previsao']).dt.strftime('%d/%m/%Y')
        dfp['Prazo'] = dfp['Prazo'].astype(int)

        for col in self.COLUNAS_PREVISOES_DATA:
            self._convert_to_date(dfp, col)
            self._format_date(dfp, col)

        dfp = dfp[self.COL_ORDER_PREVISOES]
        return self._preencher_horarios_ausentes(dfp)

    def _preencher_horarios_ausentes(self, df_in: pd.DataFrame):
        """Preenche células vazias de etapas com a duração média, destacando o que foi estimado."""
        df_estilo = df_in.copy()
        estilo: list = []
        gerador = Generator(self.COLUNAS_PREENCHIMENTO)

        for index, row in df_in.iterrows():
            for col in df_in.columns[6:20]:
                if pd.isnull(row[col]):
                    data_hora = gerador.fill_mean_time(col)
                    df_estilo.at[index, col] = data_hora
                    estilo.append(data_hora)
                    gerador.last_date(data_hora)
                else:
                    gerador.last_date(str(row[col]))

        return df_estilo.style.map(lambda x: self._cell_color(x, estilo),
                                    subset=pd.IndexSlice[:, df_in.columns[6:20]])
