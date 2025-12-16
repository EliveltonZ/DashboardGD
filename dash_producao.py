# app.py
import pandas as pd
import altair as alt
import streamlit as st
from datetime import datetime
from typing import Literal
from supabase import Client, create_client
from generator import Generator

# =============================================================================
# Conexão Supabase via SDK + RPC exec_sql(text)
# =============================================================================


@st.cache_resource(show_spinner=False)
def get_client() -> Client:
    cfg = st.secrets["supabase"]  # precisa conter: url e anon_key (ou service_role_key)
    key = cfg.get("service_role_key") or cfg.get("anon_key") or cfg.get("key")
    return create_client(cfg["url"], key)

def _bind_params(sql: str, params: dict | None) -> str:
    if not params:
        return sql
    out = sql
    for k, v in params.items():
        if v is None:
            repl = "NULL"
        elif isinstance(v, (int, float)):
            repl = str(v)
        else:
            repl = "'" + str(v).replace("'", "''") + "'"
        out = out.replace(f":{k}", repl)
    return out

def _strip_leading_comments_spaces(s: str) -> str:
    import re
    return re.sub(r'^(?:--[^\n]*\n|\s+|/\*.*?\*/)+', '', s, flags=re.S)

def _trim_trailing_semicolons(sql: str) -> str:
    # remove ; finais (um ou mais) + espaços
    return sql.rstrip().rstrip(';').rstrip()

def _force_select_prefix(sql: str) -> str:
    """Se começar com WITH, embrulha em SELECT * FROM (...) t."""
    s = _strip_leading_comments_spaces(sql.lstrip())
    head = s[:8].lower()
    if head.startswith('select'):
        return sql
    if head.startswith('with'):
        return f"SELECT * FROM (\n{sql}\n) t"
    return sql

def database(query: str, params: dict | None = None) -> pd.DataFrame:
    client = get_client()
    # 1) aplica parâmetros
    query = _bind_params(query, params)
    # 2) remove ; finais
    query = _trim_trailing_semicolons(query)
    # 3) se começar com WITH, embrulha
    query = _force_select_prefix(query)

    # (opcional) debug:
    # st.write("SQL executado:", query)

    resp = client.rpc("exec_sql", {"q": query}).execute()
    rows = resp.data or []
    norm = [r.get("exec_sql", r) for r in rows]
    return pd.DataFrame(norm)

# =============================================================================
# Utils
# =============================================================================

def convert_to_str(df: pd.DataFrame, coluna: str) -> None:
    df[coluna] = df[coluna].astype(str).str.rstrip('0').str.rstrip('.')

def convert_to_date(df: pd.DataFrame, column: str) -> None:
    df[column] = pd.to_datetime(df[column], errors='coerce')

def format_date(df: pd.DataFrame, column: str) -> None:
    df[column] = df[column].dt.strftime("%d/%m/%Y %H:%M:%S")

def cell_color(val, lista: list) -> Literal['color: yellow', 'color: red', '']:
    if val in lista and check_date(val):
        return 'color: red'
    elif val in lista:
        return 'color: yellow'
    else:
        return ''

def check_date(date_str) -> bool:
    date = datetime.strptime(date_str, "%d/%m/%Y %H:%M:%S") 
    hoje = datetime.today().replace(microsecond=0)
    return date < hoje

# =============================================================================
# SQL helpers
# =============================================================================

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

def etapa_case(prefixo: str) -> str:
    # prefixo: "Corte", "Customizacao", "Coladeira", "Usinagem", "Paineis", "Montagem", "Embalagem"
    return f"""
    CASE 
      WHEN pr."{prefixo}fim" IS NOT NULL THEN 'FINALIZADO'
      WHEN pr."{prefixo}inicio" IS NOT NULL THEN 'INICIADO'
      ELSE 'AGUARDE'
    END
    """

# =============================================================================
# UI
# =============================================================================

