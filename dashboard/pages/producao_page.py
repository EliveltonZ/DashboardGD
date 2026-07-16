import altair as alt
import pandas as pd
import streamlit as st

from dashboard.core.settings import Settings
from dashboard.services.producao_stats_service import ProducaoStatsService
from dashboard.services.producao_status_service import ProducaoStatusService


class ProducaoPage:
    """Dashboard de Produção: status por etapa, estatísticas de duração e previsões de entrega."""

    RANGE_STATUS_ETAPA = {
        'AGUARDE': "#F90303",
        'INICIADO': '#B1AE03',
        'FINALIZADO': '#2ca02c',
    }
    RANGE_STATUS_GERAL = {
        'A VENCER': '#DA8B05',
        'ATRASADO': '#FB040C',
        'INICIADO': '#F9F303',
        'PENDENCIA': '#AB13F3',
        'URGENTE': '#0276D2',
    }

    def __init__(self) -> None:
        self._status_service = ProducaoStatusService()
        self._stats_service = ProducaoStatsService()
        self._default_ini, self._default_fim = Settings().load_periodo()

    # ------------------------------------------------------------------
    # Sidebar
    # ------------------------------------------------------------------

    def render_sidebar(self):
        with st.sidebar:
            with st.form("my_form1"):
                f_projecao = st.date_input('Projeção', format='DD/MM/YYYY')

                st.markdown("### Período (Estatística)")
                f_ini = st.date_input("Início", value=pd.to_datetime(self._default_ini), format='DD/MM/YYYY')
                f_fim = st.date_input("Fim", value=pd.to_datetime(self._default_fim), format='DD/MM/YYYY')

                df = self._status_service.carregar_status(f_projecao)

                options = sorted(df['Status'].unique()) if not df.empty else []
                f_option = st.selectbox('Status de Produção', options=options,
                                        placeholder='Selecione um Status', index=None)

                t1, t2, t3 = st.columns(3)
                with t2:
                    st.form_submit_button('Filtrar')
                    return f_option, df, f_projecao, f_ini, f_fim
                with t1:
                    pass
                with t3:
                    pass

    # ------------------------------------------------------------------
    # Gráficos / abas
    # ------------------------------------------------------------------

    def render(self, filtro, df, f_projecao, f_ini, f_fim) -> None:
        if df is None or df.empty:
            st.warning("Sem dados para exibir.")
            return

        if filtro:
            df = df[df['Status'] == filtro]

        melted_df = self._status_service.montar_status_melted(df)

        tab1, tab2, tab3 = st.tabs(['Produção', 'Estatistica', 'Previsoes'])

        with tab1:
            self._render_tab_producao(df, melted_df)
        with tab2:
            self._render_tab_estatistica(df, melted_df, f_ini, f_fim)
        with tab3:
            self._render_tab_previsoes(f_projecao)

    def _render_tab_producao(self, df: pd.DataFrame, melted_df: pd.DataFrame) -> None:
        bars = alt.Chart(melted_df).mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(
            x=alt.X('Etapa_Titulo:N', sort=alt.SortField(field='Etapa_Ordem', order='ascending')),
            y=alt.Y('count()', type='quantitative'),
            color=alt.Color(field='Status_Producao', type='nominal',
                            scale=alt.Scale(domain=list(self.RANGE_STATUS_ETAPA.keys()),
                                            range=list(self.RANGE_STATUS_ETAPA.values())))
        ).properties(title='Status de Produção por Etapa', height=300)

        col1, col2, col3 = st.columns(3)
        with col2:
            st.altair_chart(bars, use_container_width=True)

        status_count = df['Status'].value_counts().reset_index()
        status_count.columns = ['Status', 'Contagem']
        status_count['Porcentagem'] = (status_count['Contagem'] / status_count['Contagem'].sum()) * 100
        status_count['%'] = status_count['Porcentagem'].apply(lambda x: f'{x:.0f}%')

        chart = alt.Chart(status_count).mark_arc(
            innerRadius=70, outerRadius=120, cornerRadius=10,
            stroke="rgba(255, 255, 255, 0.2)", strokeWidth=5
        ).encode(
            theta=alt.Theta(field='Contagem', type='quantitative', stack=True),
            color=alt.Color(field='Status', type='nominal',
                            scale=alt.Scale(domain=list(self.RANGE_STATUS_GERAL.keys()),
                                            range=list(self.RANGE_STATUS_GERAL.values()))),
            tooltip=[alt.Tooltip(field='Status', type='nominal'),
                     alt.Tooltip(field='Contagem', type='quantitative', title='Total')]
        ).properties(title='Distribuição por Status', height=300)

        label = chart.mark_text(radius=140, size=13).encode(text=alt.Text(field='%', type='nominal'))
        with col1:
            st.altair_chart(chart + label, use_container_width=True)

        chart2 = alt.Chart(df).mark_point(filled=True, fillOpacity=0.2, size=70).encode(
            x=alt.X(field='dataentrega', type='temporal', timeUnit='utcdate'),
            y='Prazo:Q',
            color=alt.Color(field='Status', type='nominal',
                            scale=alt.Scale(domain=list(self.RANGE_STATUS_GERAL.keys()),
                                            range=list(self.RANGE_STATUS_GERAL.values()))),
            tooltip=['ordemdecompra:N', 'dataentrega:T', 'Prazo:Q', 'Status:N', 'cliente:N']
        ).properties(title='Prazos de Entrega vs. Dias Restantes')

        chart_clientes = None
        with col3:
            st.altair_chart(chart2, use_container_width=True)

            cliente_contrato = (
                df.groupby("cliente", dropna=False)["contrato"]
                .size()
                .reset_index(name="ambientes")
            )
            cliente_contrato["cliente"] = cliente_contrato["cliente"].fillna("SEM CLIENTE").astype(str)
            cliente_contrato["ambientes"] = pd.to_numeric(cliente_contrato["ambientes"], errors="coerce").fillna(0).astype(int)

            if cliente_contrato.empty:
                st.warning("Sem dados para o gráfico de clientes.")
            else:
                chart_clientes = alt.Chart(cliente_contrato).mark_bar().encode(
                    x=alt.X("cliente:N", sort=alt.SortField(field="ambientes", order="descending"), title="Cliente"),
                    y=alt.Y("ambientes:Q", title="Ambientes"),
                    tooltip=[alt.Tooltip("cliente:N"), alt.Tooltip("ambientes:Q")],
                ).properties(title="Número de ambientes por cliente")

        if chart_clientes is not None:
            st.altair_chart(chart_clientes, use_container_width=True)

    def _render_tab_estatistica(self, df: pd.DataFrame, melted_df: pd.DataFrame, f_ini, f_fim) -> None:
        tamanho = 130

        inicio_iso = getattr(f_ini, "isoformat", lambda: str(f_ini))()
        fim_iso = getattr(f_fim, "isoformat", lambda: str(f_fim))()

        df_filtrado, df_medias, medias_dec, medias_hhmm = self._stats_service.run_pipeline(inicio_iso, fim_iso)

        if not df_medias.empty and "Etapa" in df_medias.columns:
            circle = alt.Chart(df_medias).mark_arc(
                cornerRadius=10, innerRadius=tamanho * 0.53, outerRadius=tamanho,
                stroke="rgba(255, 255, 255, 0.2)", strokeWidth=5
            ).encode(
                theta=alt.Theta(field='Percentual', type='quantitative', stack=True),
                color=alt.Color(field='Etapa', type='nominal'),
                tooltip=[alt.Tooltip(field="Etapa", type="nominal"),
                         alt.Tooltip(field="Media", type="nominal")]
            )
            label = circle.mark_text(radius=tamanho + 20, size=13).encode(text='%').properties()
            st.altair_chart(circle + label, use_container_width=True)
        else:
            st.warning("Sem dados para médias por etapa no período selecionado.")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            total_ordens = df['ordemdecompra'].nunique()
            st.metric("Total de Ordens de Compra", total_ordens)

            prazo_medio = df['Prazo'].mean()
            st.metric("Prazo Médio de Entrega (dias)", f"{prazo_medio:.2f}")

            contratos_por_cliente = df.groupby('cliente')['contrato'].count().reset_index()
            cliente_mais_contratos = contratos_por_cliente.sort_values(by='contrato', ascending=False).iloc[0]
            st.metric(f"cliente com Mais contratos ({cliente_mais_contratos['cliente']})",
                      int(cliente_mais_contratos['contrato']))

            projetos_atrasados = df[df['Prazo'] < 0].shape[0]
            st.metric("Número de Projetos Atrasados", projetos_atrasados)

        with col2:
            for status, count in df['Status'].value_counts().items():
                st.metric(f"Projetos com Status {status}", count)

        with col3:
            etapa_counts = df[ProducaoStatusService.STATUS_COLUMNS].apply(pd.Series.value_counts).fillna(0).sum(axis=1)
            for etapa, count in etapa_counts.items():
                st.metric(f"Etapas em {etapa}", int(count))

        with col4:
            status_distribution = (melted_df['Status_Producao'].value_counts(normalize=True) * 100).round(2)
            for status, percent in status_distribution.items():
                st.metric(f"Percentual de Status {status}", f"{percent:.2f}%")

    def _render_tab_previsoes(self, f_projecao) -> None:
        dfp = self._status_service.carregar_previsoes(f_projecao)

        if dfp.empty:
            st.warning("Sem dados para previsões.")
            return

        styled = self._status_service.preparar_previsoes(dfp)
        st.dataframe(styled)


if __name__ == '__main__':
    st.set_page_config(page_title="Produção", layout="wide")
    page = ProducaoPage()
    f_option, df, f_projecao, f_ini, f_fim = page.render_sidebar()
    page.render(f_option, df, f_projecao, f_ini, f_fim)
