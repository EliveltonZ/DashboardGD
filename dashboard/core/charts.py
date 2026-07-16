import altair as alt
import pandas as pd
import streamlit as st
from babel.numbers import format_currency, format_decimal


# Cor de fundo usada na parada inicial dos gradientes em tema escuro/claro
_GRADIENT_BASE_DARK = '#0E1117'
_GRADIENT_BASE_LIGHT = '#f0f2f6'


class Chart:
    """Encapsula a criação de gráficos Altair renderizados via Streamlit."""

    def __init__(self, dataframe: pd.DataFrame):
        self.df = dataframe
        self.result = dataframe

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    def _gradient_base(self, label_theme: str | None) -> str:
        """Retorna a cor de fundo do gradiente de acordo com o tema atual."""
        return _GRADIENT_BASE_DARK if label_theme == 'dark' else _GRADIENT_BASE_LIGHT

    def _label_color(self, label_theme: str | None) -> str:
        """Retorna a cor do texto dos rótulos de acordo com o tema atual."""
        return 'white' if label_theme == 'dark' else 'black'

    def _agregar(self, coluna: str, coluna_valor: str, agg: str) -> pd.DataFrame:
        """Agrega o DataFrame por `coluna` usando 'count' ou 'sum' em `coluna_valor`."""
        if agg == 'count':
            resultado = self.df.groupby([coluna], as_index=False).count()
        elif agg == 'sum':
            resultado = self.df.groupby(coluna)[coluna_valor].sum().reset_index()
        else:
            raise ValueError(f"Agregação '{agg}' não suportada. Use 'count' ou 'sum'.")
        return resultado[[coluna, coluna_valor]]

    def _make_gradient(self, color: str, orient: str, label_theme: str | None) -> alt.Gradient:
        """Cria um gradiente linear da cor de fundo do tema até `color`."""
        base = self._gradient_base(label_theme)
        if orient == 'vertical':
            return alt.Gradient(
                gradient='linear',
                stops=[alt.GradientStop(color=base, offset=0), alt.GradientStop(color=color, offset=1)],
                x1=1, x2=1, y1=1, y2=0,
            )
        return alt.Gradient(
            gradient='linear',
            stops=[alt.GradientStop(color=base, offset=0), alt.GradientStop(color=color, offset=1)],
            x1=1, x2=0, y1=0, y2=1,
        )

    def convert_value(self, number: float, *, currency=False) -> str:
        """Formata um número como moeda BRL ou número decimal no locale pt_BR."""
        if currency:
            return format_currency(number, 'BRL', locale='pt_BR')
        return format_decimal(number, locale='pt_BR')

    # ------------------------------------------------------------------
    # Dados agregados (exposto para uso externo se necessário)
    # ------------------------------------------------------------------

    def dados(self, column: str, column_value: str, agg: str = 'count') -> pd.DataFrame:
        """Retorna DataFrame agregado — wrapper público de _agregar."""
        return self._agregar(column, column_value, agg)

    # ------------------------------------------------------------------
    # Gráficos
    # ------------------------------------------------------------------

    def bar(self,
            x: str,
            y: str,
            aggregation: str = 'count',
            color: str = '#0276D2',
            title_x: str | None = None,
            title_y: str = 'Total',
            line_mean: bool = False,
            orient: str = 'vertical',
            group_by: bool = True,
            nlargest: bool | int = False,
            label_theme: str | None = None):
        """Renderiza um gráfico de barras (vertical ou horizontal) com gradiente e rótulos."""
        if x not in self.df.columns:
            st.error(f"A coluna '{x}' não existe no DataFrame.")
            return

        if group_by:
            self.result = self._agregar(x, y, agg=aggregation)
            if nlargest:
                top_n = nlargest if isinstance(nlargest, int) else 5
                self.result = self.result.nlargest(top_n, y)
        else:
            self.result = self.df

        max_y = self.result[y].max()
        y_domain = [0, max_y * 1.10]
        gradient = self._make_gradient(color, orient, label_theme)

        if orient == 'vertical':
            bar = alt.Chart(self.result).mark_bar(
                cornerRadiusTopLeft=5, cornerRadiusTopRight=5, color=gradient
            ).encode(
                x=alt.X(x, title=title_x),
                y=alt.Y(y, title=title_y, scale=alt.Scale(domain=y_domain), axis=alt.Axis(format=',.0f')),
            )
        elif orient == 'horizontal':
            bar = alt.Chart(self.result).mark_bar(
                width=100, cornerRadiusTopLeft=5, cornerRadiusTopRight=5, color=gradient
            ).encode(
                x=alt.X(y, title=title_y, scale=alt.Scale(domain=y_domain)),
                y=alt.Y(x, title=title_x),
                tooltip=[alt.Tooltip(field=x, type='nominal'),
                         alt.Tooltip(field=y, type='quantitative', title='Total', format=',.0f')],
            ).properties(height=300)
        else:
            st.error(f"Orientação '{orient}' não suportada. Use 'vertical' ou 'horizontal'.")
            return

        label = bar.mark_text(dy=-6, color=self._label_color(label_theme)).encode(
            text=alt.Text(y, format=',.0f'),
            tooltip=[alt.Tooltip(field=x, type='nominal'),
                     alt.Tooltip(field=y, type='quantitative', title='Total', format=',.0f')],
        )

        if line_mean:
            mean_y = self.result[y].mean()
            rule = alt.Chart(pd.DataFrame({'mean': [mean_y]})).mark_rule(color='red').encode(
                y=alt.Y('mean:Q') if orient == 'vertical' else alt.X('mean:Q')  # type: ignore
            )
            return st.altair_chart(bar + label + rule, use_container_width=True)  # type: ignore

        return st.altair_chart(bar + label, use_container_width=True)  # type: ignore

    def line(self,
             x: str, y: str,
             aggregation: str = 'count',
             color: str = '#0276D2',
             title_x: str | None = None,
             title_y: str = 'Total',
             label_theme: str | None = None):
        """Renderiza um gráfico de linha simples com rótulos de valor."""
        if x not in self.df.columns:
            st.error(f"A coluna '{x}' não existe no DataFrame.")
            return

        self.result = self._agregar(x, y, agg=aggregation)
        line = alt.Chart(self.result).mark_line(color=color).encode(
            x=alt.X(x, title=title_x),
            y=alt.Y(y, title=title_y),
        )
        label = line.mark_text(dy=-15, color=self._label_color(label_theme)).encode(
            text=alt.Text(y, format=',.0f')
        )
        return st.altair_chart(line + label, use_container_width=True)  # type: ignore

    def area_gradient(self,
                      x: str, y: str,
                      aggregation: str = 'count',
                      color: str = '#0276D2',
                      title_x: str | None = None,
                      title_y: str = 'Total',
                      line_mean: bool = False,
                      label_theme: str | None = None):
        """Renderiza um gráfico de área com gradiente e linha de média opcional."""
        if x not in self.df.columns:
            st.error(f"A coluna '{x}' não existe no DataFrame.")
            return

        self.result = self._agregar(x, y, agg=aggregation)
        max_y = self.result[y].max()
        y_domain = [0, max_y * 1.10]
        base = self._gradient_base(label_theme)

        area = alt.Chart(self.result).mark_area(
            interpolate='linear', point=True,
            line={'color': color},
            color=alt.Gradient(
                gradient='linear',
                stops=[alt.GradientStop(color=base, offset=0), alt.GradientStop(color=color, offset=1)],
                x1=1, x2=1, y1=1, y2=0,
            ),
        ).encode(
            x=alt.X(x, title=title_x),
            y=alt.Y(y, title=title_y, scale=alt.Scale(domain=y_domain)),
        )
        label = area.mark_text(dy=-15, color=self._label_color(label_theme)).encode(
            text=alt.Text(y, format=',.0f')
        )

        if line_mean:
            mean_y = self.result[y].mean()
            rule = alt.Chart(pd.DataFrame({'mean': [mean_y]})).mark_rule(color='yellow').encode(
                y=alt.Y('mean:Q')
            )
            return st.altair_chart(area + label + rule, use_container_width=True)  # type: ignore

        return st.altair_chart(area + label, use_container_width=True)  # type: ignore

    def area(self,
             x: str, y: str,
             aggregation: str = 'count',
             color: str = '#0276D2',
             title_x: str | None = None,
             title_y: str = 'Total',
             label_theme: str | None = None):
        """Renderiza um gráfico de área sólida com rótulos de valor."""
        if x not in self.df.columns:
            st.error(f"A coluna '{x}' não existe no DataFrame.")
            return

        self.result = self._agregar(x, y, agg=aggregation)
        area = alt.Chart(self.result).mark_area(color=color).encode(
            x=alt.X(x, title=title_x),
            y=alt.Y(y, title=title_y),
        )
        label = area.mark_text(dy=-15, color=self._label_color(label_theme)).encode(
            text=alt.Text(y, format=',.0f')
        )
        return st.altair_chart(area + label, use_container_width=True)  # type: ignore

    def circle(self,
               x: str, y: str,
               aggregation: str = 'count',
               innerRadius: int = 0, outerRadius: int = 0, cornerRadius: int = 0,
               range_colors: str | list = 'category',
               type_y: str = 'quantitative',
               group_by: bool = True,
               title_x: str | None = None,
               title_y: str | None = None,
               label_theme: str | None = None):
        """Renderiza um gráfico de arco (pizza / donut) com rótulos externos."""
        if x not in self.df.columns:
            st.error(f"A coluna '{x}' não existe no DataFrame.")
            return

        self.result = self._agregar(x, y, agg=aggregation) if group_by else self.df
        arc = alt.Chart(self.result).mark_arc(
            cornerRadius=cornerRadius, innerRadius=innerRadius, outerRadius=outerRadius,
            stroke='rgba(255, 255, 255, 0.2)', strokeWidth=5,
        ).encode(
            theta=alt.Theta(field=y, type=type_y, stack=True, title=title_x),  # type: ignore
            color=alt.Color(field=x, type='nominal', title=title_y).scale(range=range_colors),
            tooltip=[alt.Tooltip(field=x, type='nominal'),
                     alt.Tooltip(field=y, type='quantitative', format=',.0f', title='Total')],
        )

        if title_y:
            label = arc.mark_text(radius=outerRadius + 20, size=13,
                                  color=self._label_color(label_theme)).encode(text=title_y)
        else:
            label = arc.mark_text(dx=5, dy=10, radius=outerRadius + 30, size=13,
                                  color=self._label_color(label_theme)).encode(
                text=alt.Text(y, format=',.0f')
            )
        return st.altair_chart(arc + label, use_container_width=True)  # type: ignore

    def circle_radial(self,
                      x: str, y: str,
                      aggregation: str = 'count',
                      color: str = '#0276D2',
                      innerRadius: int = 80, outerRadius: int = 140,
                      group_by: bool = True,
                      label_theme: str | None = None):
        """Renderiza um gráfico de arco radial onde o raio representa o valor."""
        if x not in self.df.columns:
            st.error(f"A coluna '{x}' não existe no DataFrame.")
            return

        self.result = self._agregar(x, y, agg=aggregation) if group_by else self.df
        arc = alt.Chart(self.result).mark_arc(
            innerRadius=innerRadius, outerRadius=outerRadius, color=color,
            stroke='rgb(14, 17, 23)', strokeWidth=4,
        ).encode(
            theta=alt.Theta(field=y, type='quantitative', stack=True),
            radius=alt.Radius(y, scale=alt.Scale(type='sqrt', zero=True, rangeMin=50)),
            color=alt.Color(field=x, type='nominal', title=x),
        )
        label = arc.mark_text(radiusOffset=15, size=14,
                              color=self._label_color(label_theme)).encode(
            text=alt.Text(y, format=',.0f')
        )
        return st.altair_chart(arc + label, use_container_width=True)  # type: ignore

    # ------------------------------------------------------------------
    # Auxiliares de métricas
    # ------------------------------------------------------------------

    def metric(self, x: str, y: str):
        """Retorna o valor da coluna `x` na linha com maior valor em `y`."""
        return self.result.sort_values(by=y, ascending=False).iloc[0][x]

    def top_max_value(self, x: str, y: str, top: int) -> list:
        """Retorna lista com os `top` maiores valores da coluna `x` ordenados por `y`."""
        return list(self.result.sort_values(by=y, ascending=False).iloc[:top][x])
