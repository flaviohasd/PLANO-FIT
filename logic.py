# ==============================================================================
# PLANO FIT APP - LÓGICA DE NEGÓCIO
# ==============================================================================

from datetime import datetime, timedelta, date
from typing import Dict, Any, List

import pandas as pd

import config # pyright: ignore[reportMissingImports]

# ==============================================================================
# 4. FUNÇÕES DE LÓGICA DE NEGÓCIO
# ==============================================================================

def calcular_metricas_saude(dados_pessoais: Dict[str, Any], objetivo_info: Dict[str, Any]) -> Dict[str, Any]:
    sexo = dados_pessoais.get("sexo", "M"); idade = int(dados_pessoais.get("idade", 0) or 0)
    altura = float(dados_pessoais.get("altura", 1.70) or 1.70); peso = float(dados_pessoais.get(config.COL_PESO, 70.0) or 70.0)
    intensidade = objetivo_info.get("Atividade", "moderado"); objetivo = objetivo_info.get("ObjetivoPeso", "manutencao")
    inicio_objetivo = objetivo_info.get("DataInicio", date.today().strftime("%d/%m/%Y")); ambiente = objetivo_info.get("Ambiente", "ameno")
    if sexo == "M": TMB = 88.362 + (13.397 * peso) + (4.799 * altura * 100) - (5.677 * idade)
    else: TMB = 447.593 + (9.247 * peso) + (3.092 * altura * 100) - (4.330 * idade)
    IMC = peso / (altura ** 2) if altura > 0 else 0
    fatores_atividade = {"sedentario": 1.2, "leve": 1.375, "moderado": 1.55, "intenso": 1.725, "extremo": 1.9}
    TDEE = (10 * peso + 6.25 * altura * 100 - 5 * idade + 5) * fatores_atividade.get(intensidade, 1.55)
    if objetivo == "perda": alvo_calorico = TDEE * 0.8
    elif objetivo == "manutencao": alvo_calorico = TDEE
    else: alvo_calorico = TDEE * 1.15
    peso_ideal = 24.9 * (altura ** 2); balanco_calorico = alvo_calorico - TDEE
    var_semanal_kg = (balanco_calorico * 7) / 9000
    var_semanal_percent = (var_semanal_kg / peso) * 100 if peso > 0 else 0
    try:
        dt_inicio = datetime.strptime(inicio_objetivo, "%d/%m/%Y")
        if var_semanal_kg != 0:
            semanas_para_objetivo = abs((peso - peso_ideal) / var_semanal_kg); data_objetivo = dt_inicio + timedelta(weeks=semanas_para_objetivo)
            dias_restantes = (data_objetivo.date() - date.today()).days; data_objetivo_fmt = data_objetivo.strftime("%d/%m/%Y")
        else: dias_restantes, data_objetivo_fmt = 0, "N/A"
    except Exception: dias_restantes, data_objetivo_fmt = 0, "N/A"
    bonus_intensidade = {"leve": 200, "moderado": 400, "intenso": 600, "extremo": 800}.get(intensidade, 0)
    bonus_ambiente = {"frio": 0, "ameno": 200, "quente": 300}.get(ambiente, 0)
    bonus_sexo = (150 if idade < 60 else -150) if sexo == "M" else (-150 if idade >= 60 else 0)
    meta_agua_l = (peso * 30 + bonus_intensidade + bonus_ambiente + bonus_sexo) / 1000
    return {"TMB": TMB, "IMC": IMC, "TDEE": TDEE, "alvo_calorico": alvo_calorico, "peso_ideal": peso_ideal, "var_semanal_kg": var_semanal_kg, "var_semanal_percent": var_semanal_percent, "dias_restantes": dias_restantes, "data_objetivo_fmt": data_objetivo_fmt, "meta_agua_l": meta_agua_l}

