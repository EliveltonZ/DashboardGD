import pandas as pd

from dashboard.data.projetos_repository import ProjetosRepository


class FinanceiroService:
    """Regras de negócio do dashboard Financeiro: carregamento e filtragem por período/dimensões."""

    def __init__(self) -> None:
        self._repository = ProjetosRepository()

    def carregar_dados(self) -> pd.DataFrame:
        return self._repository.fetch_all()

    def filtrar(self, df: pd.DataFrame, data_inicio, data_fim,
                vendedor=None, liberador=None, ambiente=None, loja=None) -> pd.DataFrame:
        coluna_data = 'pronto'

        df = df.copy()
        df[coluna_data] = pd.to_datetime(df[coluna_data], errors='coerce')
        df['MesAno'] = df[coluna_data].dt.strftime('%Y-%m')

        mask = (df[coluna_data] >= data_inicio) & (df[coluna_data] <= data_fim)
        df_filtrado = df[mask]

        filtros_campos = {
            'vendedor': vendedor,
            'liberador': liberador,
            'tipoambiente': ambiente,
            'loja': loja,
        }
        for campo, valor in filtros_campos.items():
            if valor is not None:
                df_filtrado = df_filtrado[df_filtrado[campo] == valor]

        return df_filtrado
