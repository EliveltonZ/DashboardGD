from json import dump, load


class Settings:
    """Gerencia leitura e escrita de preferências persistidas em Settings.json."""

    _CHAVES_FILTROS = ('data_inicial', 'data_final', 'cor_ambiente', 'cor_vendedor', 'cor_liberador', 'cor_periodo')

    def __init__(self, file_name: str = 'Settings.json') -> None:
        self._file_name = file_name
        with open(file_name, 'r') as f:
            self._data: dict = load(f)

    def key(self, key: str) -> str:
        """Retorna o valor associado à chave, ou string vazia se não existir."""
        return self._data.get(key, '')

    def update_key(self, key: str, value) -> None:
        """Atualiza uma chave em memória e persiste o arquivo Settings.json."""
        self._data[key] = value
        with open(self._file_name, 'w') as f:
            dump(self._data, f, indent=2)

    def load_filtros(self) -> tuple[str, str, str, str, str, str]:
        """Lê data inicial/final e as 4 cores usadas nos dashboards de Projetos/Financeiro/Fábrica."""
        return tuple(self.key(k) for k in self._CHAVES_FILTROS)  # type: ignore[return-value]

    def save_filtros(self, data_inicio, data_fim, cor_ambiente, cor_vendedor, cor_liberador, cor_periodo) -> None:
        """Persiste data inicial/final e as 4 cores."""
        valores = (data_inicio, data_fim, cor_ambiente, cor_vendedor, cor_liberador, cor_periodo)
        for chave, valor in zip(self._CHAVES_FILTROS, valores):
            self.update_key(chave, valor)

    def load_periodo(self) -> tuple[str, str]:
        """Lê apenas data inicial/final, usado nos filtros de estatística do dashboard de Produção."""
        return self.key('data_inicial'), self.key('data_final')
