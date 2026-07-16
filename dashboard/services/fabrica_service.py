import numpy as np
import pandas as pd
from babel.numbers import format_currency

from dashboard.data.projetos_repository import ProjetosRepository

# Nomes dos meses em português para o eixo X do gráfico
_MESES_PT = {
    '01': 'janeiro', '02': 'fevereiro', '03': 'março', '04': 'abril',
    '05': 'maio', '06': 'junho', '07': 'julho', '08': 'agosto',
    '09': 'setembro', '10': 'outubro', '11': 'novembro', '12': 'dezembro',
}

_MESES_ABREV = {
    '01': 'jan', '02': 'fev', '03': 'mar', '04': 'abr',
    '05': 'mai', '06': 'jun', '07': 'jul', '08': 'ago',
    '09': 'set', '10': 'out', '11': 'nov', '12': 'dez',
}


class FabricaService:
    """Regras de negócio do dashboard de Produção - Fábrica (Faturamento vs. Vazão)."""

    def __init__(self) -> None:
        self._repository = ProjetosRepository()

    def carregar_dados(self) -> pd.DataFrame:
        return self._repository.fetch_all()

    def filtrar(self, data_inicio, data_fim,
                vendedor=None, liberador=None, loja=None, tipo_ambiente=None,
                criterio: str = 'chegoufabrica') -> pd.DataFrame:
        """
        Filtra projetos pelo intervalo de datas e pelos filtros opcionais de dimensão.

        criterio: coluna de data usada como referência do filtro temporal.
          - 'pronto'      → projetos com produção concluída no período (Vazão)
          - 'dataentrega' → projetos com entrega prevista no período (Faturamento)
        """
        df = self.carregar_dados().copy()
        df[criterio] = pd.to_datetime(df[criterio], errors='coerce')

        # MesAno é derivado do criterio escolhido para agrupar o gráfico corretamente
        df['MesAno'] = df[criterio].dt.strftime('%Y-%m')

        di = pd.to_datetime(data_inicio)
        df_ = pd.to_datetime(data_fim)
        df_filter = df[(df[criterio] >= di) & (df[criterio] <= df_)]

        if vendedor:
            df_filter = df_filter[df_filter['vendedor'] == vendedor]
        if liberador:
            df_filter = df_filter[df_filter['liberador'] == liberador]
        if loja:
            df_filter = df_filter[df_filter['loja'] == loja]
        if tipo_ambiente:
            df_filter = df_filter[df_filter['tipoambiente'] == tipo_ambiente]

        return df_filter

    @staticmethod
    def formatar_reais(valor: float) -> str:
        """Formata valor monetário como 'R$ X,XX Mi' ou 'R$ X,X K' para rótulos de gráfico."""
        if valor >= 1_000_000:
            return f"R$ {valor / 1_000_000:.2f} Mi".replace('.', ',')
        if valor >= 1_000:
            return f"R$ {valor / 1_000:.1f} K".replace('.', ',')
        return format_currency(valor, 'BRL', locale='pt_BR')

    @staticmethod
    def dias_uteis_medios(serie_ini: pd.Series, serie_fim: pd.Series) -> float:
        """Calcula a média de dias úteis (seg–sex) entre duas séries de datas."""
        start = pd.to_datetime(serie_ini, errors='coerce').dt.date
        end = pd.to_datetime(serie_fim, errors='coerce').dt.date
        valid = start.notna() & end.notna()
        if not valid.any():
            return 0.0
        days = np.busday_count(
            start[valid].values.astype('datetime64[D]'),
            end[valid].values.astype('datetime64[D]'),
        )
        positivos = days[days >= 0]
        return float(positivos.mean()) if len(positivos) > 0 else 0.0

    @staticmethod
    def nome_mes(mes_ano: str) -> str:
        """Converte 'YYYY-MM' para nome por extenso, ex: 'janeiro/2024'."""
        partes = str(mes_ano).split('-')
        if len(partes) == 2:
            return f"{_MESES_PT.get(partes[1], partes[1])}/{partes[0]}"
        return mes_ano

    @staticmethod
    def abreviacao_mes(mes_ano: str) -> str:
        """Converte 'YYYY-MM' para abreviação curta, ex: 'jan/2024'."""
        mes_ano = str(mes_ano)
        if '-' not in mes_ano:
            return mes_ano
        return f"{_MESES_ABREV.get(mes_ano[5:], mes_ano[5:])}/{mes_ano[:4]}"

    def dados_mensais(self, df_fat: pd.DataFrame, df_vaz: pd.DataFrame) -> pd.DataFrame:
        """
        Combina os dois datasets em uma visão mensal para o gráfico.
        df_fat agrupado por dataentrega → coluna Faturamento (barras).
        df_vaz agrupado por pronto      → coluna Vazao (linha).
        O join é outer para exibir todos os meses presentes em qualquer dataset.
        """
        if 'valornegociado' not in df_fat.columns:
            return pd.DataFrame()

        fat = (
            df_fat.groupby('MesAno')['valornegociado']
            .sum().reset_index()
            .rename(columns={'valornegociado': 'Faturamento'})
        )
        vaz = (
            df_vaz.groupby('MesAno')['valornegociado']
            .sum().reset_index()
            .rename(columns={'valornegociado': 'Vazao'})
        ) if 'valornegociado' in df_vaz.columns else pd.DataFrame(columns=['MesAno', 'Vazao'])

        monthly = fat.merge(vaz, on='MesAno', how='outer').fillna(0)
        monthly = monthly.sort_values('MesAno').reset_index(drop=True)
        monthly['MesNome'] = monthly['MesAno'].apply(self.nome_mes)
        monthly['MesLabel'] = monthly['MesAno'].apply(self.abreviacao_mes)
        monthly['label_fat'] = monthly['Faturamento'].apply(self.formatar_reais)
        monthly['label_vaz'] = monthly['Vazao'].apply(self.formatar_reais)

        return monthly
