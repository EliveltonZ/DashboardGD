import streamlit as st
from streamlit_option_menu import option_menu

from dashboard.core.settings import Settings
from dashboard.core.theme import apply_compact_sidebar_style, apply_no_padding_main_container_style
from dashboard.pages.fabrica_page import FabricaPage
from dashboard.pages.producao_page import ProducaoPage
from dashboard.pages.projetos_page import ProjetosPage

st.set_page_config(layout='wide',
                   page_title="Dashboard",
                   initial_sidebar_state='expanded',
                   menu_items={
                       'Get Help': 'http://meusite.com.br',
                       'Report a bug': 'http://meuoutrosite.com.br',
                       'about': 'Esse app foi desenvolvido por Elivelton Gonzaga'
                   }
                   )

apply_compact_sidebar_style()
apply_no_padding_main_container_style()

with st.sidebar:

    st.image('GD.png', width=140)
    selected = option_menu(
        menu_title="Dashboard",
        options=["Projetos", "Produção", "Financeiro"],
        icons=["house", "bookmark", "currency-dollar"],
        menu_icon='cast',
        styles={
            "container": {"padding": "0!important"},
            "icon": {"color": "white", "font-size": "14px"},
            "nav-link": {"font-size": "14px", "padding": "8px 10px", "margin": "2px 0"},
            "menu-title": {"font-size": "15px"},
        })

    if selected == "Projetos":
        projetos_page = ProjetosPage()
        filtros = Settings().load_filtros()
        resultado_projetos = projetos_page.render_sidebar(*filtros)

    elif selected == "Produção":
        producao_page = ProducaoPage()
        resultado_producao = producao_page.render_sidebar()

    elif selected == "Financeiro":
        fabrica_page = FabricaPage()
        filtros = Settings().load_filtros()
        resultado_fabrica = fabrica_page.render_sidebar(*filtros)


if selected == "Projetos":
    projetos_page.render(*resultado_projetos)

elif selected == "Produção":
    producao_page.render(*resultado_producao)

elif selected == "Financeiro":
    fabrica_page.render(*resultado_fabrica)