def create_sidebar():
    with st.sidebar:
        with st.form("my_form1"):
            fProjecao = st.date_input('Projeção', format='DD/MM/YYYY')

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
                p."cliente",
                p."contrato",
                p."ambiente",
                {STATUS_CASE} AS "Status",
                (p."dataentrega"::date - :proj::date) AS "Prazo",
                {etapa_case("corte")}           AS "SCorte",
                {etapa_case("customizacao")}    AS "SCustom",
                {etapa_case("coladeira")}       AS "SColadeira",
                {etapa_case("usinagem")}        AS "SUsinagem",
                {etapa_case("paineis")}         AS "SPaineis",
                {etapa_case("montagem")}        AS "SMontagem",
                {etapa_case("embalagem")}       AS "SEmbalagem",
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
              WHERE p."ordemdecompra" > 0
            )
            SELECT * FROM dados
            WHERE "Status" IN ('INICIADO','ATRASADO','A VENCER','URGENTE','PENDENCIA')
            ORDER BY "previsao", "urgente", "Prazo", "cliente", "codcc";
            """

            proj_iso = getattr(fProjecao, "isoformat", lambda: str(fProjecao))()
            df = database(query, params={"proj": proj_iso})

            options = sorted(df['Status'].unique()) if not df.empty else []
            fOption = st.selectbox(
                'Status de Produção', options=options, placeholder='Selecione um Status', index=None
            )

            t1, t2, t3 = st.columns(3)
            with t2:
                submit_button = st.form_submit_button('Filtrar')
                return fOption, df, None, fProjecao
            with t1:
                pass
            with t3:
                pass

def create_grafs(filter, df, _db_path_nao_usado, fProjecao):
    if df is None or df.empty:
        st.warning("Sem dados para exibir.")
        return

    if filter:
        df = df[df['Status'] == filter]

    status_columns = ['SCorte', 'SCustom', 'SColadeira', 'SPaineis', 'SUsinagem', 'SMontagem', 'SEmbalagem']
    title_mapping = {col: col[1:] for col in status_columns}

    melted_df = df.melt(
        id_vars=['ordemdecompra'],
        value_vars=status_columns,
        var_name='Etapa',
        value_name='Status_Producao'
    )

    melted_df['Etapa_Titulo'] = melted_df['Etapa'].map(title_mapping)

    range_colors = ['red', '#2ca02c', '#B1AE03']

    tab1, tab2, tab3 = st.tabs(['Produção', 'Estatistica', 'Previsoes'])

    with tab1:
        bars = alt.Chart(melted_df).mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(
            x=alt.X('Etapa_Titulo:N', sort=status_columns),
            y=alt.Y('count()', type='quantitative'),
            color=alt.Color(field='Status_Producao', type='nominal').scale(range=range_colors)
        ).properties(title='Status de Produção por Etapa', width=600, height=400)

        col1, col2, col3 = st.columns(3)
        with col2:
            st.altair_chart(bars, use_container_width=True)

        color_map = {
            'A VENCER': '#DA8B05',
            'ATRASADO': '#FB040C',
            'INICIADO': '#F9F303',
            'PENDENCIA': '#AB13F3',
            'URGENTE': '#0276D2',
        }

        status_count = df['Status'].value_counts().reset_index()
        status_count.columns = ['Status', 'Contagem']
        status_count['Porcentagem'] = (status_count['Contagem'] / status_count['Contagem'].sum()) * 100
        status_count['%'] = status_count['Porcentagem'].apply(lambda x: f'{x:.0f}%')

        chart = alt.Chart(status_count).mark_arc(innerRadius=70, outerRadius=120, cornerRadius=10,
                                                 stroke="rgba(255, 255, 255, 0.2)", strokeWidth=5).encode(
            theta=alt.Theta(field='Contagem', type='quantitative', stack=True),
            color=alt.Color(field='Status', type='nominal',
                            scale=alt.Scale(domain=list(color_map.keys()), range=list(color_map.values()))),
            tooltip=[alt.Tooltip(field='Status', type='nominal'),
                     alt.Tooltip(field='Contagem', type='quantitative', title='Total')]
        ).properties(title='Distribuição por Status', height=350)

        label = chart.mark_text(radius=140, size=13).encode(text=alt.Text(field='%', type='nominal'))
        with col1:
            st.altair_chart(chart + label, use_container_width=True)  # type: ignore

        chart2 = alt.Chart(df).mark_point(filled=True, fillOpacity=0.2, size=70).encode(
            x=alt.X(field='dataentrega', type='temporal', timeUnit='utcdate'),
            y='Prazo:Q',
            color=alt.Color(field='Status', type='nominal',
                            scale=alt.Scale(domain=list(color_map.keys()), range=list(color_map.values()))),
            tooltip=['ordemdecompra:N', 'dataentrega:T', 'Prazo:Q', 'Status:N', 'cliente:N']
        ).properties(title='Prazos de Entrega vs. Dias Restantes')

        with col3:
            st.altair_chart(chart2, use_container_width=True)

        cliente_contrato = df.groupby('cliente')['contrato'].count().reset_index()
        cliente_contrato.columns = ['cliente', 'ambientes']
        cliente_contrato = cliente_contrato.sort_values(by='ambientes', ascending=False)

        chart_clientes = alt.Chart(cliente_contrato).mark_bar().encode(
            x=alt.X('cliente:N', sort='-y'),
            y='ambientes:Q',
            color='ambientes:Q'
        ).properties(title='Número de ambientes por cliente')

        st.altair_chart(chart_clientes, use_container_width=True)

    with tab2:
        tamanho = 130
        from database_media import df_media_intervalo
        if 'Etapa' in df_media_intervalo:
            circle = alt.Chart(df_media_intervalo).mark_arc(
                cornerRadius=10, innerRadius=tamanho*0.53, outerRadius=tamanho,
                stroke="rgba(255, 255, 255, 0.2)", strokeWidth=5
            ).encode(
                theta=alt.Theta(field='Percentual', type='quantitative', stack=True),
                color=alt.Color(field='Etapa', type='nominal'),
                tooltip=[alt.Tooltip(field="Etapa", type="nominal"),
                         alt.Tooltip(field="Media", type="nominal")]
            )
            label = circle.mark_text(radius=tamanho+20, size=13).encode(text='%').properties()
            st.altair_chart(circle + label, use_container_width=True)  # type: ignore
        else:
            st.error("A coluna 'Etapa' não existe no DataFrame df_media_intervalo.")

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
            etapa_counts = df[status_columns].apply(pd.Series.value_counts).fillna(0).sum(axis=1)
            for etapa, count in etapa_counts.items():
                st.metric(f"Etapas em {etapa}", int(count))

        with col4:
            status_distribution = (melted_df['Status_Producao'].value_counts(normalize=True) * 100).round(2)
            for status, percent in status_distribution.items():
                st.metric(f"Percentual de Status {status}", f"{percent:.2f}%")

    with tab3:
        sql = f"""
        WITH dados AS (
          SELECT 
            p."codcc",
            p."cliente",
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
          WHERE p."ordemdecompra" > 0
        )
        SELECT * FROM dados
        WHERE "Status" IN ('INICIADO','ATRASADO','A VENCER','URGENTE','PENDENCIA')
        ORDER BY "previsao", "urgente", "Prazo", "cliente", "codcc";
        """
        proj_iso = getattr(fProjecao, "isoformat", lambda: str(fProjecao))()
        dfp = database(sql, params={"proj": proj_iso})

        if dfp.empty:
            st.warning("Sem dados para previsões.")
            return

        convert_to_str(dfp, 'codcc')
        convert_to_str(dfp, 'contrato')

        columns = ['corteinicio', 'cortefim', 'customizacaoinicio', 'customizacaofim',
                   'coladeirainicio', 'coladeirafim', 'usinageminicio', 'usinagemfim',
                   'montageminicio', 'montagemfim', 'paineisinicio', 'paineisfim',
                   'embalageminicio', 'embalagemfim']

        dfp['dataentrega'] = pd.to_datetime(dfp['dataentrega']).dt.strftime('%d/%m/%Y')
        dfp['previsao'] = pd.to_datetime(dfp['previsao']).dt.strftime('%d/%m/%Y')
        dfp['Prazo'] = dfp['Prazo'].astype(int)

        for col in columns:
            convert_to_date(dfp, col)
            format_date(dfp, col)

        def create_df_filled(df_in: pd.DataFrame):
            df_estilo = df_in.copy()
            estilo: list = []
            list_columns = ['corteinicio', 'customizacaoinicio', 'coladeirainicio', 'usinageminicio',
                            'paineisinicio', 'montageminicio', 'embalageminicio']
            gerador = Generator(list_columns)

            for index, row in df_in.iterrows():
                for col in df_in.columns[6:20]:
                    if pd.isnull(row[col]):
                        data_hora = gerador.fill_mean_time(col)
                        df_estilo.at[index, col] = data_hora
                        estilo.append(data_hora)
                        gerador.last_date(data_hora)
                    else:
                        gerador.last_date(str(row[col]))

            styled_df = df_estilo.style.map(lambda x: cell_color(x, estilo),
                                            subset=pd.IndexSlice[:, df_in.columns[6:20]])
            return styled_df

        col_order = ['codcc', 'cliente', 'ambiente', 'contrato', 'Status', 'Prazo', 
                    'corteinicio', 'cortefim', 'customizacaoinicio', 'customizacaofim',
                   'coladeirainicio', 'coladeirafim', 'usinageminicio', 'usinagemfim',
                   'montageminicio', 'montagemfim', 'paineisinicio', 'paineisfim',
                   'embalageminicio', 'embalagemfim', 'urgente', 'dataentrega', 'previsao']
        dfp = dfp[col_order]
        df2_styled = create_df_filled(dfp)
        st.dataframe(df2_styled)

# =============================================================================
# main
# =============================================================================

if __name__ == '__main__':
    st.set_page_config(page_title="Produção", layout="wide")
    fOption, df, _, fProjecao = create_sidebar()
    create_grafs(fOption, df, None, fProjecao)
