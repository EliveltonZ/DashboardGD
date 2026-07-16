import pandas as pd
import streamlit as st

from dashboard.core.charts import Chart
from dashboard.core.settings import Settings
from dashboard.core.theme import detect_theme_mode
from dashboard.services.projetos_service import ProjetosService


class ProjetosPage:
    """Dashboard de Projetos: filtros de sidebar + gráficos por ambiente, vendedor, liberador, loja e período."""

    def __init__(self) -> None:
        self._service = ProjetosService()

    def render_sidebar(self, data_inicial, data_final, cor_ambiente, cor_vendedor, cor_liberador, cor_periodo):
        df = self._service.carregar_dados()

        with st.sidebar:
            with st.form("my_form"):
                s1, s2, s3, s4 = st.columns(4)
                with s1:
                    color1 = st.color_picker("Amb", cor_ambiente, help='Seleciona cor (Ambiente)')
                with s2:
                    color2 = st.color_picker("Vnd", cor_vendedor, help='Seleciona cor (Vendedor)')
                with s3:
                    color3 = st.color_picker("Lib", cor_liberador, help='Seleciona cor (Liberador)')
                with s4:
                    color4 = st.color_picker("Prd", cor_periodo, help='Seleciona cor (Periodo)')

                c1, c2 = st.columns(2)
                with c1:
                    data_inicio = str(st.date_input('Data de Início', value=pd.to_datetime(data_inicial), format='DD/MM/YYYY'))
                with c2:
                    data_fim = str(st.date_input('Data de Fim', value=pd.to_datetime(data_final), format='DD/MM/YYYY'))

                data_set = self._service.filtrar(df, data_inicio, data_fim)

                vendedores = sorted(pd.Series(data_set['vendedor']).dropna().unique())
                liberadores = sorted(pd.Series(data_set['liberador']).dropna().unique())
                ambientes = sorted(pd.Series(data_set['tipoambiente']).dropna().unique())
                lojas = sorted(pd.Series(data_set['loja']).dropna().unique())

                f_vendedor = st.selectbox('Vendedores', options=vendedores, placeholder='Selecione um Vendedor', index=None)
                f_liberador = st.selectbox('Liberadores', options=liberadores, placeholder='Selecione um Liberador', index=None)
                f_ambiente = st.selectbox('Ambiente', options=ambientes, placeholder='Selecione um Ambiente', index=None)
                f_loja = st.selectbox('Loja', options=lojas, index=None, placeholder='Selcione uma Loja')

                t1, t2, t3 = st.columns(3)
                with t3:
                    if st.form_submit_button('Salvar'):
                        Settings().save_filtros(data_inicio, data_fim, color1, color2, color3, color4)
                with t2:
                    ...
                with t1:
                    st.form_submit_button('Filtrar')
                    return (data_inicio, data_fim, f_vendedor, f_liberador, f_ambiente, f_loja,
                            color1, color2, color3, color4)

    def render(self, data_inicio, data_fim, f_vendedor, f_liberador, f_ambiente, f_loja,
               color1, color2, color3, color4) -> None:
        df = self._service.carregar_dados()
        try:
            data_set = self._service.filtrar(df, data_inicio, data_fim, f_vendedor, f_liberador, f_ambiente, f_loja)
            if data_set.empty:
                raise IndexError

            theme_mode = detect_theme_mode()
            col1, col2, col3, col4_ = st.columns(4)
            col5, col6 = st.columns(2)
            col7, col8, col9 = st.columns(3)

            linha_y = 'ordemdecompra'

            with col5:
                linha_x = 'tipoambiente'
                grafico = Chart(data_set)
                grafico.bar(linha_x, linha_y, 'count', color1, 'Ambientes', label_theme=theme_mode)
                ambiente_max = grafico.metric(linha_x, linha_y)

            with col6:
                linha_x = 'vendedor'
                grafico = Chart(data_set)
                grafico.bar(linha_x, linha_y, 'count', color2, linha_x.capitalize(), line_mean=True, label_theme=theme_mode)
                max_vendas = grafico.metric(linha_x, linha_y)

            with col7:
                linha_x = 'liberador'
                grafico = Chart(data_set)
                grafico.bar(linha_x, linha_y, 'count', color3, linha_x.capitalize(), line_mean=True, label_theme=theme_mode)
                max_liberador = grafico.metric(linha_x, linha_y)

            with col8:
                linha_x = 'loja'
                grafico = Chart(data_set)
                grafico.circle(linha_x, linha_y, 'count', 80, 140, 15,
                               ['#29b09d', '#83c9ff', '#ff8700'], label_theme=theme_mode)

            with col9:
                linha_x = 'MesAno'
                grafico = Chart(data_set)
                grafico.area_gradient(linha_x, linha_y, 'count', color4, 'Periodo',
                                      line_mean=True, label_theme=theme_mode)

            with col1:
                st.metric('Ambiente mais Vendido', str(ambiente_max))
            with col3:
                st.metric('Liberador com Mais Pedido', str(max_liberador))
            with col2:
                st.metric('Vendedor com Mais Pedido', str(max_vendas))
            with col4_:
                max_project = data_set.count().iloc[0]
                st.metric('Total de Projetos no Periodo', str(max_project))

        except IndexError:
            st.error("Não existem dados com base nos filtros selecionados")


if __name__ == "__main__":
    settings = Settings()
    data_inicial, data_final, cor_ambiente, cor_vendedor, cor_liberador, cor_periodo = settings.load_filtros()

    st.title("Dashboard de Projetos")
    page = ProjetosPage()
    resultado = page.render_sidebar(data_inicial, data_final, cor_ambiente, cor_vendedor, cor_liberador, cor_periodo)
    if resultado:
        page.render(*resultado)
