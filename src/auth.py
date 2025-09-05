# ==============================================================================
# PLANO FIT APP - LÓGICA DE AUTENTICAÇÃO
# ==============================================================================

import hashlib
import pandas as pd
from datetime import datetime
import config
import utils

def hash_password(password):
    """Gera um hash SHA-256 para a senha fornecida."""
    return hashlib.sha256(str.encode(password)).hexdigest()

def verify_password(password, hashed_password):
    """Verifica se a senha corresponde ao hash salvo."""
    return hash_password(password) == hashed_password

def load_users():
    """Carrega o dataframe de usuários."""
    df = utils.carregar_df(config.DATA_DIR / config.FILE_USERS)
    if df.empty:
        return pd.DataFrame(columns=['username', 'password_hash', 'last_login'])
    return df

def save_users(df_users):
    """Salva o dataframe de usuários."""
    utils.salvar_df(df_users, config.DATA_DIR / config.FILE_USERS)

def get_last_user():
    """Lê o arquivo de sessão para obter o último usuário conectado."""
    df = utils.carregar_df(config.DATA_DIR / config.FILE_SESSION_INFO)
    if not df.empty:
        return df['last_user_logged_in'].iloc[0]
    return None

def set_last_user(username):
    """Define o último usuário conectado no arquivo de sessão."""
    df = pd.DataFrame([{'last_user_logged_in': username}])
    utils.salvar_df(df, config.DATA_DIR / config.FILE_SESSION_INFO)

def clear_last_user():
    """Limpa o arquivo de sessão."""
    df = pd.DataFrame(columns=['last_user_logged_in'])
    utils.salvar_df(df, config.DATA_DIR / config.FILE_SESSION_INFO)