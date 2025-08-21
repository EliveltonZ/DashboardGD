import pandas as pd
import streamlit as st
from graphics import Graph
from Json import Settings
from supabase import create_client, Client

# ===== Detecção de tema (no principal) =====
def detect_theme_mode() -> str:
    """
    Retorna 'dark' ou 'light'.
    1) tenta via JS (prefers-color-scheme) usando streamlit-js-eval (se instalado)
    2) fallback: calcula por theme.backgroundColor
    3) padrão: 'light'
    """
    # 1) JavaScript tempo real (opcional)
    try:
        from streamlit_js_eval import streamlit_js_eval  # type: ignore
        mode = streamlit_js_eval(
            js_expressions="(window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) ? 'dark' : 'light'",
            key="__theme_mode__", want_output=True, default="light"
        )
        if mode in ("dark", "light"):
            return mode
    except Exception:
        pass

    # 2) Fallback pelo background do tema
    bg = st.get_option("theme.backgroundColor")
    if bg:
        s = bg.lstrip("#")
        if len(s) == 3:
            s = "".join([c*2 for c in s])
        try:
            r, g, b = [int(s[i:i+2], 16) for i in (0, 2, 4)]
            lum = 0.2126*(r/255)**2.2 + 0.7152*(g/255)**2.2 + 0.0722*(b/255)**2.2
            return "light" if lum > 0.5 else "dark"
        except Exception:
            pass

    # 3) Padrão seguro
    return "light"


# ==========================
# Fonte de dados (Supabase)
# ==========================
def database(db_file=None, password=None) -> pd.DataFrame:
    sb = st.secrets.get("supabase", {})
    url = sb.get("url")
    key = sb.get("key")
    if not url or not key:
        raise RuntimeError("Defina 'supabase.url' e 'supabase.key' em st.secrets.")

    cli: Client = create_client(url, key)
    res = cli.table("tblProjetos").select("*").execute()
    df = pd.DataFrame(res.data or [])

    expected_cols = [
        'ordemdecompra', 'pronto', 'vendedor', 'liberador',
        'tipoambiente', 'loja'
    ]
    for col in expected_cols:
        if col not in df.columns:
            df[col] = pd.NA

    return df


df = database()


# ==========================
# Filtros / Transformações
# ==========================
def filtrar_por_data(df: pd.DataFrame, data_inicio, data_fim,
                     vendedor=None, liberador=None, ambiente=None, loja=None) -> pd.DataFrame:
    criterio = 'pronto'   # ou 'DataEntrega'
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


def dados(dataframe: pd.DataFrame, column: str) -> pd.DataFrame:
    data = dataframe.groupby([column], as_index=False).count()
    # mantenho assinatura original (ajuste se sua coluna real for 'ordemdecompra')
    result = data[[column, 'OrdemdeCompra']]
    return result


# ==========================
# JSON (preferências)
# ==========================
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


# ==========================
# Sidebar (filtros)
# ==========================
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

            vendedores = sorted(pd.Series(data_set['vendedor']).dropna().unique())
            liberadores = sorted(pd.Series(data_set['liberador']).dropna().unique())
            ambientes = sorted(pd.Series(data_set['tipoambiente']).dropna().unique())
            lojas = sorted(pd.Series(data_set['loja']).dropna().unique())

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


# ==========================
# Gráficos (dashboard)
# ==========================
def create_grafs(data_inicio, data_fim, fVendedor, fLiberador, fambiente, floja,
                 color1, color2, color3, color4):
    try:
        data_set = filtrar_por_data(df, data_inicio, data_fim, fVendedor, fLiberador, fambiente, floja)
        if data_set.empty:
            raise IndexError

        # Detecta tema aqui (uma vez) e passa para todos os gráficos
        theme_mode = detect_theme_mode()  # 'dark' | 'light'
        st.write(theme_mode)
        col1, col2, col3, col4_ = st.columns(4)
        col5, col6 = st.columns(2)
        col7, col8, col9 = st.columns(3)

        linha_y = 'ordemdecompra'

        with col5:
            linha_x = 'tipoambiente'
            t = Graph(data_set)
            t.bar(linha_x, linha_y, 'count', color1, 'Ambientes', label_theme=theme_mode)
            ambiente_max = t.max_value(linha_x, linha_y)

        with col6:
            linha_x = 'vendedor'
            t = Graph(data_set)
            t.bar(linha_x, linha_y, 'count', color2, linha_x, line_mean=True, label_theme=theme_mode)
            max_vendas = t.max_value(linha_x, linha_y)

        with col7:
            linha_x = 'liberador'
            t = Graph(data_set)
            t.bar(linha_x, linha_y, 'count', color3, linha_x, line_mean=True, label_theme=theme_mode)
            max_liberador = t.max_value(linha_x, linha_y)

        with col8:
            linha_x = 'loja'
            t = Graph(data_set)
            t.circle(linha_x, linha_y, 'count', 80, 140, 15,
                     ['#29b09d', '#83c9ff', '#ff8700'], label_theme=theme_mode)

        with col9:
            linha_x = 'MesAno'
            t = Graph(data_set)
            t.area_gradient(linha_x, linha_y, 'count', color4, 'Periodo',
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


# ==========================
# App
# ==========================
def main():
    st.title("Dashboard de Projetos")
    data_inicial, data_final, cor_ambiente, cor_vendedor, cor_liberador, cor_periodo = loading_json()
    ret = create_sidebar(data_inicial, data_final, cor_ambiente, cor_vendedor, cor_liberador, cor_periodo)
    if ret:
        (data_inicio, data_fim, fVendedor, fLiberador, fAmbiente, floja,
         color1, color2, color3, color4) = ret

        create_grafs(data_inicio, data_fim, fVendedor, fLiberador, fAmbiente, floja,
                     color1, color2, color3, color4)

if __name__ == "__main__":
    main()