def classificar_composicao_corporal(gordura_corporal: float, gordura_visceral: float, musculo: float, sexo: str) -> Dict[str, str]:
    _tabela_gordura = {"M": [("Baixa", 0, 10), ("Normal", 11, 20), ("Elevada", 21, 25)], "F": [("Baixa", 0, 20), ("Normal", 21, 30), ("Elevada", 31, 35)]}; _label_gordura_acima = "Muito Elevada"
    _tabela_visceral = [("Normal", 0, 9), ("Elevada", 10, 15)]; _label_visceral_acima = "Muito Elevada"
    _tabela_musculo = {"M": [("Baixo", 0, 33), ("Normal", 34, 39)],"F": [("Baixo", 0, 23), ("Normal", 24, 29)]}; _label_musculo_acima = "Excelente"
    def classificar(valor, tabela, label_acima):
        for label, min_val, max_val in tabela:
            if min_val <= valor <= max_val: return label
        return label_acima
    return {"gordura": classificar(gordura_corporal, _tabela_gordura[sexo], _label_gordura_acima), "visceral": classificar(gordura_visceral, _tabela_visceral, _label_visceral_acima), "musculo": classificar(musculo, _tabela_musculo[sexo], _label_musculo_acima)}

def calcular_gasto_treino(cardio: bool, intensidade: str, duracao: int, carga: float, peso: float) -> float:
    if cardio:
        MET = {"Leve": 3, "Moderado": 4.5, "Intenso": 6}[intensidade]
        return MET * peso * (duracao / 60)
    else:
        fator_carga = {"Leve": 0.025, "Moderado": 0.035, "Intenso": 0.045}[intensidade]
        intensidade_base = {"Leve": 2.5, "Moderado": 4, "Intenso": 6}[intensidade]
        multiplicador = {"Leve": 1.05, "Moderado": 1.1, "Intenso": 1.15}[intensidade]
        return (carga * fator_carga) + (duracao * intensidade_base * multiplicador)
    
def analisar_historico_treinos(dft: pd.DataFrame) -> Dict[str, Any]:
    if dft.empty: return {}
    dft[config.COL_DATA] = pd.to_datetime(dft[config.COL_DATA], format="%d/%m/%Y"); total_treinos = len(dft)
    total_calorias = dft["calorias"].sum(); dft["semana do ano"] = dft[config.COL_DATA].dt.isocalendar().week.astype(int)
    semanas_unicas = dft["semana do ano"].nunique()
    media_treinos_semana = total_treinos / semanas_unicas if semanas_unicas > 0 else 0
    media_semanal_kcal = total_calorias / semanas_unicas if semanas_unicas > 0 else 0
    media_diaria_kcal = total_calorias / dft[config.COL_DATA].nunique() if dft[config.COL_DATA].nunique() > 0 else 0
    semana_atual = date.today().isocalendar()[1]
    treinos_semana_atual = dft[dft["semana do ano"] == semana_atual].shape[0]
    calorias_ultimo_treino = dft["calorias"].iloc[-1] if not dft.empty else 0
    return {"total_treinos": total_treinos, "total_calorias": total_calorias, "media_treinos_semana": media_treinos_semana, "treinos_semana_atual": treinos_semana_atual, "media_semanal_kcal": media_semanal_kcal, "media_diaria_kcal": media_diaria_kcal, "calorias_ultimo_treino": calorias_ultimo_treino}

def analisar_progresso_objetivo(df_evolucao: pd.DataFrame, metricas: dict) -> Dict[str, Any]:
    if df_evolucao.empty or df_evolucao.shape[0] < 1: return None
    peso_inicial = df_evolucao[config.COL_PESO].iloc[0]; peso_atual = df_evolucao[config.COL_PESO].iloc[-1]
    peso_ideal = metricas.get('peso_ideal', peso_atual); objetivo_total_kg = peso_ideal - peso_inicial
    progresso_atual_kg = peso_atual - peso_inicial; restante_kg = peso_ideal - peso_atual
    progresso_percent = (progresso_atual_kg / objetivo_total_kg * 100) if objetivo_total_kg != 0 else 0
    return {"objetivo_total_kg": objetivo_total_kg, "progresso_atual_kg": progresso_atual_kg, "restante_kg": restante_kg, "progresso_percent": progresso_percent}

