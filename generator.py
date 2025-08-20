from datetime import datetime, timedelta
from typing import Dict, Tuple, Iterable, Optional

BR_FMT = "%d/%m/%Y %H:%M:%S"

def parse_dt(dt: str | datetime, fmt: str = BR_FMT) -> datetime:
    if isinstance(dt, datetime):
        return dt
    return datetime.strptime(dt, fmt)

def format_dt(dt: datetime, fmt: str = BR_FMT) -> str:
    return dt.strftime(fmt)

class Generator:
    def __init__(
        self,
        list_columns_initial: Optional[Iterable[str]] = None,
        work_start_h: int = 7, work_start_m: int = 30,
        work_end_h: int = 16, work_end_m: int = 30,
        workdays: Iterable[int] = (0,1,2,3,4),  # 0=Mon ... 6=Sun
        now: Optional[datetime] = None,
    ) -> None:
        self.list_columns_initial = list(list_columns_initial or [])
        # mapa de durações para colunas de FIM (minúsculas)
        self.list_columns_final: Dict[str, Tuple[int,int]] = {
            'cortefim': (4, 30),
            'customizacaofim': (5, 26),
            'coladeirafim': (4, 9),
            'usinagemfim': (8, 52),
            'paineisfim': (7, 51),
            'montagemfim': (12, 29),
            'embalagemfim': (4, 42),
        }
        self.work_start_h = work_start_h
        self.work_start_m = work_start_m
        self.work_end_h   = work_end_h
        self.work_end_m   = work_end_m
        self.workdays     = set(workdays)
        self.current_dt: datetime = now or datetime.today()

    # --- API principal (strings in/out para manter compatibilidade) ---
    def fill_mean_time(self, col: str) -> str:
        """Se for coluna de fim, soma a duração média; caso contrário retorna a data atual."""
        key = col.lower()
        if key in self.list_columns_final:
            h, m = self.list_columns_final[key]
            dt = self._add_business_time(self.current_dt, h, m)
            return format_dt(dt)
        return format_dt(self.current_dt)

    def last_date(self, date: str) -> str:
        """Atualiza a 'current_dt' para a última célula + 1 minuto (evitar colisão)."""
        base = parse_dt(date)
        self.current_dt = base + timedelta(minutes=1)
        return format_dt(self.current_dt)

    # --- Helpers internos (datetime in/out) ---
    def _add_business_time(self, start: datetime, hours: int, minutes: int) -> datetime:
        total_minutes = int(hours) * 60 + int(minutes)
        dt = start

        # se antes do expediente, pula para início; se após, vai para próximo dia útil 07:30
        dt = self._normalize_to_business_window(dt, move_to_next_if_after=True)

        while total_minutes > 0:
            # se não for dia útil, pula para próximo dia útil 07:30
            if dt.weekday() not in self.workdays:
                dt = self._next_business_day_start(dt)
                continue

            # (re)define limites do expediente PARA O DIA ATUAL
            day_start = dt.replace(hour=self.work_start_h, minute=self.work_start_m, second=0, microsecond=0)
            day_end   = dt.replace(hour=self.work_end_h,   minute=self.work_end_m,   second=0, microsecond=0)

            # garante dt >= início do expediente
            if dt < day_start:
                dt = day_start

            # minutos disponíveis hoje
            disponivel_td = day_end - dt
            disponivel_min = max(0, int(disponivel_td.total_seconds() // 60))

            if total_minutes <= disponivel_min:
                dt = dt + timedelta(minutes=total_minutes)
                total_minutes = 0
            else:
                # gasta o dia e vai para o próximo útil
                dt = self._next_business_day_start(dt)
                total_minutes -= disponivel_min

        return dt

    def _normalize_to_business_window(self, dt: datetime, move_to_next_if_after: bool = False) -> datetime:
        day_start = dt.replace(hour=self.work_start_h, minute=self.work_start_m, second=0, microsecond=0)
        day_end   = dt.replace(hour=self.work_end_h,   minute=self.work_end_m,   second=0, microsecond=0)

        # fim de semana -> vai para próximo dia útil 07:30
        if dt.weekday() not in self.workdays:
            return self._next_business_day_start(dt)

        if dt < day_start:
            return day_start
        if dt > day_end and move_to_next_if_after:
            return self._next_business_day_start(dt)
        return dt

    def _next_business_day_start(self, dt: datetime) -> datetime:
        # vai para manhã do dia seguinte até cair em um dia útil
        dt = (dt + timedelta(days=1)).replace(hour=self.work_start_h, minute=self.work_start_m, second=0, microsecond=0)
        while dt.weekday() not in self.workdays:
            dt = (dt + timedelta(days=1)).replace(hour=self.work_start_h, minute=self.work_start_m, second=0, microsecond=0)
        return dt
