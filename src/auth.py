# ==============================================================================
# PLANO FIT APP - LÓGICA DE AUTENTICAÇÃO
# ==============================================================================
# Este módulo gerencia todas as operações relacionadas a usuários e autenticação,
# como criar/verificar senhas, carregar/salvar perfis e gerenciar a sessão
# "permanecer conectado". Isolar essa lógica aqui torna o código mais seguro
# e organizado.
# ==============================================================================

import hashlib
import pandas as pd
from datetime import datetime
import config
import utils

def hash_password(password: str) -> str:
    """
    Gera um hash SHA-256 para a senha fornecida.
    
    [Nota de Segurança]: Este é um método de hashing simples. Para produção,
    é altamente recomendável usar uma biblioteca como `passlib` que adiciona
    "salts" e usa algoritmos mais robustos (ex: Argon2, bcrypt) para
    proteger contra ataques de rainbow table e força bruta.

    Args:
        password (str): A senha em texto plano.

    Returns:
        str: O hash da senha em formato hexadecimal.
    """
    return hashlib.sha256(str.encode(password)).hexdigest()

def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verifica se a senha fornecida corresponde ao hash salvo.

    Args:
        password (str): A senha em texto plano para verificar.
        hashed_password (str): O hash que está salvo no banco de dados.

    Returns:
        bool: True se a senha corresponder, False caso contrário.
    """
    # Compara o hash da senha digitada com o hash salvo.
    return hash_password(password) == hashed_password

def load_users() -> pd.DataFrame:
    """
    Carrega o dataframe de usuários do arquivo users.csv.
    Se o arquivo não existir, retorna um DataFrame vazio com a estrutura correta.

    Returns:
        pd.DataFrame: DataFrame com os dados dos usuários.
    """
    df = utils.carregar_df(config.DATA_DIR / config.FILE_USERS)
    if df.empty:
        return pd.DataFrame(columns=['username', 'password_hash', 'last_login'])
    return df

def save_users(df_users: pd.DataFrame):
    """
    Salva o dataframe de usuários no arquivo users.csv.

    Args:
        df_users (pd.DataFrame): O DataFrame a ser salvo.
    """
    utils.salvar_df(df_users, config.DATA_DIR / config.FILE_USERS)

def get_last_user() -> str or None:
    """
    Lê o arquivo de sessão para obter o último usuário que marcou
    "Permanecer conectado", permitindo o login automático.

    Returns:
        str or None: O nome do último usuário ou None se não houver nenhum.
    """
    df = utils.carregar_df(config.DATA_DIR / config.FILE_SESSION_INFO)
    if not df.empty and 'last_user_logged_in' in df.columns:
        last_user = df['last_user_logged_in'].iloc[0]
        # Retorna o usuário apenas se o valor não for nulo/vazio.
        return last_user if pd.notna(last_user) else None
    return None

def set_last_user(username: str):
    """
    Define o último usuário conectado no arquivo de sessão.
    É chamado quando o usuário faz login com a opção "Permanecer conectado".

    Args:
        username (str): O nome do usuário a ser salvo.
    """
    df = pd.DataFrame([{'last_user_logged_in': username}])
    utils.salvar_df(df, config.DATA_DIR / config.FILE_SESSION_INFO)

def clear_last_user():
    """
    Limpa o arquivo de sessão.
    É chamado quando o usuário faz logout ou desmarca a opção
    "Permanecer conectado".
    """
    df = pd.DataFrame(columns=['last_user_logged_in'])
    utils.salvar_df(df, config.DATA_DIR / config.FILE_SESSION_INFO)