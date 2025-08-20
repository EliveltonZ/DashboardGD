from typing import Literal
import pandas as pd
import streamlit as st
import pyodbc  # mantido por compatibilidade, não é usado com Supabase
from supabase import create_client, Client
import os

# @st.cache_data
def database(db_file, query, password=None) -> pd.DataFrame:
    """
    Lê dados do Supabase (Postgres) e retorna um DataFrame com as colunas necessárias.
    Mantém o NOME e a ASSINATURA originais para não quebrar seu código.
    Ignora db_file/query/password.
    """
    sb = st.secrets.get("supabase", {})
    url = sb.get("url")
    key = sb.get("key")
    if not url or not key:
        raise RuntimeError(
            "Defina SUPABASE_URL e SUPABASE_KEY nas variáveis de ambiente."
        )

    cli: Client = create_client(url, key)

    # Colunas necessárias do seu SELECT original
    cols_proj = [
        "ordemdecompra","cliente","contrato","datacontrato","dataassinatura",
        "chegoufabrica","dataentrega","iniciado","pronto","entrega",
        "valorbruto","valornegociado"
    ]
    cols_prod = [
        "ordemdecompra",
        "corteinicio","cortefim",
        "customizacaoinicio","customizacaofim",
        "coladeirainicio","coladeirafim",
        "usinageminicio","usinagemfim",
        "montageminicio","montagemfim",
        "paineisinicio","paineisfim",
        "embalageminicio","embalagemfim"
    ]

    # Busca no Supabase (PostgREST). Ajuste nomes de colunas se na sua base estiverem diferentes.
    sel_proj = ",".join(cols_proj)
    sel_prod = ",".join(cols_prod)

    res_proj = cli.table("tblProjetos").select(sel_proj).execute()
    res_prod = cli.table("tblProducao").select(sel_prod).execute()

    df_proj = pd.DataFrame(res_proj.data or [])
    df_prod = pd.DataFrame(res_prod.data or [])

    if df_proj.empty or df_prod.empty:
        return pd.DataFrame(columns=cols_proj + cols_prod[1:])  # DataFrame vazio compatível

    # Join por OrdemdeCompra (INNER JOIN como no seu SQL)
    df = df_prod.merge(df_proj, on="ordemdecompra", how="inner")

    return df

sql = "SELECT tblProjetos.ordemdecompra, tblProjetos.cliente, tblProjetos.contrato, tblProjetos.datacontrato, tblProjetos.dataassinatura, tblProjetos.chegoufabrica, tblProjetos.dataentrega, tblProjetos.iniciado, tblProjetos.pronto, tblProjetos.entrega, tblProjetos.valorbruto, tblProjetos.valornegociado, tblProducao.corteinicio, tblProducao.cortefim, tblProducao.customizacaoinicio, tblProducao.customizacaofim, tblProducao.coladeirainicio, tblProducao.coladeirafim, tblProducao.usinageminicio, tblProducao.usinagemfim, tblProducao.montageminicio, tblProducao.montagemfim, tblProducao.paineisinicio, tblProducao.paineisfim, tblProducao.embalageminicio, tblProducao.embalagemfim FROM tblProducao INNER JOIN tblProjetos ON tblProducao.OrdemdeCompra = tblProjetos.OrdemdeCompra;"

# Função para calcular a duração trabalhada
def calcular_duracao_trabalhada(inicio, fim) -> float | Literal[0]:
    hour_inicio = 7
    min_inicio = 30

    hour_final = 16
    min_final = 30

    # Definições de horário de trabalho
    jornada_inicio = pd.Timestamp(year=1900, month=1, day=1, hour=hour_inicio, minute=min_inicio)
    jornada_fim = pd.Timestamp(year=1900, month=1, day=1, hour=hour_final, minute=min_final)

    def ajustar_data(data: pd.Timestamp) -> pd.Timestamp | None:
        if pd.isnull(data):
            return None
        if data.weekday() >= 5:  # sábado/domingo
            return None
        if data.time() < jornada_inicio.time():
            data = data.replace(hour=hour_inicio, minute=min_inicio)
        elif data.time() > jornada_fim.time():
            data = data.replace(hour=hour_final, minute=min_final)
        return data

    inicio = ajustar_data(inicio)
    fim = ajustar_data(fim)

    if not inicio or not fim:
        return 0

    horas_trabalhadas = 0
    while inicio < fim:
        if inicio.weekday() < 5:
            if inicio.time() < jornada_inicio.time():
                inicio = inicio.replace(hour=hour_inicio, minute=min_inicio)
            if fim.time() > jornada_fim.time():
                fim = fim.replace(hour=hour_final, minute=min_final)
            if inicio < fim:
                horas_no_dia = (min(fim, inicio.replace(hour=hour_final, minute=min_final)) - inicio).total_seconds() / 3600
                horas_trabalhadas += horas_no_dia
        inicio = inicio + pd.DateOffset(days=1)
        inicio = inicio.replace(hour=hour_inicio, minute=min_inicio)
    return horas_trabalhadas

