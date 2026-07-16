import streamlit as st

_COMPACT_SIDEBAR_CSS = """
<style>
section[data-testid="stSidebar"] {
    font-size: 0.85rem;
}
section[data-testid="stSidebar"] label {
    font-size: 0.8rem;
    margin-bottom: 0.1rem;
}
section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] {
    gap: 0.4rem;
}
section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] {
    gap: 0.35rem;
}
section[data-testid="stSidebar"] div[data-testid="stForm"] {
    padding: 0.75rem 0.9rem;
    border-radius: 0.5rem;
}
section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
    min-height: 2rem;
    font-size: 0.8rem;
}
section[data-testid="stSidebar"] input {
    font-size: 0.8rem;
    padding: 0.25rem 0.5rem;
}
section[data-testid="stSidebar"] button {
    font-size: 0.8rem;
    padding: 0.25rem 0.7rem;
    min-height: 1.8rem;
}
section[data-testid="stSidebar"] .stMarkdown h3 {
    font-size: 0.95rem;
    margin: 0.4rem 0 0.2rem 0;
}
</style>
"""


def apply_compact_sidebar_style() -> None:
    """
    Injeta CSS para reduzir fonte/espaçamento dos widgets da sidebar (color picker,
    date input, selectbox, botões, formulário).

    Os seletores usam atributos data-testid/data-baseweb do Streamlit, que não são
    API pública — se uma futura versão do Streamlit renomeá-los, este ajuste
    simplesmente deixa de ter efeito, sem quebrar a aplicação.
    """
    st.markdown(_COMPACT_SIDEBAR_CSS, unsafe_allow_html=True)


_NO_PADDING_MAIN_CSS = """
<style>
div[data-testid="stAppViewContainer"] .block-container,
div[data-testid="stMainBlockContainer"] {
    padding-top: 1rem;
    padding-bottom: 0rem;
    padding-left: 2rem;
    padding-right: 2rem;
}
</style>
"""


def apply_no_padding_main_container_style() -> None:
    """
    Remove o padding do container principal que envolve os gráficos (esquerda,
    direita e embaixo). Mantém 1rem no topo para o conteúdo não ficar escondido
    atrás da barra de ferramentas fixa do Streamlit (menu/Deploy) — se quiser
    remover esse espaço também, é só zerar o padding-top aqui.
    """
    st.markdown(_NO_PADDING_MAIN_CSS, unsafe_allow_html=True)


def detect_theme_mode() -> str:
    """
    Detecta se o Streamlit está em tema escuro ou claro.
    Tenta via JS (streamlit-js-eval), depois via cor de fundo, e usa 'light' como padrão.
    """
    try:
        from streamlit_js_eval import streamlit_js_eval  # type: ignore
        mode = streamlit_js_eval(
            js_expressions="(window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) ? 'dark' : 'light'",
            key='__theme_mode__', want_output=True, default='light',
        )
        if mode in ('dark', 'light'):
            return mode
    except Exception:
        pass

    bg = st.get_option('theme.backgroundColor')
    if bg:
        s = bg.lstrip('#')
        if len(s) == 3:
            s = ''.join([c * 2 for c in s])
        try:
            r, g, b = [int(s[i:i + 2], 16) for i in (0, 2, 4)]
            lum = 0.2126 * (r / 255) ** 2.2 + 0.7152 * (g / 255) ** 2.2 + 0.0722 * (b / 255) ** 2.2
            return 'light' if lum > 0.5 else 'dark'
        except Exception:
            pass

    return 'light'
