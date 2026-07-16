import streamlit as st
from supabase import create_client, Client


@st.cache_resource(show_spinner=False)
def get_supabase_client() -> Client:
    """Cria (e cacheia) o cliente Supabase compartilhado por todos os dashboards."""
    cfg = st.secrets.get("supabase", {})
    url = cfg.get("url")
    key = cfg.get("service_role_key") or cfg.get("anon_key") or cfg.get("key")
    if not url or not key:
        raise RuntimeError(
            "Defina 'supabase.url' e uma chave ('key'/'anon_key'/'service_role_key') em st.secrets['supabase']."
        )
    return create_client(url, key)