def analisar_distribuicao_refeicoes(df_refeicoes: pd.DataFrame, tabela_alim: pd.DataFrame) -> pd.DataFrame:
    if df_refeicoes.empty or tabela_alim.empty: return pd.DataFrame()
    dados_detalhados = []
    for _, row in df_refeicoes.iterrows():
        alimento, qtd, refeicao = row.get("Alimento", ""), float(row.get("Quantidade", 0.0) or 0.0), row.get("Refeicao")
        if not all([alimento, qtd > 0, refeicao]): continue
        proc = normalizar_texto(alimento); linha_alim = tabela_alim[tabela_alim[config.COL_ALIMENTO_PROC].str.contains(proc, na=False)]
        if not linha_alim.empty:
            fator = qtd / 100.0
            info_nutricional = {"Refeicao": refeicao, "Quantidade": qtd, config.COL_ENERGIA: float(linha_alim.iloc[0].get(config.COL_ENERGIA, 0)) * fator, config.COL_PROTEINA: float(linha_alim.iloc[0].get(config.COL_PROTEINA, 0)) * fator, config.COL_CARBOIDRATO: float(linha_alim.iloc[0].get(config.COL_CARBOIDRATO, 0)) * fator, config.COL_LIPIDEOS: float(linha_alim.iloc[0].get(config.COL_LIPIDEOS, 0)) * fator}
            dados_detalhados.append(info_nutricional)
    if not dados_detalhados: return pd.DataFrame()
    df_detalhado = pd.DataFrame(dados_detalhados)
    return df_detalhado.groupby("Refeicao").sum()

def normalizar_texto(txt: str) -> str:
    import pandas as pd
    import unicodedata
    import re
    if pd.isna(txt): return ""
    txt = str(txt).lower()
    txt = "".join(c for c in unicodedata.normalize("NFD", txt) if unicodedata.category(c) != "Mn")
    txt = re.sub(r"[^a-z0-9\s]", " ", txt); txt = re.sub(r"\s+", " ", txt).strip()
    return txt

def analisar_consistencia_habitos(dft_log: pd.DataFrame, df_plano_semanal_ativo: pd.DataFrame) -> Dict[str, Any]:
    """
    Calcula a sequência de treinos consecutivos (streak) e a adesão ao plano semanal.

    Args:
        dft_log (pd.DataFrame): DataFrame com o histórico de todos os treinos registrados.
        df_plano_semanal_ativo (pd.DataFrame): DataFrame com o plano de treino para a semana atual.

    Returns:
        Dict[str, Any]: Um dicionário contendo as métricas de consistência.
    """
    if dft_log.empty:
        return {
            "streak_dias": 0,
            "dias_treinados_semana": 0,
            "dias_planejados_semana": 0,
            "adesao_percentual": 0
        }

    # --- Cálculo da Sequência de Treinos (Streak) ---
    workout_dates = pd.to_datetime(dft_log[config.COL_DATA], format="%d/%m/%Y").dt.date.unique()
    workout_dates = sorted(list(workout_dates), reverse=True)
    
    streak_dias = 0
    today = date.today()
    
    # Se o último treino não foi hoje nem ontem, a sequência é 0.
    if today not in workout_dates and (today - timedelta(days=1)) not in workout_dates:
        streak_dias = 0
    else:
        # Começa a contar de hoje ou de ontem, dependendo de qual foi o último treino.
        current_day = today if today in workout_dates else today - timedelta(days=1)
        
        for d in workout_dates:
            if d == current_day:
                streak_dias += 1
                current_day -= timedelta(days=1)
            else:
                # A sequência foi quebrada antes de chegar nesta data.
                break

    # --- Cálculo da Adesão Semanal ---
    dias_planejados_semana = 0
    if not df_plano_semanal_ativo.empty:
        dias_planejados_semana = df_plano_semanal_ativo[df_plano_semanal_ativo['plano_treino'] != 'Descanso'].shape[0]

    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    dias_treinados_semana = dft_log[
        pd.to_datetime(dft_log[config.COL_DATA], format="%d/%m/%Y").dt.date.between(start_of_week, end_of_week)
    ].shape[0]

    adesao_percentual = 0
    if dias_planejados_semana > 0:
        adesao_percentual = round((dias_treinados_semana / dias_planejados_semana) * 100)

    return {
        "streak_dias": streak_dias,
        "dias_treinados_semana": dias_treinados_semana,
        "dias_planejados_semana": dias_planejados_semana,
        "adesao_percentual": adesao_percentual
    }