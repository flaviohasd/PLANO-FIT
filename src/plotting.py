# ==============================================================================
# PLANO FIT APP - FUNÇÕES DE PLOTAGEM
# ==============================================================================

from typing import Tuple

import matplotlib.pyplot as plt
import streamlit as st

def plot_energy_composition(tmb: float, tdee: float, alvo: float):
    fig, ax = plt.subplots(figsize=(8, 1.5))
    gasto_atividade = tdee - tmb
    ax.barh("Gasto Energético", tmb, color='skyblue', label='TMB (Metabolismo Basal)')
    ax.barh("Gasto Energético", gasto_atividade, left=tmb, color='deepskyblue', label='Gasto com Atividades')
    ax.axvline(x=alvo, color='r', linestyle='--', linewidth=2, label='Alvo Calórico')
    ax.set_xlabel("Calorias (kcal)")
    ax.set_yticks([])
    ax.legend(loc='lower right')
    st.pyplot(fig)
def plot_composition_range(title: str, current_value: float, normal_range: Tuple[float, float], total_range: Tuple[float, float]):
    fig, ax = plt.subplots(figsize=(10, 1.5))
    ax.set_xlim(total_range)
    ax.barh([0], total_range[1] - total_range[0], left=total_range[0], color='#E0E0E0')
    ax.barh([0], normal_range[1] - normal_range[0], left=normal_range[0], color='lightgreen')
    ax.axvline(x=current_value, color='black', linestyle='-', linewidth=2)
    ax.text(current_value, 0.1, f'{current_value:.1f}%', ha='center', va='bottom', fontweight='bold')
    ax.set_yticks([])
    ax.set_title(title)
    st.pyplot(fig)