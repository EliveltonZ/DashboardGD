import streamlit as st
import pandas as pd
import yfinance as yf

st.set_page_config(layout='wide',
                   page_title = "Dashboard",
                   initial_sidebar_state='expanded', 
                   menu_items={
                       'Get Help': 'http://meusite.com.br',
                       'Report a bug': 'http://meuoutrosite.com.br',
                       'about': 'Esse app foi desenvolvido por Elivelton Gonzaga'
                   }
                   )

with st.sidebar:
    st.write('teste')
    
st.write("""# Bolsa de Valores""")

def load_data(enterprise) -> pd.DataFrame:
    dados = yf.Ticker(enterprise)
    dados_acao = dados.history(period='1d', start='2010-01-01', end='2024-07-01')
    dados_acao = dados_acao[['Close']]
    return dados_acao

dados = load_data('ITUB4.SA')
st.line_chart(dados)