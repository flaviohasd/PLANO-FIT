# ==============================================================================
# PLANO FIT APP - CONFIGURAÇÕES
# ==============================================================================
# Este arquivo centraliza todas as constantes e configurações da aplicação.
# Usar um arquivo de configuração ajuda a evitar "números mágicos" ou strings
# repetidas no código, tornando a manutenção mais fácil e segura.
# ==============================================================================

from pathlib import Path

# ==============================================================================
# 1. CONSTANTES E CONFIGURAÇÕES GERAIS
# ==============================================================================

# --- Configuração da Aplicação ---
APP_TITLE = "PLANO FIT"

# --- [CORREÇÃO] Construção de Caminho Absoluto para os Diretórios ---
# Constrói um caminho absoluto para as pastas 'data' e 'assets'.
# Isso garante que o app encontre os arquivos, não importa de onde ele seja executado.
SRC_DIR = Path(__file__).resolve().parent
APP_DIR = SRC_DIR.parent
DATA_DIR = APP_DIR / "data"
ASSETS_DIR = APP_DIR / "assets"

# --- Nomes dos Arquivos de Dados ---
# Manter os nomes dos arquivos como constantes evita erros de digitação.

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
DATA_DIR.mkdir(exist_ok=True)  # Garante que o diretório de dados exista.
PATH_TABELA_ALIM = ASSETS_DIR / "utils" / FILE_TABELA_ALIM
PATH_RECOMEND = ASSETS_DIR / "utils" / FILE_RECOMEND

# --- Nomes de Colunas (para evitar erros de digitação) ---
COL_ALIMENTO = "Alimento"
COL_ALIMENTO_PROC = "Alimento_proc"
COL_PROTEINA = "Proteina(g)"
COL_CARBOIDRATO = "Carboidrato(g)"
COL_LIPIDEOS = "Lipideos(g)"
COL_SODIO = "Sodio(mg)"
COL_ENERGIA = "Energia(kcal)"
COL_PESO = "peso"
COL_DATA = "Data"

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

# --- Gráfico de músculos ---
PATH_GRAFICO_MUSCULOS_BACK = ASSETS_DIR / "muscle_diagram" / "muscular_system_back.svg"
PATH_GRAFICO_MUSCULOS_FRONT = ASSETS_DIR / "muscle_diagram" / 'muscular_system_front.svg'
PATH_GRAFICO_MUSCULOS_MAIN = ASSETS_DIR / "muscle_diagram" / "main"
PATH_GRAFICO_MUSCULOS_SECONDARY = ASSETS_DIR / "muscle_diagram" / "secondary"

# --- Mapeamento de Músculos para Arquivos SVG ---
# ATENÇÃO: As chaves (ex: 'abdômen') devem corresponder aos dados do arquivo
# exercicios.json (em minúsculas). Os valores (ex: 'abdominals.svg') devem
# corresponder aos nomes dos seus arquivos .svg que devem estar em inglês.
MUSCLE_SVG_MAP = {
    # Músculos Frontais
    "abdômen": "abdominals.svg",
    "abdutores": "abductors.svg",
    "adutores": "adductors.svg",
    "bíceps": "biceps.svg",
    "peito": "chest.svg",
    "antebraços": "forearms.svg",
    "pescoço": "neck.svg",
    "quadríceps": "quadriceps.svg",
    "ombros": "shoulders.svg",
    "serrátil anterior": "serratus_anterior.svg", # Músculo adicionado
    # Músculos Traseiros
    "panturrilhas": "calves.svg",
    "glúteos": "glutes.svg",
    "isquiotibiais": "hamstrings.svg",
    "dorsais": "lats.svg",
    "lombar": "lower_back.svg",
    "meio das costas": "middle_back.svg",
    "trapézio": "traps.svg",
    "tríceps": "triceps.svg",
}

# Define quais músculos aparecem em cada vista para renderização correta
# ATENÇÃO: Os nomes aqui devem estar em minúsculas para corresponder à lógica do código.
FRONT_MUSCLES = {
    "abdômen", "abdutores", "adutores", "bíceps", "peito", "antebraços",
    "pescoço", "quadríceps", "ombros", "serrátil anterior" # Músculo adicionado
}
BACK_MUSCLES = {
    "panturrilhas", "glúteos", "isquiotibiais", "dorsais", "lombar", "meio das costas",
    "trapézio", "tríceps", "antebraços", "ombros", "pescoço" # alguns são visíveis de ambos os lados
}
