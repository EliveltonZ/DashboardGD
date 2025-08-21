import altair as alt
import pandas as pd
import streamlit as st
from babel.numbers import format_currency, format_decimal

class Graph:
    def __init__(self, dataframe: pd.DataFrame):
        self.df = dataframe
        self.result = dataframe  # evita attribute error

    # ========= Helpers =========
    def convert_value(self, number: float, *, currency=False):
        if currency:
            return format_currency(number, "BRL", locale="pt_BR")
        return format_decimal(number, locale="pt_BR")

    def _label_color(self, label_theme: str | None) -> str:
        """
        Recebe 'dark' | 'light' | None e retorna cor do texto.
        Sem detecção aqui: o módulo principal decide e passa pra cá.
        """
        if label_theme == "dark":
            return "white"
        return "black"  # default ou 'light'

    # ========= Dados =========
    def dados(self, column: str, column_value: str, agg: str = 'count') -> pd.DataFrame:
        if agg == 'count':
            data = self.df.groupby([column], as_index=False).count()
        elif agg == 'sum':
            data = self.df.groupby(column)[column_value].sum().reset_index()
        else:
            raise ValueError("Aggregation must be 'count' or 'sum'.")
        return data[[column, column_value]]

    # ========= Gráficos =========
    def bar_c(self,
        x: str,
        y: str,
        aggregation='count',
        color: str='#0276D2',
        title_x: str | None = None,
        title_y: str = 'Total',
        line_mean: bool = False,
        orient: str = 'vertical',
        range_colors: str | list = 'category',
        label_theme: str | None = None
    ):
        if x not in self.df.columns:
            st.error(f"A coluna '{x}' não existe no DataFrame.")
            return

        self.result = self.dados(x, y, agg=aggregation)
        max_y = self.result[y].max()
        y_domain = [0, max_y * 1.10]

        if orient == 'vertical':
            bar = alt.Chart(self.result).mark_bar(
                height=600, cornerRadiusTopLeft=5, cornerRadiusTopRight=5
            ).encode(
                x=alt.X(x, title=title_x),
                color=alt.Color(field=x, type='nominal', title=x, legend=None).scale(range=range_colors),
                y=alt.Y(y, title=title_y, scale=alt.Scale(domain=y_domain))
            )
        elif orient == 'horizontal':
            bar = alt.Chart(self.result).mark_bar(
                cornerRadiusTopLeft=5, cornerRadiusTopRight=5, color=alt.Gradient(
                    gradient='linear',
                    stops=[alt.GradientStop(color='#0E1117', offset=0),
                           alt.GradientStop(color=color, offset=1)],
                    x1=1, x2=0, y1=0, y2=1)
            ).encode(
                x=alt.X(y, title=title_y, scale=alt.Scale(domain=y_domain)),
                y=alt.Y(x, title=title_x)
            )
        else:
            st.error(f"Orientação '{orient}' não é suportada. Use 'vertical' ou 'horizontal'.")
            return

        label = bar.mark_text(dy=-6, color=self._label_color(label_theme)).encode(
            text=alt.Text(y, format=',.0f')
        )

        if line_mean:
            mean_y = self.result[y].mean()
            rule = alt.Chart(pd.DataFrame({'mean': [mean_y]})).mark_rule(color='red').encode(
                y=alt.Y('mean:Q') if orient == 'vertical' else alt.X('mean:Q')  # type: ignore
            )
            return st.altair_chart(bar + label + rule, use_container_width=True)  # type: ignore

        return st.altair_chart(bar + label, use_container_width=True)  # type: ignore

    def bar(self,
        x: str,
        y: str,
        aggregation='count',
        color: str='#0276D2',
        title_x: str | None = None,
        title_y: str = 'Total',
        line_mean: bool = False,
        orient: str = 'vertical',
        group_by: bool = True,
        nlargest=False,
        label_theme: str | None = None
    ):
        if x not in self.df.columns:
            st.error(f"A coluna '{x}' não existe no DataFrame.")
            return

        if group_by:
            self.result = self.dados(x, y, agg=aggregation)
            if nlargest:
                self.result = self.result.nlargest(5, y)
        else:
            self.result = self.df

        max_y = self.result[y].max()
        y_domain = [0, max_y * 1.10]

        if orient == 'vertical':
            bar = alt.Chart(self.result).mark_bar(
                cornerRadiusTopLeft=5, cornerRadiusTopRight=5, color=alt.Gradient(
                    gradient='linear',
                    stops=[alt.GradientStop(color='#0E1117', offset=0),
                           alt.GradientStop(color=color, offset=1)],
                    x1=1, x2=1, y1=1, y2=0)
            ).encode(
                x=alt.X(x, title=title_x),
                y=alt.Y(y, title=title_y, scale=alt.Scale(domain=y_domain), axis=alt.Axis(format=',.0f'))
            )
        elif orient == 'horizontal':
            bar = alt.Chart(self.result).mark_bar(
                width=100, cornerRadiusTopLeft=5, cornerRadiusTopRight=5, color=alt.Gradient(
                    gradient='linear',
                    stops=[alt.GradientStop(color='#0E1117', offset=0),
                           alt.GradientStop(color=color, offset=1)],
                    x1=1, x2=0, y1=0, y2=1)
            ).encode(
                x=alt.X(y, title=title_y, scale=alt.Scale(domain=y_domain)),
                y=alt.Y(x, title=title_x),
                tooltip=[alt.Tooltip(field=x, type='nominal'),
                         alt.Tooltip(field=y, type='quantitative', title='Total', format=',.0f')]
            ).properties(width=800, height=350)
        else:
            st.error(f"Orientação '{orient}' não é suportada. Use 'vertical' ou 'horizontal'.")
            return

        label = bar.mark_text(
            dy=-6, color=self._label_color(label_theme)
        ).encode(
            text=alt.Text(y, format=',.0f'),
            tooltip=[alt.Tooltip(field=x, type='nominal'),
                     alt.Tooltip(field=y, type='quantitative', title='Total', format=',.0f')]
        )

        if line_mean:
            mean_y = self.result[y].mean()
            rule = alt.Chart(pd.DataFrame({'mean': [mean_y]})).mark_rule(color='red').encode(
                y=alt.Y('mean:Q') if orient == 'vertical' else alt.X('mean:Q')  # type: ignore
            )
            return st.altair_chart(bar + label + rule, use_container_width=True)  # type: ignore

        return st.altair_chart(bar + label, use_container_width=True)  # type: ignore

    def line(self,
            x: str, y: str, aggregation='count',
            color: str='#0276D2', title_x: str | None=None, title_y: str='Total',
            label_theme: str | None = None):
        if x not in self.df.columns:
            st.error(f"A coluna '{x}' não existe no DataFrame.")
            return

        self.result = self.dados(x, y, agg=aggregation)
        line = alt.Chart(self.result).mark_line(color=color).encode(
            x=alt.X(x, title=title_x),
            y=alt.Y(y, title=title_y)
        )
        label = line.mark_text(dy=-15, color=self._label_color(label_theme)).encode(
            text=alt.Text(y, format=',.0f')
        )
        return st.altair_chart(line + label, use_container_width=True)  # type: ignore

    def area_gradient(self,
            x: str, y: str, aggregation='count',
            color: str='#0276D2', title_x: str | None=None, title_y: str='Total',
            line_mean: bool = False, label_theme: str | None = None):
        if x not in self.df.columns:
            st.error(f"A coluna '{x}' não existe no DataFrame.")
            return

        self.result = self.dados(x, y, agg=aggregation)
        max_y = self.result[y].max()
        y_domain = [0, max_y * 1.10]
        area_gradient = alt.Chart(self.result).mark_area(
            interpolate='linear', point=True,
            line={'color': color},
            color=alt.Gradient(
                gradient='linear',
                stops=[alt.GradientStop(color='#101010', offset=0),
                       alt.GradientStop(color=color, offset=1)],
                x1=1, x2=1, y1=1, y2=0
            )
        ).encode(
            x=alt.X(x, title=title_x),
            y=alt.Y(y, title=title_y, scale=alt.Scale(domain=y_domain))
        )
        label = area_gradient.mark_text(dy=-15, color=self._label_color(label_theme)).encode(
            text=alt.Text(y, format=',.0f')
        )
        if line_mean:
            mean_y = self.result[y].mean()
            rule = alt.Chart(pd.DataFrame({'mean': [mean_y]})).mark_rule(color='yellow').encode(
                y=alt.Y('mean:Q')
            )
            return st.altair_chart(area_gradient + label + rule, use_container_width=True)  # type: ignore

        return st.altair_chart(area_gradient + label, use_container_width=True)  # type: ignore

    def area(self,
            x: str, y: str, aggregation='count',
            color: str='#0276D2', title_x: str | None=None, title_y: str='Total',
            label_theme: str | None = None):
        if x not in self.df.columns:
            st.error(f"A coluna '{x}' não existe no DataFrame.")
            return

        self.result = self.dados(x, y, agg=aggregation)
        area = alt.Chart(self.result).mark_area(color=color).encode(
            x=alt.X(x, title=title_x),
            y=alt.Y(y, title=title_y)
        )
        label = area.mark_text(dy=-15, color=self._label_color(label_theme)).encode(
            text=alt.Text(y, format=',.0f')
        )
        return st.altair_chart(area + label, use_container_width=True)  # type: ignore

    def circle(self,
            x: str, y: str, aggregation='count',
            innerRadius=0, outerRadius=0, cornerRadius=0,
            range_colors: str | list = 'category',
            type_y='quantitative', group_by: bool = True,
            title_x=None, title_y=None, label_theme: str | None = None):
        if x not in self.df.columns:
            st.error(f"A coluna '{x}' não existe no DataFrame.")
            return

        self.result = self.dados(x, y, agg=aggregation) if group_by else self.df
        circle = alt.Chart(self.result).mark_arc(
            cornerRadius=cornerRadius, innerRadius=innerRadius, outerRadius=outerRadius,
            stroke="rgba(255, 255, 255, 0.2)", strokeWidth=5
        ).encode(
            theta=alt.Theta(field=y, type=type_y, stack=True, title=title_x),  # type: ignore
            color=alt.Color(field=x, type='nominal', title=title_y).scale(range=range_colors),
            tooltip=[alt.Tooltip(field=x, type='nominal'),
                     alt.Tooltip(field=y, type='quantitative', format=',.0f', title='Total')]
        )

        if title_y:
            label = circle.mark_text(radius=outerRadius + 20, size=13,
                                     color=self._label_color(label_theme)).encode(
                text=title_y
            )
        else:
            label = circle.mark_text(dx=5, dy=10, radius=outerRadius + 30, size=13,
                                     color=self._label_color(label_theme)).encode(
                text=alt.Text(y, format=',.0f')
            )
        return st.altair_chart(circle + label, use_container_width=True)  # type: ignore

    def circle_radial(self,
            x: str, y: str, aggregation='count',
            color: str='#0276D2', _innerRadius=80, _outerRadius=140,
            group_by: bool = True, label_theme: str | None = None):
        if x not in self.df.columns:
            st.error(f"A coluna '{x}' não existe no DataFrame.")
            return

        self.result = self.dados(x, y, agg=aggregation) if group_by else self.df
        circle = alt.Chart(self.result).mark_arc(
            innerRadius=_innerRadius, outerRadius=_outerRadius, color=color,
            stroke="rgb(14, 17, 23)", strokeWidth=4
        ).encode(
            theta=alt.Theta(field=y, type='quantitative', stack=True),
            radius=alt.Radius(y, scale=alt.Scale(type="sqrt", zero=True, rangeMin=50)),
            color=alt.Color(field=x, type='nominal', title=x)
        )
        label = circle.mark_text(radiusOffset=15, size=14,
                                 color=self._label_color(label_theme)).encode(
            text=alt.Text(y, format=',.0f')
        )
        return st.altair_chart(circle + label, use_container_width=True)  # type: ignore

    # ========= Auxiliares =========
    def max_value(self, x, y):
        max_df = self.result.sort_values(by=y, ascending=False)
        return max_df.iloc[0][x]

    def top_max_value(self, x: str, y: str, top: int):
        max_df = self.result.sort_values(by=y, ascending=False)
        return list(max_df.iloc[0:top][x])
