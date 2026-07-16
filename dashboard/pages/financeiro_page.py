import pandas as pd
import streamlit as st
from babel.numbers import format_currency

from dashboard.core.charts import Chart
from dashboard.core.settings import Settings
from dashboard.core.theme import detect_theme_mode
from dashboard.services.financeiro_service import FinanceiroService


class FinanceiroPage:
    """
    Dashboard Financeiro: ranking de ambientes/vendedores/liberadores e faturamento por período.

    Página migrada e mantida disponível para uso standalone, mas não está roteada em novo.py —
    o menu "Financeiro" hoje abre o dashboard de Produção - Fábrica (ver fabrica_page.py).
    """

    def __init__(self) -> None:
        self._service = FinanceiroService()

    def render_sidebar(self, data_inicial, data_final, cor_ambiente, cor_vendedor, cor_liberador, cor_periodo):
        df = self._service.carregar_dados()

        with st.sidebar:
            with st.form("filtros_financeiro"):
                s1, s2, s3, s4 = st.columns(4)
                with s1:
                    color1 = st.color_picker("Amb", cor_ambiente, help='Cor para Ambiente')
                with s2:
                    color2 = st.color_picker("Vnd", cor_vendedor, help='Cor para Vendedor')
                with s3:
                    color3 = st.color_picker("Lib", cor_liberador, help='Cor para Liberador')
                with s4:
                    color4 = st.color_picker("Prd", cor_periodo, help='Cor para Período')

                c1, c2 = st.columns(2)
                with c1:
                    data_inicio = str(st.date_input('Data de Início', value=pd.to_datetime(data_inicial), format='DD/MM/YYYY'))
                with c2:
                    data_fim = str(st.date_input('Data de Fim', value=pd.to_datetime(data_final), format='DD/MM/YYYY'))

                dados_periodo = self._service.filtrar(df, data_inicio, data_fim)
                vendedores = sorted(dados_periodo['vendedor'].dropna().unique())
                liberadores = sorted(dados_periodo['liberador'].dropna().unique())
                ambientes = sorted(dados_periodo['tipoambiente'].dropna().unique())
                lojas = sorted(dados_periodo['loja'].dropna().unique())

                f_vendedor = st.selectbox('Vendedores', options=vendedores, placeholder='Selecione um Vendedor', index=None)
                f_liberador = st.selectbox('Liberadores', options=liberadores, placeholder='Selecione um Liberador', index=None)
                f_ambiente = st.selectbox('Ambiente', options=ambientes, placeholder='Selecione um Ambiente', index=None)
                f_loja = st.selectbox('Loja', options=lojas, placeholder='Selecione uma Loja', index=None)

                t1, t2, t3 = st.columns(3)
                with t1:
                    st.form_submit_button('Filtrar')
                with t3:
                    if st.form_submit_button('Salvar'):
                        Settings().save_filtros(data_inicio, data_fim, color1, color2, color3, color4)

                return data_inicio, data_fim, f_vendedor, f_liberador, f_ambiente, f_loja, color1, color2, color3, color4

    @staticmethod
    def _exibir_ranking(titulo: str, itens: list) -> None:
        st.write(f"**{titulo}**")
        for posicao, item in enumerate(itens):
            if posicao == 0:
                st.metric('Ranking', f"{posicao + 1} - {item}", label_visibility="hidden")
            else:
                st.write(f"{posicao + 1} - {item}")
        st.write('')

    def render(self, data_inicio, data_fim, f_vendedor, f_liberador, f_ambiente, f_loja,
               color1, color2, color3, color4) -> None:
        df = self._service.carregar_dados()

        try:
            dados = self._service.filtrar(df, data_inicio, data_fim, f_vendedor, f_liberador, f_ambiente, f_loja)
            if dados.empty:
                raise IndexError

            theme_mode = detect_theme_mode()
            col1, col2, col3, col4 = st.columns(4)
            col5, col6 = st.columns(2)
            col7, col8, col9 = st.columns(3)

            valor = 'valornegociado'

            with col5:
                grafico = Chart(dados)
                grafico.bar('tipoambiente', valor, 'sum', color1, 'Ambientes',
                            orient='horizontal', nlargest=True, label_theme=theme_mode)
                top_ambientes = grafico.top_max_value('tipoambiente', valor, 4)

            with col6:
                grafico = Chart(dados)
                grafico.bar('vendedor', valor, 'sum', color2, 'Vendedor',
                            orient='horizontal', nlargest=True, label_theme=theme_mode)
                top_vendedores = grafico.top_max_value('vendedor', valor, 3)

            with col7:
                grafico = Chart(dados)
                grafico.bar('liberador', valor, 'sum', color3, 'Liberador',
                            orient='horizontal', nlargest=True, label_theme=theme_mode)
                top_liberadores = grafico.top_max_value('liberador', valor, 3)

            with col8:
                grafico = Chart(dados)
                grafico.circle('loja', valor, 'sum', 80, 140, 15, ['#29b09d', '#83c9ff', '#ff8700'])

            with col9:
                grafico = Chart(dados)
                grafico.area_gradient('MesAno', valor, 'sum', color4, 'Período',
                                      line_mean=True, label_theme=theme_mode)

            with col1:
                self._exibir_ranking('Ambientes mais Vendidos', top_ambientes[:3])
            with col2:
                self._exibir_ranking('Vendedor com Mais Pedido', top_vendedores[:3])
            with col3:
                self._exibir_ranking('Liberador com Mais Pedido', top_liberadores[:3])
            with col4:
                total = dados.groupby('tipocontrato')[valor].sum().iloc[0]
                st.metric('Total de Faturamento no Período', format_currency(total, "BRL", locale="pt_BR"))

        except IndexError:
            st.error("Não existem dados com base nos filtros selecionados.")


if __name__ == '__main__':
    st.set_page_config(page_title="Financeiro", layout="wide")
    settings = Settings()
    data_inicial, data_final, cor_ambiente, cor_vendedor, cor_liberador, cor_periodo = settings.load_filtros()

    page = FinanceiroPage()
    resultado = page.render_sidebar(data_inicial, data_final, cor_ambiente, cor_vendedor, cor_liberador, cor_periodo)
    page.render(*resultado)
