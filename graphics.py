import altair as alt
import pandas as pd
import streamlit as st
import locale

class Graph():

    def __init__(self, dataframe: pd.DataFrame):
        self.df=dataframe
        locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')

    def convert_value(self, number: float):
        return locale.currency(number, symbol=True, grouping=True)

    def dados(self, column: str, column_value: str, agg: str = 'count') -> pd.DataFrame:
        """
        Agrupa o DataFrame por uma coluna específica e conta ou soma as ocorrências.
        """
        if agg == 'count':
            data = self.df.groupby([column], as_index=False).count()

        elif agg == 'sum':
            data = self.df.groupby(column)[column_value].sum().reset_index()

        else:
            raise ValueError("Aggregation must be 'count' or 'sum'.")

        result = data[[column, column_value]]
        return result

    def bar_c(self,
        x: str,
        y: str,
        aggregation = 'count',
        color: str='#0276D2',
        title_x: str | None = None,
        title_y: str = 'Total',
        line_mean: bool = False,
        orient: str = 'vertical',
        range_colors: str | list = 'category'
        ):

        if x in self.df.columns:
            self.result = self.dados(x, y, agg=aggregation)

            max_y = self.result[y].max()
            y_domain = [0, max_y * 1.10]

            if orient == 'vertical':
                bar = alt.Chart(self.result).mark_bar(height=600,
                    cornerRadiusTopLeft=5, cornerRadiusTopRight=5
                ).encode(
                    x=alt.X(x, title=title_x), color=alt.Color(field=x, type='nominal', title=x, legend=None).scale(range=range_colors),
                    y=alt.Y(y, title=title_y, scale=alt.Scale(domain=y_domain))
                )
            elif orient == 'horizontal':
                bar = alt.Chart(self.result).mark_bar(
                    cornerRadiusTopLeft=5, cornerRadiusTopRight=5, color=alt.Gradient(
                        gradient='linear',
                        stops=[alt.GradientStop(color='#0E1117', offset=0),
                            alt.GradientStop(color=color, offset=1)],
                        x1=1,
                        x2=0,
                        y1=0,
                        y2=1)
                ).encode(
                    x=alt.X(y, title=title_y, scale=alt.Scale(domain=y_domain)),
                    y=alt.Y(x, title=title_x)
                )
            else:
                st.error(f"Orientação '{orient}' não é suportada. Use 'vertical' ou 'horizontal'.")
                return

            label = bar.mark_text(dy=-6, color='white').encode(
                text=alt.Text(y, format=',.0f')
            )

            if line_mean:
                mean_y = (self.result[y].max() + self.result[y].min()) / 2
                rule = alt.Chart(pd.DataFrame({'mean': [mean_y]})).mark_rule(color='red').encode(
                    y=alt.Y('mean:Q') if orient == 'vertical' else alt.X('mean:Q') # type: ignore
                )  # Remove o título e o eixo

                return st.altair_chart(bar + label + rule, use_container_width=True) # type: ignore

            return st.altair_chart(bar + label, use_container_width=True) # type: ignore
        else:
            st.error(f"A coluna '{x}' não existe no DataFrame.")

    def bar(self,
        x: str,
        y: str,
        aggregation = 'count',
        color: str='#0276D2',
        title_x: str | None = None,
        title_y: str = 'Total',
        line_mean: bool = False,
        orient: str = 'vertical',
        group_by: bool = True,
        nlargest = False
        ):

        if x in self.df.columns:
            if group_by:
                self.result = self.dados(x, y, agg=aggregation)
                if nlargest:
                    self.result = self.result.nlargest(5, y)
            else:
                 self.result

            max_y = self.result[y].max()
            y_domain = [0, max_y * 1.10]
            # self.result[y].apply(self.convert_value)

            if orient == 'vertical':
                bar = alt.Chart(self.result).mark_bar(
                    cornerRadiusTopLeft=5, cornerRadiusTopRight=5, color=alt.Gradient(
                        gradient='linear',
                        stops=[alt.GradientStop(color='#0E1117', offset=0),
                            alt.GradientStop(color=color, offset=1)],
                        x1=1,
                        x2=1,
                        y1=1,
                        y2=0)
                ).encode(
                    x=alt.X(x, title=title_x), 
                    y=alt.Y(y, title=title_y, scale=alt.Scale(domain=y_domain), axis=alt.Axis(format=',.0f'))
                )
            elif orient == 'horizontal':
                bar = alt.Chart(self.result).mark_bar(width=100,
                    cornerRadiusTopLeft=5, cornerRadiusTopRight=5, color=alt.Gradient(
                        gradient='linear',
                        stops=[alt.GradientStop(color='#0E1117', offset=0),
                            alt.GradientStop(color=color, offset=1)],
                        x1=1,
                        x2=0,
                        y1=0,
                        y2=1)
                ).encode(
                    x=alt.X(y, title=title_y, scale=alt.Scale(domain=y_domain)),
                    y=alt.Y(x, title=title_x), tooltip=[alt.Tooltip(field=x, type='nominal'),
                    alt.Tooltip(field=y, type='quantitative', title='Total', format=',.0f')]

                ).properties(
                    width=800,  # Altere a largura aqui
                    height=350  # Altere a altura aqui
                )
            else:
                st.error(f"Orientação '{orient}' não é suportada. Use 'vertical' ou 'horizontal'.")
                return

            label = bar.mark_text(dy=-6, color='white').encode(
                text=alt.Text(y, format=',.0f'), tooltip=[alt.Tooltip(field=x, type='nominal'),
                    alt.Tooltip(field=y, type='quantitative', title='Total', format=',.0f')]
            )

            if line_mean:
                mean_y = (self.result[y].max() + self.result[y].min()) / 2
                rule = alt.Chart(pd.DataFrame({'mean': [mean_y]})).mark_rule(color='red').encode(
                    y=alt.Y('mean:Q') if orient == 'vertical' else alt.X('mean:Q') # type: ignore
                )  # Remove o título e o eixo

                return st.altair_chart(bar + label + rule, use_container_width=True) # type: ignore

            return st.altair_chart(bar + label, use_container_width=True) # type: ignore
        else:
            st.error(f"A coluna '{x}' não existe no DataFrame.")

    def line(self,
            x: str,
            y: str,
            aggregation = 'count',
            color: str='#0276D2',
            title_x: str | None=None,
            title_y: str='Total'):

        if x in self.df.columns:
                self.result=self.dados(x, y, agg=aggregation)
                line=alt.Chart(self.result).mark_line(
                    color=color
                ).encode(
                    x=alt.X(x, title=title_x), 
                    y=alt.Y(y, title=title_y)
                )
                label=line.mark_text(dy=-15, color='white').encode(
                    text=alt.Text(y, format=',.0f')
                )
                return st.altair_chart(line + label, use_container_width=True) # type: ignore
        else:
            st.error(f"A coluna '{x}' não existe no DataFrame.")

    def area_gradient(self,
            x: str,
            y: str,
            aggregation = 'count',
            color: str='#0276D2',
            title_x: str | None=None,
            title_y: str='Total',
            line_mean: bool = False):

        if x in self.df.columns:
                self.result=self.dados(x, y, agg=aggregation)
                max_y = self.result[y].max()
                y_domain = [0, max_y * 1.10] 
                area_gradient = alt.Chart(self.result).mark_area(interpolate='linear', point=True,
                line={'color': color},
                color=alt.Gradient(
                    gradient='linear',
                    stops=[alt.GradientStop(color='#101010', offset=0),
                        alt.GradientStop(color=color, offset=1)],
                    x1=1,
                    x2=1,
                    y1=1,
                    y2=0
                )).encode(
                    x=alt.X(x, title=title_x), 
                    y=alt.Y(y, title=title_y, scale=alt.Scale(domain=y_domain))
                )
                label=area_gradient.mark_text(dy=-15, color='white').encode(
                    text=alt.Text(y, format=',.0f')
                )
                if line_mean:
                    mean_y = (self.result[y].max() + self.result[y].min()) / 2
                    rule = alt.Chart(pd.DataFrame({'mean': [mean_y]})).mark_rule(color='yellow').encode(
                    y=alt.Y('mean:Q'),)  # Remove o título e o eixo

                    return st.altair_chart(area_gradient + label + rule, use_container_width=True) # type: ignore

                return st.altair_chart(area_gradient + label, use_container_width=True) # type: ignore
        else:
            st.error(f"A coluna '{x}' não existe no DataFrame.")

    def area(self,
            x: str,
            y: str,
            aggregation = 'count',
            color: str='#0276D2',
            title_x: str | None=None,
            title_y: str='Total'):

        if x in self.df.columns:
                self.result=self.dados(x, y, agg=aggregation)
                area = alt.Chart(self.result).mark_area(
                    color=color
                ).encode(
                    x=alt.X(x, title=title_x), 
                    y=alt.Y(y, title=title_y)
                )
                label=area.mark_text(dy=-15, color='white').encode(
                    text=y
                )
                return st.altair_chart(area + label, use_container_width=True) # type: ignore
        else:
            st.error(f"A coluna '{x}' não existe no DataFrame.")

    def circle(self,
            x: str,
            y: str,
            aggregation = 'count',
            innerRadius=0,
            outerRadius=0,
            cornerRadius=0,
            range_colors: str | list = 'category',
            type_y = 'quantitative',
            group_by: bool = True,
            title_x = None,
            title_y = None):

        if x in self.df.columns:
                if group_by:
                    self.result = self.dados(x, y, agg=aggregation)
                else:
                    self.result = self.df

                circle = alt.Chart(self.result).mark_arc(cornerRadius=cornerRadius, innerRadius=innerRadius, outerRadius=outerRadius, stroke="rgba(255, 255, 255, 0.2)", strokeWidth=5).encode(
                    theta=alt.Theta(field=y, type=type_y, stack=True, title=title_x), # type: ignore
                    color=alt.Color(field=x, type='nominal', title=title_y).scale(range=range_colors), 
                    tooltip=[alt.Tooltip(field=x, type='nominal'), alt.Tooltip(field=y, type='quantitative', format=',.0f', title='Total')]
                )
                if title_y:
                    label=circle.mark_text(radius=outerRadius + 20, size=13).encode(
                    text=title_y
                    )
                else:
                     label=circle.mark_text(dx=5, dy=10, radius=outerRadius + 30, size=13).encode(
                    text=alt.Text(y, format=',.0f')
                    )
                return st.altair_chart(circle + label, use_container_width=True) # type: ignore
        else:
            st.error(f"A coluna '{x}' não existe no DataFrame.")

    def circle_radial(self,
            x: str,
            y: str,
            aggregation = 'count',
            color: str='#0276D2',
            _innerRadius=80,
            _outerRadius=140,
            group_by: bool = True):

        if x in self.df.columns:
                if group_by:
                    self.result = self.dados(x, y, agg=aggregation)
                else:
                    self.result = self.df

                circle = alt.Chart(self.result).mark_arc(innerRadius=_innerRadius, outerRadius=_outerRadius, color=color, stroke="rgb(14, 17, 23)", strokeWidth=4).encode(
                    theta=alt.Theta(field=y, type='quantitative', stack=True),
                    radius=alt.Radius(y, scale=alt.Scale(type="sqrt", zero=True, rangeMin=50)),
                    color=alt.Color(field=x, type='nominal', title=x)
                )
                label=circle.mark_text(radiusOffset=15, size=14, color='azure').encode(
                text=y
                )
                return st.altair_chart(circle + label, use_container_width=True) # type: ignore
        else:
            st.error(f"A coluna '{x}' não existe no DataFrame.")

    def max_value(self, x, y):
        max=self.result.sort_values(by=y, ascending=False)
        max_value=max.iloc[0][x]
        return max_value
    
    def top_max_value(self, x: str, y: str, top: int):
        max=self.result.sort_values(by=y, ascending=False)
        max_value=max.iloc[0:top][x]
        top_list = []
        for i in max_value:
             top_list.append(i)
        return top_list
