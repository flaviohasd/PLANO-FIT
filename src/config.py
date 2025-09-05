# ==============================================================================
# PLANO FIT APP - CONFIGURAÇÕES
# ==============================================================================

from pathlib import Path

# ==============================================================================
# 1. CONSTANTES E CONFIGURAÇÕES GERAIS
# ==============================================================================

# --- Configuração da Aplicação ---
APP_TITLE = "PLANO FIT"
DATA_DIR = Path("data")

# --- Nomes dos Arquivos de Dados ---
# Arquivos Globais (na raiz de data/)
FILE_TABELA_ALIM = "tabela_alimentacao.csv"
FILE_RECOMEND = "recomendacao_diaria.csv"
FILE_USERS = "users.csv"
FILE_SESSION_INFO = "session_info.csv"

# Arquivos Específicos do Usuário (dentro de data/username/)
FILE_DADOS_PESSOAIS = "dados_pessoais.csv"
FILE_OBJETIVO = "objetivo_salvo.csv"
FILE_REFEICOES = "refeicoes_salvas.csv"
FILE_PLANOS_ALIMENTARES = "planos_alimentares.csv"
FILE_EVOLUCAO = "evolucao.csv"
FILE_LOG_TREINOS_SIMPLES = "treinos.csv"
FILE_PLANOS_TREINO = "planos_treino.csv"
FILE_PLANOS_EXERCICIOS = "planos_exercicios.csv"
FILE_LOG_EXERCICIOS = "log_exercicios.csv"
FILE_MACROCICLOS = "macrociclos.csv"
FILE_MESOCICLOS = "mesociclos.csv"
FILE_PLANO_SEMANAL = "plano_semanal.csv"

# --- Caminhos Completos para os Arquivos Globais ---
DATA_DIR.mkdir(exist_ok=True)
PATH_TABELA_ALIM = DATA_DIR / FILE_TABELA_ALIM
PATH_RECOMEND = DATA_DIR / FILE_RECOMEND

# --- Nomes de Colunas (para evitar erros de digitação) ---
COL_ALIMENTO = "Alimento"
COL_ALIMENTO_PROC = "Alimento_proc"
COL_PROTEINA = "Proteina(g)"
COL_CARBOIDRATO = "Carboidrato(g)"
COL_LIPIDEOS = "Lipideos(g)"
COL_SODIO = "Sodio(mg)"
COL_ENERGIA = "Energia(kcal)"
COL_PESO = "peso"
COL_DATA = "data"

# --- Listas de Opções para Selectbox e Cálculos ---
OPCOES_SEXO = ["M", "F"]
OPCOES_NIVEL_ATIVIDADE = ["sedentario", "leve", "moderado", "intenso", "extremo"]
OPCOES_AMBIENTE = ["frio", "ameno", "quente"]
OPCOES_OBJETIVO_PESO = ["perda", "manutencao", "ganho"]
OPCOES_REFEICOES = [
    "Cafe da manha", "Lanche da manha", "Almoco", "Lanche da tarde",
    "Pos-treino", "Jantar", "Lanche da noite"
]
OPCOES_INTENSIDADE_TREINO = ["Leve", "Moderado", "Intenso"]
OPCOES_GRUPOS_MUSCULARES = [
    "Peito", "Costas", "Ombros", "Bíceps", "Tríceps", "Pernas (Quadríceps)",
    "Pernas (Posterior)", "Glúteos", "Panturrilhas", "Abdômen"
]