# ==============================================================================
# PLANO FIT APP - FUNÇÕES UTILITÁRIAS
# ==============================================================================

import re
import unicodedata
from pathlib import Path

import pandas as pd
import streamlit as st

import config

def get_user_data_path(username: str, filename: str) -> Path:
    """Constrói o caminho para o arquivo de dados específico do usuário."""
    if not username:
        st.error("Erro: Nome de usuário não encontrado na sessão.")
        return None
    user_dir = config.DATA_DIR / username
    user_dir.mkdir(exist_ok=True)
    return user_dir / filename

def limpar_texto_bruto(txt: str) -> str:
    if pd.isna(txt): return ""
    txt = str(txt).replace("\n", " ").replace("\r", " ").replace("\t", " ")
    txt = re.sub(r"\s+", " ", txt); txt = "".join(c for c in txt if unicodedata.category(c)[0] != "C")
    txt = re.sub(r"[^\w\s.,;:()-]", "", txt); txt = re.sub(r"\s+", " ", txt).strip()
    return txt

def limpar_valor_numerico(valor) -> float:
    if pd.isna(valor): return 0.0
    valor_limpo = str(valor).replace("*", "").strip()
    if not valor_limpo: return 0.0
    try: return float(valor_limpo.replace(",", "."))
    except ValueError: return 0.0

def normalizar_texto(txt: str) -> str:
    if pd.isna(txt): return ""
    txt = str(txt).lower()
    txt = "".join(c for c in unicodedata.normalize("NFD", txt) if unicodedata.category(c) != "Mn")
    txt = re.sub(r"[^a-z0-9\s]", " ", txt); txt = re.sub(r"\s+", " ", txt).strip()
    return txt

def carregar_df(path: Path) -> pd.DataFrame:
    if path is None: return pd.DataFrame()
    if not path.exists(): return pd.DataFrame()
    try: 
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo {path.name}: {e}")
        return pd.DataFrame()

def salvar_df(df: pd.DataFrame, path: Path):
    if path is None: return
    try: 
        df.to_csv(path, index=False)
    except Exception as e: 
        st.error(f"Erro ao salvar o arquivo {path.name}: {e}")

def adicionar_registro_df(df_novo: pd.DataFrame, path: Path):
    if path is None: return
    try:
        if path.exists() and path.stat().st_size > 0:
            df_existente = pd.read_csv(path)
            df_final = pd.concat([df_existente, df_novo], ignore_index=True)
            df_final.to_csv(path, index=False)
        else:
            df_novo.to_csv(path, index=False)
    except Exception as e: 
        st.error(f"Erro ao adicionar registro em {path.name}: {e}")


@st.cache_data(show_spinner="Carregando tabela de alimentos...")
def carregar_tabela_alimentacao(path: Path) -> pd.DataFrame:
    if not path.exists(): return pd.DataFrame()
    df = pd.read_csv(path, encoding="latin1", sep=";", on_bad_lines="skip")
    if config.COL_ALIMENTO in df.columns:
        df[config.COL_ALIMENTO] = df[config.COL_ALIMENTO].apply(limpar_texto_bruto)
        df[config.COL_ALIMENTO_PROC] = df[config.COL_ALIMENTO].apply(normalizar_texto)
    colunas_macros = [config.COL_PROTEINA, config.COL_CARBOIDRATO, config.COL_LIPIDEOS, config.COL_SODIO, config.COL_ENERGIA]
    for col in colunas_macros:
        if col in df.columns: df[col] = df[col].apply(limpar_valor_numerico)
    return df

@st.cache_data(show_spinner="Carregando recomendações...")
def carregar_recomendacao(path: Path) -> pd.DataFrame:
    if not path.exists(): return pd.DataFrame()
    return pd.read_csv(path, encoding="latin1", sep=";", on_bad_lines="skip")