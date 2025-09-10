# ==============================================================================
# PLANO FIT APP - FUNÇÕES DE PLOTAGEM
# ==============================================================================
# Este módulo centraliza a criação de gráficos.
# [SUGESTÃO] A aplicação foi refatorada para usar Plotly em vez de Matplotlib.
# Plotly cria gráficos interativos (HTML/JS) que oferecem uma experiência
# de usuário muito melhor em aplicações web (zoom, tooltips, etc.) e
# se integram perfeitamente com o Streamlit.
# ==============================================================================

from typing import Tuple
import plotly.graph_objects as go
import streamlit as st

def plot_energy_composition(tmb: float, tdee: float, alvo: float):
    """
    Cria um gráfico de barras interativo com Plotly para visualizar a composição
    do gasto energético (TMB + Atividade) e a meta calórica.

    Args:
        tmb (float): Taxa Metabólica Basal.
        tdee (float): Gasto Energético Diário Total.
        alvo (float): Alvo calórico diário.
    """
    gasto_atividade = tdee - tmb
    
    fig = go.Figure()

    # Adiciona a barra para TMB com tooltip personalizado
    fig.add_trace(go.Bar(
        y=['Gasto Energético'],
        x=[tmb],
        name='TMB (Metabolismo Basal)',
        orientation='h',
        marker=dict(color='skyblue', line=dict(color='black', width=1)),
        hovertemplate='<b>TMB (Metabolismo Basal)</b>: %{x:,.0f} kcal<extra></extra>'
    ))

    # Adiciona a barra para Gasto com Atividades com tooltip personalizado
    fig.add_trace(go.Bar(
        y=['Gasto Energético'],
        x=[gasto_atividade],
        name='Gasto com Atividades',
        orientation='h',
        marker=dict(color='deepskyblue', line=dict(color='black', width=1)),
        customdata=[tdee], # Adiciona o TDEE para usar no hover
        hovertemplate='<b>Gasto com Atividades</b>: %{x:,.0f} kcal<br><b>Gasto Total (TDEE)</b>: %{customdata:,.0f} kcal<extra></extra>'
    ))
    
    # Layout empilhado para as barras
    fig.update_layout(barmode='stack')

    # Adiciona uma linha vertical mais espessa para o Alvo Calórico
    fig.add_vline(
        x=alvo,
        line_width=2.5,
        y0=0,
        y1=0.9,
        #line_dash='dash',
        line_color="#FA0000"
    )

    # Adiciona uma anotação destacada para o Alvo Calórico
    fig.add_annotation(
        x=alvo,
        y=0, # Centraliza a seta na barra
        text=f"🎯 Alvo Calórico: {alvo:.0f} kcal",
        showarrow=False,
        arrowhead=1,
        yshift=39,
        ax=0,
        ay=-50,
        font=dict(size=12, color="#FFFFFF"),
        align="center",
        bgcolor="#A70000",
        borderpad=4,
        opacity=1
    )

    # Configurações de layout do gráfico
    fig.update_layout(
        title_text="Composição do Gasto Energético (kcal/dia)",
        xaxis_title="Calorias (kcal)",
        yaxis_title="",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=250,
        margin=dict(l=20, r=20, t=50, b=40),
        plot_bgcolor='rgba(0,0,0,0)'
    )
    fig.update_yaxes(showticklabels=False)

    st.plotly_chart(fig, use_container_width=True)

def plot_composition_range(title: str, current_value: float, normal_range: Tuple[float, float], total_range: Tuple[float, float]):
    """
    Cria um gráfico de 'bullet' ou 'gauge' horizontal para mostrar um valor
    atual dentro de uma faixa normal e uma faixa total.

    Args:
        title (str): O título do gráfico.
        current_value (float): O valor atual do usuário.
        normal_range (Tuple[float, float]): A tupla (min, max) da faixa considerada normal.
        total_range (Tuple[float, float]): A tupla (min, max) da faixa total do gráfico.
    """
    fig = go.Figure()

    # Adiciona a barra de fundo (faixa total)
    fig.add_trace(go.Bar(
        y=[''], x=[total_range[1] - total_range[0]], base=total_range[0],
        orientation='h', marker_color='#E0E0E0', showlegend=False,
        hoverinfo='none'
    ))
    
    # Adiciona a barra da faixa normal
    fig.add_trace(go.Bar(
        y=[''], x=[normal_range[1] - normal_range[0]], base=normal_range[0],
        orientation='h', marker_color='lightgreen', showlegend=False,
        hovertemplate=f"Faixa Normal: {normal_range[0]}-{normal_range[1]}<extra></extra>"
    ))

    # Define o tamanho do offset do texto à barra
    delta_offset = (total_range[1] - total_range[0]) * 0.03

    # Define a cor do texto com base no valor atual
    color = 'red' if current_value > normal_range[1] or normal_range[0] > current_value else 'black'

    # Adiciona uma linha vertical para marcar o valor atual
    fig.add_vline(x=current_value, line_width=3, line_color=color)

    # Adiciona uma anotação para o valor atual
    fig.add_annotation(
        x=current_value + delta_offset, y=-0.1, text=f'<b>{current_value:.1f}</b>',
        showarrow=False, font=dict(color=color, size=14)
    )

    # Configurações de layout
    fig.update_layout(
        title=title,
        barmode='overlay',
        height=150,
        xaxis=dict(range=total_range, showticklabels=True),
        yaxis=dict(showticklabels=False),
        margin=dict(l=10, r=10, t=50, b=10),
        plot_bgcolor='rgba(0,0,0,0)',
    )

    st.plotly_chart(fig, use_container_width=True)