import pandas as pd
import streamlit as st

from dashboard.data.client import get_supabase_client

_COLUNAS_ESPERADAS = ['ordemdecompra', 'pronto', 'vendedor', 'liberador', 'tipoambiente', 'loja']

class ProjetosRepository:
    """Acesso a dados da tabela tblProjetos no Supabase (usado por Projetos, Financeiro e Fábrica)."""

    @staticmethod
    @st.cache_data(ttl=300, show_spinner=False)
    def _fetch_clientes() -> pd.DataFrame:
        """Busca o cadastro oficial de clientes (id, name) usado para resolver o nome do cliente."""
        cli = get_supabase_client()
        res = cli.table("tblClientes").select("id, name").execute()
        return pd.DataFrame(res.data or [])

    @staticmethod
    def _resolver_cliente(df: pd.DataFrame) -> pd.DataFrame:
        """
        Substitui a coluna 'cliente' (texto solto em tblProjetos) pelo nome oficial em
        tblClientes, via inner join por id_cliente. Não há FK declarada no banco entre
        as duas tabelas, então o join é feito aqui (client-side) em vez de via PostgREST.
        """
        if 'id_cliente' not in df.columns:
            return df

        clientes = ProjetosRepository._fetch_clientes()
        if clientes.empty:
            return df

        clientes = clientes.rename(columns={'id': 'id_cliente', 'name': 'cliente'})
        df = df.drop(columns=['cliente'], errors='ignore')
        return df.merge(clientes, on='id_cliente', how='inner')

    @staticmethod
    @st.cache_data(ttl=300, show_spinner=False)
    def _fetch_lojas() -> pd.DataFrame:
        """Busca o cadastro oficial de lojas (id, name) usado para resolver o nome da loja."""
        cli = get_supabase_client()
        res = cli.table("tblLoja").select("id, name").execute()
        return pd.DataFrame(res.data or [])

    @staticmethod
    def _resolver_loja(df: pd.DataFrame) -> pd.DataFrame:
        """
        Substitui a coluna 'loja' (texto solto em tblProjetos) pelo nome oficial em
        tblLoja, via inner join por id_loja. Não há FK declarada no banco entre
        as duas tabelas, então o join é feito aqui (client-side) em vez de via PostgREST.
        """
        if 'id_loja' not in df.columns:
            return df

        lojas = ProjetosRepository._fetch_lojas()
        if lojas.empty:
            return df

        lojas = lojas.rename(columns={'id': 'id_loja', 'name': 'loja'})
        df = df.drop(columns=['loja'], errors='ignore')
        return df.merge(lojas, on='id_loja', how='inner')

    @staticmethod
    @st.cache_data(ttl=300, show_spinner=False)
    def fetch_all() -> pd.DataFrame:
        """Busca todos os projetos e garante que as colunas usadas nos filtros sempre existam."""
        cli = get_supabase_client()
        res = cli.table("tblProjetos").select("*").execute()
        df = pd.DataFrame(res.data or [])

        for col in _COLUNAS_ESPERADAS:
            if col not in df.columns:
                df[col] = pd.NA

        if 'valornegociado' in df.columns:
            df['valornegociado'] = pd.to_numeric(df['valornegociado'], errors='coerce')

        df = ProjetosRepository._resolver_cliente(df)
        df = ProjetosRepository._resolver_loja(df)

        return df