# Passo 2: Definir a função decimal_to_hours
def decimal_to_hours(decimal_hours):
    if pd.isna(decimal_hours):
        return None
    hours = int(decimal_hours)
    minutes = int((decimal_hours - hours) * 60)
    return f"{hours:02d}:{minutes:02d}"

# Ler dados (agora do Supabase)
df = database('\\\\GDD02\\sistema\\BD_Geracao.accdb', sql, '1')

def filtrar(df:pd.DataFrame, inicio: str, fim: str):
    # garante comparação em datetime
    di = pd.to_datetime(inicio)
    df_ = pd.to_datetime(fim)
    df_filtrado = df[(pd.to_datetime(df['corteinicio']) >= di) & (pd.to_datetime(df['cortefim']) <= df_)]
    return df_filtrado

# Converter colunas de datas/horas para datetime
for col in [
    'corteinicio','cortefim',
    'customizacaoinicio','customizacaofim',
    'coladeirainicio','coladeirafim',
    'usinageminicio','usinagemfim',
    'montageminicio','montagemfim',
    'paineisinicio','paineisfim',
    'embalageminicio','embalagemfim'
]:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors='coerce')

df = filtrar(df, '2024-01-01', '2024-12-01')

# Calcular a duração trabalhada para cada fase
df['DuraçãocorteHoras'] = df.apply(lambda row: calcular_duracao_trabalhada(row['corteinicio'], row['cortefim']), axis=1)
df['DuraçãocustomizacaoHoras'] = df.apply(lambda row: calcular_duracao_trabalhada(row['customizacaoinicio'], row['customizacaofim']), axis=1)
df['DuraçãocoladeiraHoras'] = df.apply(lambda row: calcular_duracao_trabalhada(row['coladeirainicio'], row['coladeirafim']), axis=1)
df['DuraçãousinagemHoras'] = df.apply(lambda row: calcular_duracao_trabalhada(row['usinageminicio'], row['usinagemfim']), axis=1)
df['DuraçãomontagemHoras'] = df.apply(lambda row: calcular_duracao_trabalhada(row['montageminicio'], row['montagemfim']), axis=1)
df['DuraçãopaineisHoras'] = df.apply(lambda row: calcular_duracao_trabalhada(row['paineisinicio'], row['paineisfim']), axis=1)
df['DuraçãoembalagemHoras'] = df.apply(lambda row: calcular_duracao_trabalhada(row['embalageminicio'], row['embalagemfim']), axis=1)

total_projetos_periodo = df['OrdemdeCompra'].nunique() if 'OrdemdeCompra' in df.columns else len(df)

# Calcular a média por etapa (em hh:mm e decimal)
def _safe_mean(series: pd.Series, n: int) -> float:
    return (series.sum() / n) if n else 0.0

media_intervalo_duracoes = {
    'corte':         decimal_to_hours(_safe_mean(df['DuraçãocorteHoras'], total_projetos_periodo)),
    'customizacao':  decimal_to_hours(_safe_mean(df['DuraçãocustomizacaoHoras'], total_projetos_periodo)),
    'coladeira':     decimal_to_hours(_safe_mean(df['DuraçãocoladeiraHoras'], total_projetos_periodo)),
    'usinagem':      decimal_to_hours(_safe_mean(df['DuraçãousinagemHoras'], total_projetos_periodo)),
    'montagem':      decimal_to_hours(_safe_mean(df['DuraçãomontagemHoras'], total_projetos_periodo)),
    'paineis':       decimal_to_hours(_safe_mean(df['DuraçãopaineisHoras'], total_projetos_periodo)),
    'embalagem':     decimal_to_hours(_safe_mean(df['DuraçãoembalagemHoras'], total_projetos_periodo)),
}

media_intervalo_duracoes_teste = {
    'corte':        _safe_mean(df['DuraçãocorteHoras'], total_projetos_periodo),
    'customizacao': _safe_mean(df['DuraçãocustomizacaoHoras'], total_projetos_periodo),
    'coladeira':    _safe_mean(df['DuraçãocoladeiraHoras'], total_projetos_periodo),
    'usinagem':     _safe_mean(df['DuraçãousinagemHoras'], total_projetos_periodo),
    'montagem':     _safe_mean(df['DuraçãomontagemHoras'], total_projetos_periodo),
    'paineis':      _safe_mean(df['DuraçãopaineisHoras'], total_projetos_periodo),
    'embalagem':    _safe_mean(df['DuraçãoembalagemHoras'], total_projetos_periodo),
}

# Criar DataFrame de médias
df_media_intervalo = pd.DataFrame(list(media_intervalo_duracoes_teste.items()), columns=['Etapa', 'HorasDecimal'])
df_media_intervalo['Percentual'] = ((df_media_intervalo['HorasDecimal'] / df_media_intervalo['HorasDecimal'].sum()) * 100).round(1)
df_media_intervalo['%'] = df_media_intervalo['Percentual'].astype(str) + '%'
df_media_intervalo['Media'] = list(media_intervalo_duracoes.values())
