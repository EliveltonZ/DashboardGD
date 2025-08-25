import streamlit as st
from streamlit_option_menu import option_menu
from streamlit_js_eval import streamlit_js_eval

st.set_page_config(layout='wide',
                   page_title = "Dashboard",
                   initial_sidebar_state='expanded', 
                   menu_items={
                       'Get Help': 'http://meusite.com.br',
                       'Report a bug': 'http://meuoutrosite.com.br',
                       'about': 'Esse app foi desenvolvido por Elivelton Gonzaga'
                   }
                   )

st.markdown(
    """
    <style>
    .block-container {
        padding: 1.9rem 4rem; 
    }

    [data-testid="stSidebar"] {
        zoom: 0.85;
    }

    </style>
    """,
    unsafe_allow_html=True
)

with st.sidebar:

    st.image('GD.png')
    selected = option_menu(
        menu_title = "Dashboard",
        options = ["Projetos", "Produção", "Financeiro"],
        icons=["house", "bookmark", "currency-dollar"],
        menu_icon='cast',
        styles={
            "icon": {"color": "white"}
        })

    if selected == "Projetos":
        import dash_projetos
        filtros = dash_projetos.loading_json()
        t = dash_projetos.create_sidebar(*filtros)

    elif selected == "Produção":
        import dash_producao
        te = dash_producao.create_sidebar()
    
    elif selected == "Financeiro":
        import dash_financeiro
        filtros = dash_financeiro.loading_json()
        t = dash_financeiro.create_sidebar(*filtros)

if selected == "Projetos":
    dash_projetos.create_grafs(*t)

elif selected == "Produção":
    dash_producao.create_grafs(*te)

elif selected == "Financeiro":
    dash_financeiro.create_grafs(*t)
    
    


