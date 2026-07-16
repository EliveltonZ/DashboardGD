import altair as alt
import pandas as pd
import streamlit as st
from babel.numbers import format_currency

from dashboard.core.settings import Settings
from dashboard.core.theme import detect_theme_mode
from dashboard.services.fabrica_service import FabricaService


class FabricaPage:
    """
    Dashboard de Produção - Fábrica: Faturamento vs. Vazão de projetos.

    Roteado no menu principal como "Financeiro" (ver novo.py).
    """

    def __init__(self) -> None:
        self._service = FabricaService()

    # ------------------------------------------------------------------
    # Sidebar
    # ------------------------------------------------------------------

    def render_sidebar(self, data_inicial, data_final, cor_ambiente, cor_vendedor, cor_liberador, cor_periodo):
        with st.sidebar:
            with st.form("filtros_novo_producao"):
                color1 = cor_ambiente
                color2 = cor_vendedor
                color3 = cor_liberador
                color4 = cor_periodo

                c1, c2 = st.columns(2)
                with c1:
                    data_inicio = str(st.date_input('Data de Início', value=pd.to_datetime(data_inicial), format='DD/MM/YYYY'))
                with c2:
                    data_fim = str(st.date_input('Data de Fim', value=pd.to_datetime(data_final), format='DD/MM/YYYY'))

                dados_periodo = self._service.filtrar(data_inicio, data_fim)
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

    # ------------------------------------------------------------------
    # Métricas (KPIs)
    # ------------------------------------------------------------------

    def _render_metricas(self, df_fat: pd.DataFrame, df_vaz: pd.DataFrame) -> None:
        """
        Renderiza os 6 cards de KPI.
        df_fat: projetos filtrados por dataentrega (base do Faturamento).
        df_vaz: projetos filtrados por pronto      (base da Vazão / produção).
        """
        col1, col2, col3 = st.columns(3)
        col4, col5, col6 = st.columns(3)

        faturamento = df_fat['valornegociado'].sum() if 'valornegociado' in df_fat.columns else 0.0
        col1.metric('Faturamento total fábrica (R$)', format_currency(faturamento, 'BRL', locale='pt_BR'))

        vazao_r = df_vaz['valornegociado'].sum() if 'valornegociado' in df_vaz.columns else 0.0
        col2.metric('Vazão de projetos (R$ produzido)', format_currency(vazao_r, 'BRL', locale='pt_BR'))

        lt_pedido = 0.0
        if 'chegoufabrica' in df_fat.columns and df_fat['chegoufabrica'].notna().any():
            lt_pedido = self._service.dias_uteis_medios(df_fat['chegoufabrica'], df_fat['entrega'])
        col3.metric('LT Médio Pedido (d.u.)', f"{lt_pedido:.1f}")

        vazao_n = len(df_vaz)
        col4.metric('Vazão de projetos (nº de finalizados)', vazao_n)

        for col_pecas in ('peças', 'totalitens', 'pecas'):
            if col_pecas in df_vaz.columns and df_vaz[col_pecas].notna().any():
                total = int(pd.to_numeric(df_vaz[col_pecas], errors='coerce').sum())
                col5.metric('Total de peças produzidas', f"{total:,}".replace(',', '.'))
                break
        else:
            col5.metric('Total de peças produzidas', 'N/D')

        lt_prod = 0.0
        if 'iniciado' in df_vaz.columns and df_vaz['iniciado'].notna().any():
            lt_prod = self._service.dias_uteis_medios(df_vaz['iniciado'], df_vaz['pronto'])
        col6.metric('LT Médio Produção (d.u.)', f"{lt_prod:.1f}")

    # ------------------------------------------------------------------
    # Gráfico combinado barra + linha
    # ------------------------------------------------------------------

    def _render_grafico_combinado(self, monthly: pd.DataFrame, color_bar: str, color_line: str, label_color: str) -> None:
        """
        Renderiza o gráfico combinado:
        - Barras = Faturamento total fábrica por mês
        - Linha  = Vazão de projetos (R$ produzido) por mês

        Cada camada usa alt.Chart independente para evitar que o Altair
        propague encodings de Y entre as camadas de texto (rótulos duplicados).
        """
        sorter = list(monthly['MesNome'])
        max_val = max(monthly['Faturamento'].max(), monthly['Vazao'].max())
        y_domain = [0, max_val * 1.18]
        y_scale = alt.Scale(domain=y_domain)
        x_enc = alt.X('MesNome:O', sort=sorter, title='Mês', axis=alt.Axis(labelAngle=-30))

        bars = alt.Chart(monthly).mark_bar(
            cornerRadiusTopLeft=4, cornerRadiusTopRight=4,
            color=alt.Gradient(
                gradient='linear',
                stops=[
                    alt.GradientStop(color='#0E1117', offset=0),
                    alt.GradientStop(color=color_bar, offset=1),
                ],
                x1=1, x2=1, y1=1, y2=0,
            ),
        ).encode(
            x=x_enc,
            y=alt.Y('Faturamento:Q', scale=y_scale, axis=alt.Axis(title='R$', format=',.0f')),
            tooltip=[
                alt.Tooltip('MesNome:N', title='Mês'),
                alt.Tooltip('label_fat:N', title='Faturamento (R$)'),
            ],
        )

        bar_labels = alt.Chart(monthly).mark_text(
            dy=-12, color=label_color, fontSize=11, tooltip=None
        ).encode(
            x=x_enc,
            y=alt.Y('Faturamento:Q', scale=y_scale),
            text=alt.Text('label_fat:N'),
        )

        line = alt.Chart(monthly).mark_line(
            strokeWidth=2.5,
            color=color_line,
            point=alt.OverlayMarkDef(filled=True, color=color_line, size=60),
        ).encode(
            x=x_enc,
            y=alt.Y('Vazao:Q', scale=y_scale),
            tooltip=[
                alt.Tooltip('MesNome:N', title='Mês'),
                alt.Tooltip('label_vaz:N', title='Vazão (R$)'),
            ],
        )

        line_labels = alt.Chart(monthly).mark_text(
            dy=-14, fontSize=11, tooltip=None,
            color=color_line,
        ).encode(
            x=x_enc,
            y=alt.Y('Vazao:Q', scale=y_scale),
            text=alt.Text('label_vaz:N'),
        )

        chart = (
            alt.layer(bars, bar_labels, line, line_labels)
            .properties(
                title=alt.TitleParams(
                    text='Vendas fábrica vs. Produção (R$)',
                    fontSize=16,
                    anchor='start',
                ),
                height=350,
            )
        )

        st.altair_chart(chart, use_container_width=True)

    # ------------------------------------------------------------------
    # Gráfico de barras — Vazão mensal com linha de média
    # ------------------------------------------------------------------

    def _render_grafico_vazao(self, monthly: pd.DataFrame, color_bar: str, label_color: str) -> None:
        """Barras de Vazão (R$ produzido) por mês com linha de média no período."""
        df = monthly.sort_values('MesAno').reset_index(drop=True)
        if df.empty or df['Vazao'].sum() == 0:
            return

        df['VazaoMid'] = df['Vazao'] / 2

        sorter = list(df['MesLabel'])
        max_val = df['Vazao'].max()
        y_domain = [0, max_val * 1.22]
        y_scale = alt.Scale(domain=y_domain)
        x_enc = alt.X('MesLabel:O', sort=sorter, title='mes_ano', axis=alt.Axis(labelAngle=0))

        bars = alt.Chart(df).mark_bar(
            cornerRadiusTopLeft=4, cornerRadiusTopRight=4, color=color_bar
        ).encode(
            x=x_enc,
            y=alt.Y('Vazao:Q', scale=y_scale,
                    axis=alt.Axis(title='Vazão de projetos (R$ produzido)', format=',.0f')),
            tooltip=[
                alt.Tooltip('MesNome:N', title='Mês'),
                alt.Tooltip('label_vaz:N', title='Vazão (R$)'),
            ],
        )

        bar_labels = alt.Chart(df).mark_text(
            fontSize=11, baseline='middle', color='white', tooltip=None
        ).encode(
            x=x_enc,
            y=alt.Y('VazaoMid:Q', scale=y_scale),
            text=alt.Text('label_vaz:N'),
        )

        mean_val = df['Vazao'].mean()
        mean_str = self._service.formatar_reais(mean_val).replace('R$ ', '')
        df = df.assign(mean=mean_val, mean_label=mean_str)

        mean_line = alt.Chart(df).mark_rule(
            color='#ff69b4', strokeDash=[4, 2], strokeWidth=1.5
        ).encode(y=alt.Y('mean:Q', scale=y_scale))

        mean_labels = alt.Chart(df).mark_text(
            dy=-8, fontSize=10, color=label_color, tooltip=None
        ).encode(
            x=x_enc,
            y=alt.Y('mean:Q', scale=y_scale),
            text=alt.Text('mean_label:N'),
        )

        chart = (
            alt.layer(bars, bar_labels, mean_line, mean_labels)
            .properties(
                title=alt.TitleParams(
                    text='Valor Produzido (R$)',
                    fontSize=16,
                    anchor='start',
                ),
                height=350,
            )
        )

        st.altair_chart(chart, use_container_width=True)

    # ------------------------------------------------------------------
    # Renderização principal
    # ------------------------------------------------------------------

    def render(self, data_inicio, data_fim, f_vendedor, f_liberador, f_ambiente, f_loja,
               color1, color2, color3, color4) -> None:
        """Carrega os dados filtrados e renderiza métricas + gráficos."""
        try:
            filtros = dict(vendedor=f_vendedor, liberador=f_liberador, loja=f_loja, tipo_ambiente=f_ambiente)

            # Faturamento: projetos com dataentrega no período (o que foi vendido/previsto)
            df_fat = self._service.filtrar(data_inicio, data_fim, **filtros, criterio='chegoufabrica')

            # Vazão: projetos com pronto no período (o que saiu da produção)
            df_vaz = self._service.filtrar(data_inicio, data_fim, **filtros, criterio='pronto')

            if df_fat.empty and df_vaz.empty:
                st.warning("Nenhum dado encontrado para os filtros selecionados.")
                return

            theme_mode = detect_theme_mode()
            label_color = 'white' if theme_mode == 'dark' else '#31333f'

            self._render_metricas(df_fat, df_vaz)

            st.divider()

            monthly = self._service.dados_mensais(df_fat, df_vaz)
            if monthly.empty:
                st.warning("Sem dados mensais para exibir o gráfico.")
                return

            col_a, col_b = st.columns(2)
            with col_a:
                self._render_grafico_combinado(monthly, color1, color3, label_color)
            with col_b:
                self._render_grafico_vazao(monthly, color2, label_color)

        except Exception as e:
            st.error(f"Erro ao carregar os dados: {e}")


if __name__ == '__main__':
    st.set_page_config(page_title="Produção - Fábrica", layout="wide")
    settings = Settings()
    data_inicial, data_final, cor_ambiente, cor_vendedor, cor_liberador, cor_periodo = settings.load_filtros()

    page = FabricaPage()
    resultado = page.render_sidebar(data_inicial, data_final, cor_ambiente, cor_vendedor, cor_liberador, cor_periodo)
    page.render(*resultado)
