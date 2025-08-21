import pandas as pd
import streamlit as st
from graphics import Graph, detect_theme_mode
from Json import Settings
from babel.numbers import format_currency
from supabase import create_client, Client

def database(db_file=None, password=None) -> pd.DataFrame:
    """
    Retorna um DataFrame com os dados de 'tblProjetos' vindos do Supabase.
    Mantém o NOME e a ASSINATURA originais para não quebrar o código.
    Parâmetros db_file/password são ignorados nesta versão.
    """
    sb = st.secrets.get("supabase", {})
    url = sb.get("url")
    key = sb.get("key")
    if not url or not key:
        # Se preferir, troque por st.secrets['supabase']['url']/['key']
        raise RuntimeError("Defina SUPABASE_URL e SUPABASE_KEY nas variáveis de ambiente.")

    cli: Client = create_client(url, key)

    # Ajuste as colunas se quiser otimizar tráfego (aqui traz todas para manter compatibilidade)
    res = cli.table("tblProjetos").select("*").execute()
    df = pd.DataFrame(res.data or [])

    # Normalizações mínimas para compatibilidade com o restante do código
    # Garanta que as colunas esperadas existam (se não existirem na sua base, crie vazias)
    expected_cols = [
        'ordemdecompra', 'pronto', 'vendedor', 'liberador',
        'tipoambiente', 'loja'
    ]
    for col in expected_cols:
        if col not in df.columns:
            df[col] = pd.NA

    return df

df = database()

df['valornegociado'] = pd.to_numeric(df['valornegociado'], errors='coerce')

def filtrar_por_data(df: pd.DataFrame, data_inicio, data_fim, vendedor = None, liberador = None, ambiente = None, loja = None) -> pd.DataFrame:
    """
    Filtra o DataFrame com base no intervalo de datas fornecido.
    """
    criterio = 'pronto'
    # criterio = 'DataEntrega'

    df[criterio] = pd.to_datetime(df[criterio], errors='coerce')
    df['MesAno'] = df[criterio].dt.strftime('%Y-%m')

    df_filtrado = df[(df[criterio] >= data_inicio) & (df[criterio] <= data_fim)]

    if vendedor is not None:
        df_filtrado = df_filtrado[df_filtrado['vendedor'] == vendedor]
    if liberador is not None:
        df_filtrado = df_filtrado[df_filtrado['liberador'] == liberador]
    if ambiente is not None:
        df_filtrado = df_filtrado[df_filtrado['tipoambiente'] == ambiente]
    if loja is not None:
        df_filtrado = df_filtrado[df_filtrado['loja'] == loja]
    return df_filtrado

def loading_json():
    s = Settings()
    data_inicial = s.key('data_inicial')
    data_final = s.key('data_final')
    cor_ambiente = s.key('cor_ambiente')
    cor_vendedor = s.key('cor_vendedor')
    cor_liberador = s.key('cor_liberador')
    cor_periodo = s.key('cor_periodo')
    return data_inicial, data_final, cor_ambiente, cor_vendedor, cor_liberador, cor_periodo

def update_json(data_inicio, data_fim, color1, color2, color3, color4):
    s = Settings()
    s.update_json('data_inicial', data_inicio)
    s.update_json('data_final', data_fim)
    s.update_json('cor_ambiente', color1)
    s.update_json('cor_vendedor', color2)
    s.update_json('cor_liberador', color3)
    s.update_json('cor_periodo', color4)


def metrica(message, list_itens):
    st.write(f"**{message}**")
    for i, ambiente in enumerate(list_itens):
        if i == 0:
            st.metric('Ranking', f"{i+1} - {ambiente}", label_visibility="hidden")
        else:
            st.write(f"{i+1} - {ambiente}")
    st.write('')

def create_sidebar(data_inicial, data_final, cor_ambiente, cor_vendedor, cor_liberador, cor_periodo):

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

            data_set = filtrar_por_data(df, data_inicio, data_fim)

            # Crie as listas de opções
            vendedores = sorted(data_set['vendedor'].unique())
            liberadores = sorted(data_set['liberador'].unique())
            ambientes = sorted(data_set['tipoambiente'].unique())
            lojas = sorted(data_set['loja'].unique())

            # Crie os selectboxes
            fVendedor = st.selectbox('Vendedores', options=vendedores, placeholder='Selecione um Vendedor', index=None)
            fLiberador = st.selectbox('Liberadores', options=liberadores, placeholder='Selecione um Liberador', index=None)
            fAmbiente = st.selectbox('Ambiente', options=ambientes, placeholder='Selecione um Ambiente', index=None)
            floja = st.selectbox('Loja', options=lojas, index=None, placeholder='Selcione uma Loja')

            t1, t2, t3 = st.columns(3)
            with t3:
                filter_save = st.form_submit_button('Salvar')
                if filter_save:
                    update_json(data_inicio, data_fim, color1, color2, color3, color4)
            with t2:
                ...
            with t1:
                submit_button = st.form_submit_button('Filtrar')
                return data_inicio, data_fim, fVendedor, fLiberador, fAmbiente, floja, color1, color2, color3, color4

def create_grafs(data_inicio, data_fim, fVendedor, fLiberador, fambiente, floja, color1, color2, color3, color4):
    try:
        
        data_set = filtrar_por_data(df, data_inicio, data_fim, fVendedor, fLiberador, fambiente, floja)
        if data_set.empty:
            raise IndexError
        
        theme_mode = detect_theme_mode()
        col1, col2, col3, col4 = st.columns(4)
        col5, col6 = st.columns(2)
        col7, col8, col9 = st.columns(3)

        linha_y = 'valornegociado'
        
        with col5:
            linha_x = 'tipoambiente'
            t = Graph(data_set)
            t.bar(linha_x, linha_y, 'sum', color1, 'Ambientes', orient='horizontal', nlargest=True, label_theme=theme_mode)
            ambiente_max = t.top_max_value(linha_x, linha_y, 4)

        with col6:
            linha_x = 'vendedor'
            t = Graph(data_set)
            t.bar(linha_x, linha_y, 'sum', color2, linha_x, orient='horizontal', nlargest=True, label_theme=theme_mode)
            max_vendas = t.top_max_value(linha_x, linha_y, 3)

        with col7:
            linha_x = 'liberador'
            t = Graph(data_set)
            t.bar(linha_x, linha_y, 'sum', color3, linha_x, orient='horizontal', nlargest=True, label_theme=theme_mode)
            max_liberador = t.top_max_value(linha_x, linha_y, 3)

        with col8:
            linha_x = 'loja'
            t = Graph(data_set)
            t.circle(linha_x, linha_y, 'sum', 80, 140, 15, ['#29b09d', '#83c9ff', '#ff8700'])

        with col9:
            linha_x = 'MesAno'
            t = Graph(data_set)
            t.area_gradient(linha_x, linha_y, 'sum', color4, 'Periodo', line_mean=True, label_theme=theme_mode)

        with col1:
            metrica('Ambientes mais Vendidos', ambiente_max[0:3])
            
        with col3:
            metrica('Liberador com Mais Pedido', max_liberador[0:3])

        with col2:
            metrica('Vendedor com Mais Pedido', max_vendas[0:3])

        with col4:
            max_project = data_set.groupby('tipocontrato')[linha_y].sum().iloc[0]
            numero_formatado = format_currency(max_project, "BRL", locale="pt_BR")
            st.metric('Total de Faturamento no Período', numero_formatado)

    except IndexError as e:
        st.error("Não existem dados com base nos filtros selecionados")
