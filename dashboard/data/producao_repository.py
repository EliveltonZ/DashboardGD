import re

import pandas as pd

from dashboard.data.client import get_supabase_client


class ProducaoSqlRepository:
    """Executa SQL arbitrário via RPC exec_sql no Supabase (dashboard de Produção)."""

    @staticmethod
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

    @staticmethod
    def _strip_leading_comments_spaces(s: str) -> str:
        return re.sub(r'^(?:--[^\n]*\n|\s+|/\*.*?\*/)+', '', s, flags=re.S)

    @classmethod
    def _trim_trailing_semicolons(cls, sql: str) -> str:
        return sql.rstrip().rstrip(';').rstrip()

    @classmethod
    def _force_select_prefix(cls, sql: str) -> str:
        """Se começar com WITH, embrulha em SELECT * FROM (...) t."""
        s = cls._strip_leading_comments_spaces(sql.lstrip())
        head = s[:8].lower()
        if head.startswith('select'):
            return sql
        if head.startswith('with'):
            return f"SELECT * FROM (\n{sql}\n) t"
        return sql

    @classmethod
    def query(cls, sql: str, params: dict | None = None) -> pd.DataFrame:
        client = get_supabase_client()
        sql = cls._bind_params(sql, params)
        sql = cls._trim_trailing_semicolons(sql)
        sql = cls._force_select_prefix(sql)

        resp = client.rpc("exec_sql", {"q": sql}).execute()
        rows = resp.data or []
        norm = [r.get("exec_sql", r) for r in rows]
        return pd.DataFrame(norm)


class ProducaoJoinRepository:
    """Busca dados brutos de tblProjetos + tblProducao via select direto (estatísticas de duração)."""

    COLS_PROJ = [
        "ordemdecompra", "contrato", "datacontrato", "dataassinatura",
        "chegoufabrica", "dataentrega", "iniciado", "pronto", "entrega",
        "valorbruto", "valornegociado",
    ]
    COLS_PROD = [
        "ordemdecompra",
        "corteinicio", "cortefim",
        "customizacaoinicio", "customizacaofim",
        "coladeirainicio", "coladeirafim",
        "usinageminicio", "usinagemfim",
        "montageminicio", "montagemfim",
        "paineisinicio", "paineisfim",
        "embalageminicio", "embalagemfim",
    ]

    @classmethod
    def fetch_joined(cls) -> pd.DataFrame:
        """Busca e faz o JOIN de tblProjetos + tblProducao. Sem cache: dados sempre atualizados."""
        cli = get_supabase_client()
        df_proj = pd.DataFrame(
            cli.table("tblProjetos").select(",".join(cls.COLS_PROJ)).execute().data or []
        )
        df_prod = pd.DataFrame(
            cli.table("tblProducao").select(",".join(cls.COLS_PROD)).execute().data or []
        )

        if df_proj.empty or df_prod.empty:
            return pd.DataFrame(columns=cls.COLS_PROJ + cls.COLS_PROD[1:])

        df = df_prod.merge(df_proj, on="ordemdecompra", how="inner")

        # Mantém compatibilidade com 'OrdemdeCompra' se o restante do código usar
        if "ordemdecompra" in df.columns and "OrdemdeCompra" not in df.columns:
            df["OrdemdeCompra"] = df["ordemdecompra"]

        return df
