# ==============================================================================
# PLANO FIT APP - LÓGICA DE NEGÓCIO
# ==============================================================================
# Este arquivo é o "cérebro" da aplicação. Ele contém todas as funções que
# realizam cálculos, análises e transformações de dados.
# ==============================================================================

from datetime import datetime, timedelta, date
from typing import Dict, Any, List
import pandas as pd
import config
from utils import normalizar_texto
import utils

# ==============================================================================
# FUNÇÕES DE LÓGICA DE NEGÓCIO
# ==============================================================================

def calcular_metricas_saude(dados_pessoais: Dict[str, Any], objetivo_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calcula um conjunto de métricas de saúde e metas com base nos dados
    pessoais e objetivos do usuário.
    """
    # Coleta e trata os dados de entrada
    sexo = dados_pessoais.get("sexo", "M")
    idade = int(dados_pessoais.get("idade", 0) or 0)
    altura_cm = float(dados_pessoais.get("altura", 1.70) or 1.70) * 100
    altura_m = float(dados_pessoais.get("altura", 1.70) or 1.70)
    peso = float(dados_pessoais.get(config.COL_PESO, 70.0) or 0.0)
    intensidade = objetivo_info.get("Atividade", "moderado")
    objetivo = objetivo_info.get("ObjetivoPeso", "manutencao")
    inicio_objetivo = objetivo_info.get("DataInicio", date.today().strftime("%d/%m/%Y"))
    ambiente = objetivo_info.get("Ambiente", "ameno")
    fator_dieta = objetivo_info.get("FatorDieta", 1.0)

    # Pega o Peso Alvo que o usuário inseriu. O padrão é 0.0.
    peso_alvo_usuario = float(objetivo_info.get("PesoAlvo", 0.0) or 0.0)

    # Calcula o peso ideal de referência (baseado no IMC 24.9)
    peso_ideal_bmi = 24.9 * (altura_m ** 2)

    # Se o usuário não inseriu um peso alvo (ou deixou em 0), usa o peso ideal do IMC.
    meta_de_peso_final = peso_alvo_usuario if peso_alvo_usuario > 0 else peso_ideal_bmi

    # Cálculo da TMB com a fórmula de Harris-Benedict
    if sexo == "M":
        TMB = 88.362 + (13.397 * peso) + (4.799 * altura_m * 100) - (5.677 * idade)
    else:
        TMB = 447.593 + (9.247 * peso) + (3.092 * altura_m * 100) - (4.330 * idade)

    IMC = peso / (altura_m ** 2) if altura_m > 0 else 0
    
    fatores_atividade = {"sedentario": 1.2, "leve": 1.375, "moderado": 1.55, "intenso": 1.725, "extremo": 1.9}
    TDEE = TMB * fatores_atividade.get(intensidade, 1.55)

    if objetivo == "perda":
        alvo_calorico = TDEE * 0.8 / fator_dieta
        if alvo_calorico < TMB:
            alvo_calorico = TMB
        elif alvo_calorico > TDEE:
            alvo_calorico = TDEE

    elif objetivo == "manutencao":
        alvo_calorico = TDEE
        
    else: # ganho
        alvo_calorico = TDEE * 1.15 * fator_dieta
        if alvo_calorico < TDEE:
            alvo_calorico = TDEE
        elif alvo_calorico > 1.5*TDEE:
            alvo_calorico = TDEE * 1.5

    balanco_calorico = alvo_calorico - TDEE
    var_semanal_kg = (balanco_calorico * 7) / 9000 # Aproximadamente 7700 kcal equivalem a 1 kg de gordura / utilizando 9000 para ser mais conservador
    var_semanal_percent = (var_semanal_kg / peso) * 100 if peso > 0 else 0

    try:
        dt_inicio = datetime.strptime(inicio_objetivo, "%d/%m/%Y")
        if var_semanal_kg != 0:
            # A timeline agora é calculada com base na 'meta_de_peso_final'
            semanas_para_objetivo = abs((peso - meta_de_peso_final) / var_semanal_kg)
            data_objetivo = datetime.today() + timedelta(weeks=semanas_para_objetivo)
            dias_restantes = (data_objetivo.date() - date.today()).days
            data_objetivo_fmt = data_objetivo.strftime("%d/%m/%Y")
        else:
            dias_restantes, data_objetivo_fmt = 0, "N/A"
    except (ValueError, TypeError):
        dias_restantes, data_objetivo_fmt = 0, "N/A"

    bonus_intensidade = {"leve": 200, "moderado": 400, "intenso": 600, "extremo": 800}.get(intensidade, 0)
    bonus_ambiente = {"frio": 0, "ameno": 200, "quente": 300}.get(ambiente, 0)
    bonus_sexo = (150 if idade < 60 else -150) if sexo == "M" else (-150 if idade >= 60 else 0)
    meta_agua_l = (peso * 30 + bonus_intensidade + bonus_ambiente + bonus_sexo) / 1000

    return {
        "TMB": TMB, "IMC": IMC, "TDEE": TDEE, "alvo_calorico": alvo_calorico,
        "peso_ideal": peso_ideal_bmi, # Mantemos o 'peso_ideal' como referência
        "peso_alvo_final": meta_de_peso_final, # Retorna a meta que está sendo usada
        "var_semanal_kg": var_semanal_kg,
        "var_semanal_percent": var_semanal_percent, "dias_restantes": dias_restantes,
        "data_objetivo_fmt": data_objetivo_fmt, "meta_agua_l": meta_agua_l
    }

def obter_faixa_gordura_ideal(sexo: str, idade: int) -> tuple:
    """
    Retorna a faixa de gordura corporal ideal (min, max) com base no sexo e idade.
    """
    faixas_homens = {
        (15, 24): (13.2, 18.6),
        (25, 34): (15.3, 21.8),
        (35, 44): (16.2, 23.1),
        (45, 54): (16.6, 23.7),
        (55, 64): (18.3, 25.6), # Faixa interpolada para cobrir o intervalo
        (65, 74): (19.9, 27.5)
    }
    
    faixas_mulheres = {
        (15, 24): (23.0, 29.6),
        (25, 34): (22.9, 29.7),
        (35, 44): (22.8, 29.8),
        (45, 54): (23.4, 31.9),
        (55, 64): (27.5, 35.8), # Faixa interpolada para cobrir o intervalo
        (65, 74): (31.5, 39.8)
    }

    tabela_faixas = faixas_homens if sexo == "M" else faixas_mulheres

    for (idade_min, idade_max), faixa in tabela_faixas.items():
        if idade_min <= idade <= idade_max:
            return faixa
    
    # Retorna uma faixa padrão caso a idade esteja fora das tabelas
    return (15, 22) if sexo == "M" else (22, 30)

def classificar_composicao_corporal(gordura_corporal: float, gordura_visceral: float, musculo: float, sexo: str, idade: int) -> Dict[str, str]:
    """
    Classifica os percentuais de gordura corporal, gordura visceral e músculo
    em categorias como 'Normal', 'Elevada', etc., com base no sexo e idade.
    """
    # A classificação de gordura agora usa a nova função baseada em idade.
    faixa_ideal_gordura = obter_faixa_gordura_ideal(sexo, idade)
    gordura_min, gordura_max = faixa_ideal_gordura

    classificacao_gordura = "Normal"
    if gordura_corporal < gordura_min:
        classificacao_gordura = "Baixa"
    elif gordura_corporal > gordura_max:
        # Adiciona um limiar para "Muito Elevada"
        if gordura_corporal > gordura_max * 1.2: # Ex: 20% acima do máximo
            classificacao_gordura = "Muito Elevada"
        else:
            classificacao_gordura = "Elevada"
    _tabela_visceral = [("Normal", 0, 9), ("Elevada", 10, 15)]
    _label_visceral_acima = "Muito Elevada"
    _tabela_musculo = {"M": [("Baixo", 0, 33), ("Normal", 34, 39)],"F": [("Baixo", 0, 23), ("Normal", 24, 29)]}
    _label_musculo_acima = "Excelente"

    def classificar(valor, tabela, label_acima):
        for label, min_val, max_val in tabela:
            if min_val <= valor <= max_val:
                return label
        return label_acima

    return {
        "gordura": classificacao_gordura,
        "visceral": classificar(gordura_visceral, _tabela_visceral, _label_visceral_acima),
        "musculo": classificar(musculo, _tabela_musculo.get(sexo, []), _label_musculo_acima)
    }

def calcular_gasto_treino(cardio: bool, intensidade: str, duracao: int, carga: float, peso: float) -> float:
    """
    Estima o gasto calórico de um treino com base no tipo (cardio ou musculação),
    intensidade, duração, carga e peso corporal.

    Args:
        cardio (bool): True se o treino for cardiovascular.
        intensidade (str): 'Leve', 'Moderado' ou 'Intenso'.
        duracao (int): Duração do treino em minutos.
        carga (float): Carga total levantada (em kg), relevante para musculação.
        peso (float): Peso corporal do usuário (em kg).

    Returns:
        float: A estimativa de calorias gastas.
    """
    if cardio:
        # Para cardio, usa a fórmula baseada em MET (Metabolic Equivalent of Task).
        # MET * peso (kg) * duração (horas)
        MET = {"Leve": 3, "Moderado": 4.5, "Intenso": 6}.get(intensidade, 7) # Valores mais comuns: {"Leve": 3.5, "Moderado": 7, "Intenso": 10}
        return MET * peso * (duracao / 60)
    else:
        # Para musculação, uma fórmula empírica que combina carga e duração.
        fator_carga = {"Leve": 0.025, "Moderado": 0.035, "Intenso": 0.045}.get(intensidade, 0.035)
        intensidade_base = {"Leve": 2.5, "Moderado": 4, "Intenso": 6}.get(intensidade, 4)
        multiplicador = {"Leve": 1.05, "Moderado": 1.1, "Intenso": 1.15}.get(intensidade, 1.1)
        return (carga * fator_carga) + (duracao * intensidade_base * multiplicador)

def analisar_historico_treinos(dft: pd.DataFrame) -> Dict[str, Any]:
    """
    Calcula estatísticas agregadas a partir do histórico de treinos.

    Args:
        dft (pd.DataFrame): DataFrame com o log de treinos.

    Returns:
        Dict[str, Any]: Dicionário com métricas como total de treinos,
                        média por semana, etc. Retorna zerado se o input for vazio.
    """
    if dft.empty:
        return {
            "total_treinos": 0,
            "total_calorias": 0,
            "media_treinos_semana": 0.0,
            "treinos_semana_atual": 0,
            "media_semanal_kcal": 0.0,
            "media_diaria_kcal": 0.0,
            "calorias_ultimo_treino": 0
        }
        
    dft[config.COL_DATA] = pd.to_datetime(dft[config.COL_DATA], format="%d/%m/%Y")
    total_treinos = len(dft)
    total_calorias = dft["Calorias Gastas"].sum()
    # Usa `isocalendar().week` para uma definição consistente de semana.
    dft["semana_do_ano"] = dft[config.COL_DATA].dt.isocalendar().week.astype(int)
    semanas_unicas = dft["semana_do_ano"].nunique()

    media_treinos_semana = total_treinos / semanas_unicas if semanas_unicas > 0 else 0
    media_semanal_kcal = total_calorias / semanas_unicas if semanas_unicas > 0 else 0
    dias_unicos_treinados = dft[config.COL_DATA].nunique()
    media_diaria_kcal = total_calorias / dias_unicos_treinados if dias_unicos_treinados > 0 else 0

    semana_atual = date.today().isocalendar()[1]
    treinos_semana_atual = dft[dft["semana_do_ano"] == semana_atual].shape[0]
    calorias_ultimo_treino = dft["Calorias Gastas"].iloc[0] if not dft.empty else 0

    return {
        "total_treinos": total_treinos,
        "total_calorias": total_calorias,
        "media_treinos_semana": media_treinos_semana,
        "treinos_semana_atual": treinos_semana_atual,
        "media_semanal_kcal": media_semanal_kcal,
        "media_diaria_kcal": media_diaria_kcal,
        "calorias_ultimo_treino": calorias_ultimo_treino
    }

def analisar_progresso_objetivo(df_evolucao: pd.DataFrame, peso_alvo: float) -> Dict[str, Any]:
    """
    Analisa o progresso do usuário em direção à sua meta de peso pessoal.

    Args:
        df_evolucao (pd.DataFrame): DataFrame com o histórico de medições de peso.
        peso_alvo (float): A meta de peso definida pelo usuário.

    Returns:
        Dict[str, Any]: Dicionário com o progresso em kg, percentual e o peso restante.
    """
    if df_evolucao.empty or df_evolucao.shape[0] < 1:
        return None

    peso_inicial = df_evolucao[config.COL_PESO].iloc[0]
    peso_atual = df_evolucao[config.COL_PESO].iloc[-1]

    objetivo_total_kg = peso_alvo - peso_inicial
    progresso_atual_kg = peso_atual - peso_inicial
    restante_kg = peso_alvo - peso_atual

    # Calcula o progresso percentual, tratando a divisão por zero.
    progresso_percent = (progresso_atual_kg / objetivo_total_kg * 100) if objetivo_total_kg != 0 else 0

    return {
        "objetivo_total_kg": objetivo_total_kg,
        "progresso_atual_kg": progresso_atual_kg,
        "restante_kg": restante_kg,
        "progresso_percent": progresso_percent
    }

def analisar_distribuicao_refeicoes(df_refeicoes: pd.DataFrame, tabela_alim: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega os macronutrientes totais por tipo de refeição (café da manhã, almoço, etc.).

    Args:
        df_refeicoes (pd.DataFrame): DataFrame com os alimentos e quantidades do dia.
        tabela_alim (pd.DataFrame): Tabela de composição dos alimentos.

    Returns:
        pd.DataFrame: Um DataFrame com os totais de macros agrupados por refeição.
    """
    if df_refeicoes.empty or tabela_alim.empty: return pd.DataFrame()

    dados_detalhados = []
    # Itera sobre cada alimento registrado pelo usuário.
    for _, row in df_refeicoes.iterrows():
        alimento = row.get("Alimento", "")
        qtd = float(row.get("Quantidade", 0.0) or 0.0)
        refeicao = row.get("Refeicao")

        if not all([alimento, qtd > 0, refeicao]): continue

        # Normaliza o nome do alimento para fazer uma busca flexível na tabela.
        proc = normalizar_texto(alimento)
        linha_alim = tabela_alim[tabela_alim[config.COL_ALIMENTO_PROC].str.contains(proc, na=False)]

        # Se o alimento for encontrado, calcula seus macros proporcionalmente à quantidade.
        if not linha_alim.empty:
            fator = qtd / 100.0 # A tabela TACO é baseada em 100g.
            info_nutricional = {
                "Refeicao": refeicao,
                "Quantidade": qtd,
                config.COL_ENERGIA: float(linha_alim.iloc[0].get(config.COL_ENERGIA, 0)) * fator,
                config.COL_PROTEINA: float(linha_alim.iloc[0].get(config.COL_PROTEINA, 0)) * fator,
                config.COL_CARBOIDRATO: float(linha_alim.iloc[0].get(config.COL_CARBOIDRATO, 0)) * fator,
                config.COL_LIPIDEOS: float(linha_alim.iloc[0].get(config.COL_LIPIDEOS, 0)) * fator
            }
            dados_detalhados.append(info_nutricional)

    if not dados_detalhados: return pd.DataFrame()

    df_detalhado = pd.DataFrame(dados_detalhados)
    # Agrupa por refeição e soma os valores para obter os totais.
    return df_detalhado.groupby("Refeicao").sum()


def analisar_consistencia_habitos(dft_log: pd.DataFrame, df_plano_semanal_ativo: pd.DataFrame) -> Dict[str, Any]:
    """
    Calcula a sequência de treinos consecutivos (streak) e a adesão ao plano semanal.

    Args:
        dft_log (pd.DataFrame): DataFrame com o histórico de todos os treinos registrados.
        df_plano_semanal_ativo (pd.DataFrame): DataFrame com o plano de treino para a semana atual.

    Returns:
        Dict[str, Any]: Um dicionário contendo as métricas de consistência.
    """
    # Retorna valores padrão se não houver histórico de treinos.
    if dft_log.empty:
        return {
            "streak_dias": 0, "dias_treinados_semana": 0,
            "dias_planejados_semana": 0, "adesao_percentual": 0
        }

    # --- Cálculo da Sequência de Treinos (Streak) ---
    # Pega as datas únicas de treino, converte para date e ordena da mais recente para a mais antiga.
    workout_dates = pd.to_datetime(dft_log[config.COL_DATA], format="%d/%m/%Y").dt.date.unique()
    workout_dates = sorted(list(workout_dates), reverse=True)
    
    streak_dias = 0
    today = utils.get_local_date() # <-- ALTERAÇÃO AQUI
    
    # Se o último treino não foi hoje nem ontem, a sequência é 0.
    if not workout_dates or (today not in workout_dates and (today - timedelta(days=1)) not in workout_dates):
        streak_dias = 0
    else:
        # Define o ponto de partida da contagem: hoje ou ontem.
        current_day = workout_dates[0]
        
        # Percorre as datas de treino verificando se são consecutivas.
        for d in workout_dates:
            if d == current_day:
                streak_dias += 1
                current_day -= timedelta(days=1)
            else:
                # A sequência foi quebrada.
                break

    # --- Cálculo da Adesão Semanal ---
    dias_planejados_semana = 0
    if not df_plano_semanal_ativo.empty:
        # Conta quantos dias na semana têm um plano que não seja "Descanso".
        dias_planejados_semana = df_plano_semanal_ativo[df_plano_semanal_ativo['plano_treino'] != 'Descanso'].shape[0]

    # Define o início (segunda-feira) e o fim (domingo) da semana atual.
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    # Conta quantos treinos foram registrados dentro do intervalo desta semana.
    dias_treinados_semana = dft_log[
        pd.to_datetime(dft_log[config.COL_DATA], format="%d/%m/%Y").dt.date.between(start_of_week, end_of_week)
    ][config.COL_DATA].nunique() # .nunique() para não contar dois treinos no mesmo dia como 2 dias.

    adesao_percentual = 0
    if dias_planejados_semana > 0:
        adesao_percentual = round((dias_treinados_semana / dias_planejados_semana) * 100)

    return {
        "streak_dias": streak_dias,
        "dias_treinados_semana": dias_treinados_semana,
        "dias_planejados_semana": dias_planejados_semana,
        "adesao_percentual": adesao_percentual
    }

def get_workout_for_day(user_data: Dict[str, Any], target_date: date) -> Dict[str, Any] or None: # type: ignore
    """
    Encontra o plano de treino e os exercícios associados para uma data específica.
    """
    df_macro = user_data.get("df_macrociclos", pd.DataFrame())
    df_meso = user_data.get("df_mesociclos", pd.DataFrame())
    df_plano_sem = user_data.get("df_plano_semanal", pd.DataFrame())
    df_planos_treino = user_data.get("df_planos_treino", pd.DataFrame())
    df_exercicios = user_data.get("df_exercicios", pd.DataFrame())
    
    target_date_ts = pd.to_datetime(target_date)

    if df_macro.empty or 'data_inicio' not in df_macro.columns: return None
    macro_ativo = df_macro[
        (pd.to_datetime(df_macro['data_inicio']) <= target_date_ts) & 
        (pd.to_datetime(df_macro['data_fim']) >= target_date_ts)
    ]
    if macro_ativo.empty: return None

    id_macro_ativo = macro_ativo['id_macrociclo'].iloc[0]
    mesos_do_macro = df_meso[df_meso['id_macrociclo'] == id_macro_ativo] if 'id_macrociclo' in df_meso.columns else pd.DataFrame()
    if mesos_do_macro.empty: return None

    data_inicio_macro = pd.to_datetime(macro_ativo['data_inicio'].iloc[0])
    dias_desde_inicio = (target_date_ts - data_inicio_macro).days
    semana_no_macro = (dias_desde_inicio // 7) + 1
    
    meso_ativo_info = None
    semana_no_mes = 0
    semanas_acumuladas = 0
    if semana_no_macro > 0 and 'ordem' in mesos_do_macro.columns:
        for _, meso in mesos_do_macro.sort_values('ordem').iterrows():
            duracao_meso = int(meso.get('duracao_semanas', 4))
            if semana_no_macro <= semanas_acumuladas + duracao_meso:
                meso_ativo_info = meso
                semana_no_mes = semana_no_macro - semanas_acumuladas
                break
            semanas_acumuladas += duracao_meso
    
    if meso_ativo_info is None: return None

    id_meso_ativo = meso_ativo_info['id_mesociclo']
    dia_da_semana_map = {0: 'Segunda', 1: 'Terça', 2: 'Quarta', 3: 'Quinta', 4: 'Sexta', 5: 'Sábado', 6: 'Domingo'}
    dia_da_semana_hoje = dia_da_semana_map[target_date.weekday()]
    
    plano_semanal = df_plano_sem[
        (df_plano_sem['id_mesociclo'] == id_meso_ativo) & 
        (df_plano_sem['semana_numero'] == semana_no_mes) &
        (df_plano_sem['dia_da_semana'] == dia_da_semana_hoje)
    ] if 'id_mesociclo' in df_plano_sem.columns else pd.DataFrame()

    if plano_semanal.empty: return None
    
    nome_plano_treino = plano_semanal['plano_treino'].iloc[0]
    if nome_plano_treino == "Descanso": return None
    
    plano_info = df_planos_treino[df_planos_treino['nome_plano'] == nome_plano_treino] if 'nome_plano' in df_planos_treino.columns else pd.DataFrame()
    if plano_info.empty: return None

    id_plano = plano_info['id_plano'].iloc[0]
    exercicios_do_plano = df_exercicios[df_exercicios['id_plano'] == id_plano].copy() if 'id_plano' in df_exercicios.columns else pd.DataFrame()

    if exercicios_do_plano.empty: return None

    if 'ordem' in exercicios_do_plano.columns:
        exercicios_do_plano = exercicios_do_plano.sort_values('ordem').reset_index(drop=True)

    return {
        "nome_plano": nome_plano_treino,
        "exercicios": exercicios_do_plano
    }

def get_previous_performance(df_log_exercicios: pd.DataFrame, exercicio_nome: str) -> dict:
    """
    Encontra o último desempenho registrado para um exercício específico,
    retornando os dados brutos (kg, reps, minutos).

    Args:
        df_log_exercicios (pd.DataFrame): O log completo de todos os exercícios.
        exercicio_nome (str): O nome do exercício a ser buscado.

    Returns:
        dict: Um dicionário contendo {'kg': float, 'reps': int, 'minutos': int}. 
              Retorna zeros se não houver registro anterior.
    """
    if df_log_exercicios.empty or 'nome_exercicio' not in df_log_exercicios.columns:
        return {'kg': 0.0, 'reps': 0, 'minutos': 0}

    log_exercicio = df_log_exercicios[df_log_exercicios['nome_exercicio'] == exercicio_nome].copy()
    
    if log_exercicio.empty:
        return {'kg': 0.0, 'reps': 0, 'minutos': 0}

    log_exercicio['Data'] = pd.to_datetime(log_exercicio['Data'], format="%d/%m/%Y")
    ultimo_treino = log_exercicio.sort_values(by='Data', ascending=False).iloc[0]
    
    kg = ultimo_treino.get('kg_realizado', 0.0)
    reps = ultimo_treino.get('reps_realizadas', 0)
    minutos = ultimo_treino.get('minutos_realizados', 0)

    return {'kg': kg, 'reps': reps, 'minutos': minutos}    


def get_latest_metrics(dados_pessoais: Dict[str, Any], df_evolucao: pd.DataFrame) -> Dict[str, Any]:
    """
    Constrói um dicionário com as métricas mais recentes do usuário, buscando o último
    valor diferente de zero no histórico de evolução para cada medida.
    """
    latest_metrics = dados_pessoais.copy()

    if df_evolucao is None or df_evolucao.empty:
        return latest_metrics

    # Preserva o índice original para usá-lo como critério de desempate
    df_sorted = df_evolucao.copy().reset_index()

    df_sorted.columns = df_sorted.columns.astype(str).str.strip()

    col_data = getattr(config, "COL_DATA", "data")
    if col_data not in df_sorted.columns and "data" in df_sorted.columns:
        col_data = "data"

    if col_data not in df_sorted.columns:
        return latest_metrics 

    df_sorted['data_dt'] = pd.to_datetime(df_sorted[col_data], format="%d/%m/%Y", errors='coerce')
    df_sorted.dropna(subset=['data_dt'], inplace=True)
    
    # Ordena pela data (desc) e depois pelo índice original (desc) para que o último lançamento do dia fique no topo
    df_sorted = df_sorted.sort_values(by=['data_dt', 'index'], ascending=[False, False])

    metric_aliases = {
        config.COL_PESO if hasattr(config, "COL_PESO") else "peso": [config.COL_PESO if hasattr(config, "COL_PESO") else "peso", "peso"],
        "gordura_corporal": ["gordura_corporal", "gord_corp", "gordura_corporal_pct"],
        "gordura_visceral": ["gordura_visceral", "gord_visc", "gordura_visceral_pct"],
        "massa_muscular": ["musculos_esqueleticos", "massa_muscular", "musculo", "musc_esq"]
    }
    
    def _to_numeric_series(s):
        s_clean = s.astype(str).str.strip().str.replace(",", ".", regex=False)
        return pd.to_numeric(s_clean, errors='coerce')

    for metric_key, aliases in metric_aliases.items():
        col_found = next((alias for alias in aliases if alias in df_sorted.columns), None)

        if not col_found:
            continue
        
        # CORREÇÃO: Usa a função auxiliar para converter a coluna inteira de forma robusta primeiro
        series_num = _to_numeric_series(df_sorted[col_found])

        # Itera na série numérica já ordenada e limpa
        for idx, value in series_num.items():
            if pd.notna(value) and value != 0:
                latest_metrics[metric_key] = float(value)
                break  # Encontrou o primeiro valor válido, para a busca para esta métrica
            
    return latest_metrics
