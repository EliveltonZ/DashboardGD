import pandas as pd

from dashboard.data.projetos_repository import ProjetosRepository


class ProjetosService:
    """Regras de negócio do dashboard de Projetos: carregamento e filtragem por período/dimensões."""

    def __init__(self) -> None:
        self._repository = ProjetosRepository()

    def carregar_dados(self) -> pd.DataFrame:
        return self._repository.fetch_all()

    def filtrar(self, df: pd.DataFrame, data_inicio, data_fim,
                vendedor=None, liberador=None, ambiente=None, loja=None) -> pd.DataFrame:
        criterio = 'pronto'
        df = df.copy()
        df[criterio] = pd.to_datetime(df[criterio], errors='coerce')
        di = pd.to_datetime(data_inicio)
        df_ = pd.to_datetime(data_fim)

        df['MesAno'] = df[criterio].dt.strftime('%Y-%m')
        df_filtrado = df[(df[criterio] >= di) & (df[criterio] <= df_)]

        if vendedor is not None:
            df_filtrado = df_filtrado[df_filtrado['vendedor'] == vendedor]
        if liberador is not None:
            df_filtrado = df_filtrado[df_filtrado['liberador'] == liberador]
        if ambiente is not None:
            df_filtrado = df_filtrado[df_filtrado['tipoambiente'] == ambiente]
        if loja is not None:
            df_filtrado = df_filtrado[df_filtrado['loja'] == loja]
        return df_filtrado
