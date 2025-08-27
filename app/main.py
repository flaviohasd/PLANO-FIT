
import os
import re
import unicodedata
from datetime import datetime, timedelta, date

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

# ==========================
# Configuração e utilidades
# ==========================
APP_TITLE = "PLANO FIT"
DATA_DIR = "data"

st.set_page_config(page_title=APP_TITLE, layout="wide")
st.title("🏋️‍♂️ PLANO FIT")
st.caption("Metas, planejamento alimentar, treinos e evolução")

os.makedirs(DATA_DIR, exist_ok=True)

# Caminhos padrão
PATH_TABELA_ALIM = os.path.join(DATA_DIR, "tabela_alimentacao.csv")
PATH_RECOMEND = os.path.join(DATA_DIR, "recomendacao_diaria.csv")
PATH_DADOS = os.path.join(DATA_DIR, "dados_pessoais.csv")
PATH_OBJ = os.path.join(DATA_DIR, "objetivo_salvo.csv")
PATH_REFEICOES = os.path.join(DATA_DIR, "refeicoes_salvas.csv")
PATH_TREINOS = os.path.join(DATA_DIR, "treinos.csv")
PATH_EVOL = os.path.join(DATA_DIR, "evolucao.csv")

# ------------------
# Funções utilitárias
# ------------------
def limpar_texto_bruto(txt):
    if pd.isna(txt):
        return ""
    txt = str(txt)
    txt = txt.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    txt = re.sub(r"\s+", " ", txt)
    txt = "".join(c for c in txt if unicodedata.category(c)[0] != "C")
    txt = re.sub(r"[^\w\s.,;:()-]", "", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt

def limpar_valor_numerico(valor):
    if pd.isna(valor):
        return 0.0
    valor_limpo = str(valor).replace("*", "").strip()
    if valor_limpo == "":
        return 0.0
    try:
        return float(valor_limpo.replace(",", "."))
    except ValueError:
        return 0.0

def normalizar_texto(txt):
    if pd.isna(txt):
        return ""
    txt = str(txt).lower()
    txt = "".join(c for c in unicodedata.normalize("NFD", txt) if unicodedata.category(c) != "Mn")
    txt = re.sub(r"[^a-z0-9\s]", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt

@st.cache_data(show_spinner=False)
def carregar_tabela_alimentacao(path):
    if not os.path.exists(path):
        return pd.DataFrame()
    df = pd.read_csv(path, encoding="latin1", sep=";", on_bad_lines="skip")
    if "Alimento" in df.columns:
        df["Alimento"] = df["Alimento"].apply(limpar_texto_bruto)
        df["Alimento_proc"] = df["Alimento"].apply(normalizar_texto)
    for col in ["Proteina(g)", "Carboidrato(g)", "Lipideos(g)", "Sodio(mg)", "Energia(kcal)"]:
        if col in df.columns:
            df[col] = df[col].apply(limpar_valor_numerico)
    return df

@st.cache_data(show_spinner=False)
def carregar_recomendacao(path):
    if not os.path.exists(path):
        return pd.DataFrame()
    df = pd.read_csv(path, encoding="latin1", sep=";", on_bad_lines="skip")
    return df

# =====================
# Sidebar: Arquivos base
# =====================
st.sidebar.header("⚙️ Configurações & Arquivos")
up1 = st.sidebar.file_uploader("Tabela de alimentação (.csv ; latin1)", type=["csv"], key="alim")
if up1 is not None:
    with open(PATH_TABELA_ALIM, "wb") as f:
        f.write(up1.read())

up2 = st.sidebar.file_uploader("Recomendação diária (.csv ; latin1)", type=["csv"], key="rec")
if up2 is not None:
    with open(PATH_RECOMEND, "wb") as f:
        f.write(up2.read())

st.sidebar.write(":open_file_folder: Pasta de dados:", os.path.abspath(DATA_DIR))

# Carregamentos
TABELA_ALIM = carregar_tabela_alimentacao(PATH_TABELA_ALIM)
RECOMEND = carregar_recomendacao(PATH_RECOMEND)

if TABELA_ALIM.empty:
    st.warning("Carregue a tabela de alimentação na barra lateral para ativar buscas por alimentos.")
if RECOMEND.empty:
    st.info("Carregue a tabela de recomendação diária na barra lateral para metas de macros.")

# ========================
# Sessão: Dados Pessoais
# ========================
st.subheader("👤 Dados pessoais")

# Carregar existentes
if os.path.exists(PATH_DADOS):
    df_pessoais = pd.read_csv(PATH_DADOS)
    if not df_pessoais.empty:
        row = df_pessoais.iloc[0].to_dict()
    else:
        row = {}
else:
    row = {}

with st.form("form_pessoais"):
    colA, colB, colC, colD = st.columns(4)
    nome = colA.text_input("Nome", value=row.get("nome", ""))
    nascimento = colB.text_input("Nascimento (DD/MM/AAAA)", value=row.get("nascimento", ""))
    altura = colC.number_input("Altura (m)", min_value=0.5, max_value=2.5, step=0.01, value=float(row.get("altura", 1.70) or 1.70))
    sexo = colD.selectbox("Sexo", options=["M", "F"], index=0 if row.get("sexo", "M") == "M" else 1)

    # Peso: se houver evolucao.csv, pegue o último
    peso_existente = None
    if os.path.exists(PATH_EVOL):
        try:
            dfe = pd.read_csv(PATH_EVOL)
            if not dfe.empty and "peso" in dfe.columns:
                peso_existente = float(dfe["peso"].iloc[-1])
        except Exception:
            pass
    peso_val = float(row.get("peso", 70.0) or 70.0)
    if peso_existente is not None:
        peso_val = peso_existente

    colE, colF, colG = st.columns(3)
    peso = colE.number_input("Peso (kg)", min_value=20.0, max_value=400.0, step=0.1, value=peso_val)
    gordura_corporal = colF.number_input("Gordura corporal (%)", min_value=0.0, max_value=80.0, step=0.1, value=float(row.get("gordura_corporal", 0.0) or 0.0))
    gordura_visceral = colG.number_input("Gordura visceral (%)", min_value=0.0, max_value=100.0, step=0.1, value=float(row.get("gordura_visceral", 0.0) or 0.0))

    musculo = st.number_input("Massa muscular (%)", min_value=0.0, max_value=100.0, step=0.1, value=float(row.get("massa_muscular", 0.0) or 0.0))

    submitted = st.form_submit_button("Salvar dados pessoais")

if submitted:
    # idade
    try:
        data_nasc = datetime.strptime(nascimento, "%d/%m/%Y")
        hoje = datetime.today()
        idade = hoje.year - data_nasc.year - ((hoje.month, hoje.day) < (data_nasc.month, data_nasc.day))
    except Exception:
        idade = 0

    df_pessoais = pd.DataFrame([
        {
            "nome": nome,
            "nascimento": nascimento,
            "altura": altura,
            "sexo": sexo,
            "peso": peso,
            "idade": idade,
            "gordura_corporal": gordura_corporal,
            "gordura_visceral": gordura_visceral,
            "massa_muscular": musculo,
        }
    ])
    df_pessoais.to_csv(PATH_DADOS, index=False)
    st.success("Dados pessoais salvos!")

# Recarregar após possível gravação
if os.path.exists(PATH_DADOS):
    df_pessoais = pd.read_csv(PATH_DADOS)
    dados = df_pessoais.iloc[0].to_dict()
else:
    dados = {
        "nome": "",
        "nascimento": "",
        "altura": 1.70,
        "sexo": "M",
        "peso": 70.0,
        "idade": 0,
        "gordura_corporal": 0.0,
        "gordura_visceral": 0.0,
        "massa_muscular": 0.0,
    }

st.divider()

# ========================
# Sessão: Objetivo & metas
# ========================
st.subheader("🎯 Objetivo & Metas")

if os.path.exists(PATH_OBJ):
    df_obj = pd.read_csv(PATH_OBJ)
    row_obj = df_obj.iloc[0].to_dict()
else:
    row_obj = {"DataInicio": date.today().strftime("%d/%m/%Y"), "Atividade": "moderado", "Ambiente": "ameno", "ObjetivoPeso": "manutencao"}

with st.form("form_obj"):
    c1, c2, c3, c4 = st.columns(4)
    inicio_objetivo = c1.text_input("Início do objetivo (DD/MM/AAAA)", value=row_obj.get("DataInicio", date.today().strftime("%d/%m/%Y")))
    intensidade = c2.selectbox("Nível de atividade", options=["sedentario", "leve", "moderado", "intenso", "extremo"], index=["sedentario","leve","moderado","intenso","extremo"].index(row_obj.get("Atividade", "moderado")))
    ambiente = c3.selectbox("Ambiente", options=["frio", "ameno", "quente"], index=["frio","ameno","quente"].index(row_obj.get("Ambiente", "ameno")))
    objetivo = c4.selectbox("Objetivo de peso", options=["perda", "manutencao", "ganho"], index=["perda","manutencao","ganho"].index(row_obj.get("ObjetivoPeso", "manutencao")))
    sbm2 = st.form_submit_button("Salvar objetivo")

if sbm2:
    pd.DataFrame([
        {"DataInicio": inicio_objetivo, "Atividade": intensidade, "Ambiente": ambiente, "ObjetivoPeso": objetivo}
    ]).to_csv(PATH_OBJ, index=False)
    st.success("Objetivo salvo!")

# -------- Cálculos --------
sexo = dados.get("sexo", "M")
idade = int(dados.get("idade", 0) or 0)
altura = float(dados.get("altura", 1.70) or 1.70)
peso = float(dados.get("peso", 70.0) or 70.0)
gordura_corporal = float(dados.get("gordura_corporal", 0.0) or 0.0)
gordura_visceral = float(dados.get("gordura_visceral", 0.0) or 0.0)
musculo = float(dados.get("massa_muscular", 0.0) or 0.0)

# TMB (Harris-Benedict base que você usou)
if sexo == "M":
    TMB = 88.362 + (13.397 * peso) + (4.799 * altura * 100) - (5.677 * idade)
else:
    TMB = 447.593 + (9.247 * peso) + (3.092 * altura * 100) - (4.330 * idade)

IMC = peso / (altura ** 2)

def classificar_imc(v):
    if v < 18.5:
        return "(Abaixo do peso)"
    elif v <= 24.9:
        return "(Peso normal)"
    elif v <= 29.9:
        return "(Sobrepeso)"
    elif v <= 35:
        return "(Obesidade grau I)"
    elif v <= 40:
        return "(Obesidade grau II)"
    else:
        return "(Obesidade grau III)"

fatores = {"sedentario": 1.2, "leve": 1.375, "moderado": 1.55, "intenso": 1.725, "extremo": 1.9}
TDEE = (10 * peso + 6.25 * altura * 100 - 5 * idade + 5) * fatores.get(intensidade, 1.55)

# Tabelas de classificação
_tabela_gordura = pd.DataFrame({
    "classificacao": ["Baixa", "Normal", "Elevada", "Muito Elevada"],
    "homem_min": [0, 11, 21, 26],
    "homem_max": [10, 20, 25, 100],
    "mulher_min": [0, 21, 31, 36],
    "mulher_max": [20, 30, 35, 100],
})
_tabela_visceral = pd.DataFrame({
    "classificacao": ["Normal", "Elevada", "Muito Elevada"],
    "min": [0, 10, 16],
    "max": [9, 15, 100],
})
_tabela_musculo = pd.DataFrame({
    "classificacao": ["Baixo", "Normal", "Excelente"],
    "homem_min": [0, 34, 40],
    "homem_max": [33, 39, 100],
    "mulher_min": [0, 24, 30],
    "mulher_max": [23, 29, 100],
})

def classificar_gordura(valor, sx):
    if sx == "M":
        mask = (_tabela_gordura["homem_min"] <= valor) & (valor <= _tabela_gordura["homem_max"])
    else:
        mask = (_tabela_gordura["mulher_min"] <= valor) & (valor <= _tabela_gordura["mulher_max"])
    return _tabela_gordura.loc[mask, "classificacao"].values[0] if mask.any() else "-"

def classificar_visceral(valor):
    mask = (_tabela_visceral["min"] <= valor) & (valor <= _tabela_visceral["max"])
    return _tabela_visceral.loc[mask, "classificacao"].values[0] if mask.any() else "-"

def classificar_musculo(valor, sx):
    if sx == "M":
        mask = (_tabela_musculo["homem_min"] <= valor) & (valor <= _tabela_musculo["homem_max"])
    else:
        mask = (_tabela_musculo["mulher_min"] <= valor) & (valor <= _tabela_musculo["mulher_max"])
    return _tabela_musculo.loc[mask, "classificacao"].values[0] if mask.any() else "-"

# Alvo calórico
if objetivo == "perda":
    alvo_calorico = TDEE * 0.8
elif objetivo == "manutencao":
    alvo_calorico = TDEE * 1.0
elif objetivo == "ganho":
    alvo_calorico = TDEE * 1.15
else:
    alvo_calorico = TDEE

peso_ideal = 24.9 * (altura ** 2)
caloric_deficit = TDEE - alvo_calorico
var_semanal = (caloric_deficit * 7) / 7700 if alvo_calorico else 0
var_semanal_percent = (var_semanal / peso) * 100 if peso else 0

try:
    dt_inicio = datetime.strptime(inicio_objetivo, "%d/%m/%Y")
    if var_semanal != 0:
        semanas = abs((peso - peso_ideal) / var_semanal)
        data_objetivo = dt_inicio + timedelta(days=semanas * 7)
        dias_rest = (data_objetivo.date() - date.today()).days
        data_objetivo_fmt = data_objetivo.strftime("%d/%m/%Y")
    else:
        semanas = 0
        dias_rest = 0
        data_objetivo_fmt = "N/A"
except Exception:
    semanas = 0
    dias_rest = 0
    data_objetivo_fmt = "N/A"

# Meta de água
bonus_intensidade = {"leve": 200, "moderado": 400, "intenso": 600, "extremo": 800}.get(intensidade, 0)
bonus_ambiente = {"frio": 0, "ameno": 200, "quente": 300}.get(ambiente, 0)
if sexo == "M":
    bonus_sexo = 150 if idade < 60 else -150
else:
    bonus_sexo = -150 if idade >= 60 else 0
qtd_agua = (peso * 30 + bonus_intensidade + bonus_ambiente + bonus_sexo) / 1000

# Bloco métricas
m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("IMC", f"{IMC:.2f}", classificar_imc(IMC))
m2.metric("TMB", f"{TMB:.0f} kcal")
m3.metric("TDEE", f"{TDEE:.0f} kcal")
m4.metric("Alvo calórico", f"{alvo_calorico:.0f} kcal")
m5.metric("Água/dia", f"{qtd_agua:.2f} L")
m6.metric("Peso ideal", f"{peso_ideal:.1f} kg")

st.info(f"Variação semanal esperada: **{var_semanal:+.2f} kg** ({var_semanal_percent:+.2f}%) • Conclusão estimada: **{data_objetivo_fmt}** ({dias_rest} dias)")


# ========================
# Sessão: Classificações
# ========================
st.subheader("🧪 Classificações atuais")
colX, colY, colZ = st.columns(3)
colX.info(f"Gordura corporal: **{gordura_corporal:.1f}%** — {classificar_gordura(gordura_corporal, sexo)}")
colY.info(f"Gordura visceral: **{gordura_visceral:.1f}%** — {classificar_visceral(gordura_visceral)}")
colZ.info(f"Massa muscular: **{musculo:.1f}%** — {classificar_musculo(musculo, sexo)}")

st.divider()


# ========================
# Sessão: Alimentação
# ========================
st.subheader("🍽️ Alimentação e Macros")

# Editor de refeições
if os.path.exists(PATH_REFEICOES):
    df_refeicoes = pd.read_csv(PATH_REFEICOES, encoding="latin1")
else:
    df_refeicoes = pd.DataFrame(columns=["Refeicao", "Alimento", "Quantidade"])  # Quantidade em g

with st.expander("Editar refeições do dia", expanded=False):
    st.caption("Dica: clique em + para adicionar linhas. 'Quantidade' em gramas.")

    # Busca de alimento com ajuda
    if not TABELA_ALIM.empty:
        palavra = st.text_input("Buscar alimento na base (digite parte do nome)")
        if palavra:
            palavra_proc = normalizar_texto(palavra)
            res = TABELA_ALIM[TABELA_ALIM["Alimento_proc"].str.contains(palavra_proc, na=False, regex=False)][["Alimento", "Energia(kcal)", "Proteina(g)", "Carboidrato(g)", "Lipideos(g)"]].head(25)
            st.dataframe(res, use_container_width=True, hide_index=True)

    edit = st.data_editor(
        df_refeicoes,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={
            "Refeicao": st.column_config.SelectboxColumn(options=[
                "Cafe da manha", "Lanche da manha", "Almoco", "Lanche da tarde",
                "Pos-treino", "Jantar", "Lanche da noite"
            ], required=False),
            "Quantidade": st.column_config.NumberColumn("Quantidade (g)", min_value=0.0, step=1.0),
        },
        key="editor_refeicoes",
    )
    if st.button("💾 Salvar refeições"):
        edit.to_csv(PATH_REFEICOES, index=False)
        st.success("Refeições salvas!")

# Cálculo de macros totais
cols_needed = {"Proteina(g)": 0.0, "Carboidrato(g)": 0.0, "Lipideos(g)": 0.0, "Sodio(mg)": 0.0, "Energia(kcal)": 0.0}

total = {k: 0.0 for k in cols_needed}
if not df_refeicoes.empty and not TABELA_ALIM.empty:
    for _, rowr in df_refeicoes.iterrows():
        alimento = str(rowr.get("Alimento", ""))
        qtd = float(rowr.get("Quantidade", 0.0) or 0.0)
        if not alimento or qtd <= 0:
            continue
        proc = normalizar_texto(alimento)
        linha = TABELA_ALIM[TABELA_ALIM["Alimento_proc"].str.contains(proc, na=False)]
        if not linha.empty:
            fator = qtd / 100.0
            for col in cols_needed:
                total[col] += float(linha.iloc[0][col]) * fator
        else:
            st.warning(f"Alimento não encontrado no banco: {alimento}")

# Recomendação diária
st.markdown("#### 🔢 Totais do dia")
if RECOMEND.empty:
    st.write(pd.DataFrame([total]).rename(columns={
        "Energia(kcal)": "Calorias (kcal)",
        "Proteina(g)": "Proteína (g)",
        "Carboidrato(g)": "Carboidrato (g)",
        "Lipideos(g)": "Gorduras (g)",
        "Sodio(mg)": "Sódio (mg)",
    }))
else:
    def obter_recomendacao_diaria(sexo, objetivo, intensidade):
        filt = RECOMEND[
            (RECOMEND["Sexo"].str.lower() == sexo.lower()) &
            (RECOMEND["Objetivo"].str.lower() == objetivo.lower()) &
            (RECOMEND["Atividade"].str.lower() == intensidade.lower())
        ]
        if filt.empty:
            return None
        return filt.iloc[0]

    rec = obter_recomendacao_diaria(sexo, objetivo, intensidade)
    if rec is None:
        st.error("Nenhuma recomendação encontrada para os critérios fornecidos.")
    else:
        prot_obj = float(rec.iloc[3]) * peso
        carb_obj = float(rec.iloc[4]) * peso
        gord_obj = float(rec.iloc[5]) * peso
        sod_obj = float(rec.iloc[6])

        cA, cB, cC, cD, cE = st.columns(5)
        cA.metric("Calorias", f"{total['Energia(kcal)']:.0f} kcal", f"{(total['Energia(kcal)']/alvo_calorico*100 if alvo_calorico else 0):.0f}% do alvo")
        cB.metric("Proteína", f"{total['Proteina(g)']:.1f} g", f"{(total['Proteina(g)']/prot_obj*100 if prot_obj else 0):.0f}% do alvo")
        cC.metric("Carboidrato", f"{total['Carboidrato(g)']:.1f} g", f"{(total['Carboidrato(g)']/carb_obj*100 if carb_obj else 0):.0f}% do alvo")
        cD.metric("Gorduras", f"{total['Lipideos(g)']:.1f} g", f"{(total['Lipideos(g)']/gord_obj*100 if gord_obj else 0):.0f}% do alvo")
        cE.metric("Sódio", f"{total['Sodio(mg)']:.0f} mg", f"{(total['Sodio(mg)']/sod_obj*100 if sod_obj else 0):.0f}% do alvo")

st.divider()


# ========================
# Sessão: Treinos
# ========================
st.subheader("🏃‍♂️ Treinos e Gasto calórico")

# Estimativa de gasto
c1, c2, c3, c4 = st.columns(4)
cardio = c1.toggle("Cardio?", value=False)
intensidade_tr = c2.selectbox("Intensidade", options=["Leve", "Moderado", "Intenso"], index=1)
duracao_min = c3.number_input("Duração (min)", min_value=0, max_value=600, step=5, value=60)
carga_total = c4.number_input("Carga total (kg) — musculação", min_value=0.0, step=5.0, value=5000.0)

# Usa SEMPRE o peso atual salvo
peso_para_gasto = peso

if cardio:
    MET = {"Leve": 3, "Moderado": 4.5, "Intenso": 6}[intensidade_tr]
    gasto_est = MET * peso_para_gasto * (duracao_min/60)
else:
    fator_carga = {"Leve": 0.025, "Moderado": 0.035, "Intenso": 0.045}[intensidade_tr]
    intensidade_base = {"Leve": 2.5, "Moderado": 4, "Intenso": 6}[intensidade_tr]
    multiplicador = {"Leve": 1.05, "Moderado": 1.1, "Intenso": 1.15}[intensidade_tr]
    gasto_est = (carga_total * fator_carga) + (duracao_min * intensidade_base * multiplicador)

st.metric("Gasto estimado", f"{gasto_est:.0f} kcal")

with st.form("form_add_treino"):
    data_treino = st.text_input("Data do treino (DD/MM/AAAA) — vazio = hoje", value="")
    tipo_str = "Cardio" if cardio else "Musculação"
    sbm_treino = st.form_submit_button(f"Adicionar treino: {tipo_str}")

if sbm_treino:
    data_reg = datetime.today().strftime("%d/%m/%Y") if not data_treino else datetime.strptime(data_treino, "%d/%m/%Y").strftime("%d/%m/%Y")
    novo = pd.DataFrame([
        {"data": data_reg, "tipo_treino": tipo_str, "duracao_min": duracao_min, "calorias": round(gasto_est, 2)}
    ])
    if not os.path.exists(PATH_TREINOS):
        novo.to_csv(PATH_TREINOS, index=False)
    else:
        novo.to_csv(PATH_TREINOS, mode="a", header=False, index=False)
    st.success("Treino adicionado!")

# Estatísticas
if os.path.exists(PATH_TREINOS):
    dft = pd.read_csv(PATH_TREINOS)
    if not dft.empty:
        dft["data"] = pd.to_datetime(dft["data"], dayfirst=True)
        total_treinos = len(dft)
        total_calorias = dft["calorias"].sum()
        dft["semana_do_ano"] = dft["data"].dt.isocalendar().week.astype(int)
        semanas = dft["semana_do_ano"].nunique()
        media_treinos_semana = total_treinos / semanas if semanas > 0 else 0
        media_semanal = total_calorias / semanas if semanas > 0 else 0
        media_diaria = total_calorias / dft["data"].nunique() if dft["data"].nunique() > 0 else 0
        semana_atual = datetime.today().isocalendar()[1]
        treinos_semana = dft[dft["semana_do_ano"] == semana_atual].shape[0]
        ultima_cal = dft["calorias"].iloc[-1]

        c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
        c1.metric("Total treinos", f"{total_treinos}")
        c2.metric("Total kcal", f"{total_calorias:.0f}")
        c3.metric("Média/semana", f"{media_treinos_semana:.1f}")
        c4.metric("Treinos esta semana", f"{treinos_semana}")
        c5.metric("kcal/semana (média)", f"{media_semanal:.0f}")
        c6.metric("kcal/dia (média)", f"{media_diaria:.0f}")
        c7.metric("Último treino (kcal)", f"{ultima_cal:.0f}")

        with st.expander("Histórico de Treinos", expanded=False):
            st.dataframe(dft.sort_values("data", ascending=False), use_container_width=True)

st.divider()


# ========================
# Sessão: Evolução
# ========================

st.subheader("📈 Evolução")
with st.expander("Adicionar medidas", expanded=False):

    with st.form("form_add_medida"):
        col1, col2 = st.columns(2)
        data_med = col1.text_input("Data (DD/MM/AAAA) — vazio = hoje", value="")
        peso_in = col2.number_input("Peso (kg)", min_value=0.0, max_value=400.0, step=0.1, value=peso)
        c1, c2, c3, c4 = st.columns(4)
        gord_corp = c1.number_input("Gordura corporal (%)", min_value=0.0, max_value=80.0, step=0.1, value=gordura_corporal)
        gord_visc = c2.number_input("Gordura visceral (%)", min_value=0.0, max_value=100.0, step=0.1, value=gordura_visceral)
        musc_esq = c3.number_input("Músculos esqueléticos (%)", min_value=0.0, max_value=100.0, step=0.1, value=musculo)
        cintura = c4.number_input("Cintura (cm)", min_value=0.0, max_value=300.0, step=0.1, value=0.0)
        peito = st.number_input("Peito (cm)", min_value=0.0, max_value=300.0, step=0.1, value=0.0)
        braco = st.number_input("Braço (cm)", min_value=0.0, max_value=100.0, step=0.1, value=0.0)
        coxa = st.number_input("Coxa (cm)", min_value=0.0, max_value=200.0, step=0.1, value=0.0)
        obs = st.text_input("Observações", value="")
        sbm_med = st.form_submit_button("Adicionar medida")

    if sbm_med:
        if not data_med:
            data_fmt = date.today().strftime("%d/%m/%Y")
        else:
            data_fmt = datetime.strptime(data_med, "%d/%m/%Y").date().strftime("%d/%m/%Y")

        if os.path.exists(PATH_EVOL):
            dfe = pd.read_csv(PATH_EVOL)
        else:
            dfe = pd.DataFrame()

        semana = len(dfe) + 1
        var = 0.0
        if not dfe.empty and "peso" in dfe.columns:
            var = float(peso_in - float(dfe["peso"].iloc[-1]))

        novo = pd.DataFrame([
            {
                "semana": semana,
                "data": data_fmt,
                "peso": peso_in,
                "var": var,
                "gordura_corporal": gord_corp or 0.0,
                "gordura_visceral": gord_visc or 0.0,
                "musculos_esqueleticos": musc_esq or 0.0,
                "cintura": cintura or 0.0,
                "peito": peito or 0.0,
                "braco": braco or 0.0,
                "coxa": coxa or 0.0,
                "observacoes": obs,
            }
        ])

        # atualiza peso em dados pessoais
        try:
            dfp = pd.read_csv(PATH_DADOS)
            dfp.loc[0, "peso"] = float(peso_in)
            dfp.to_csv(PATH_DADOS, index=False)
        except Exception:
            pass

        if not os.path.exists(PATH_EVOL):
            novo.to_csv(PATH_EVOL, index=False)
        else:
            novo.to_csv(PATH_EVOL, mode="a", header=False, index=False)
        st.success("Medida adicionada!")

# Medidas anteriores
with st.expander("Histórico de medições", expanded=False):
    if os.path.exists(PATH_EVOL):
        try:
            dfe = pd.read_csv(PATH_EVOL)
            st.dataframe(dfe.sort_values("semana", ascending=False), use_container_width=True)
            df_evolucao = pd.read_csv(PATH_EVOL, encoding="latin1")

            with st.expander("Editar medidas", expanded=False):
                edit = st.data_editor(
                        df_evolucao,
                        num_rows="dynamic",
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Medidas": st.column_config.SelectboxColumn(options=[
                                "data", "peso", "gordura_corporal",
                                "gordura_visceral", "musculos_esqueleticos", "cintura",
                                "peito", "braco", "coxa", "observacoes"
                            ], required=False),
                            #"data": st.column_config.DatetimeColumn("data", min_value=datetime(2000, 1, 1), format="DD/MM/YYYY", default=datetime.today()),
                            "peso": st.column_config.NumberColumn("peso", min_value=0.0, step=0.01),
                            "gordura_corporal": st.column_config.NumberColumn("gordura_corporal", min_value=0.0, step=0.01),
                            "gordura_visceral": st.column_config.NumberColumn("gordura_visceral", min_value=0.0, step=0.01),
                            "musculos_esqueleticos": st.column_config.NumberColumn("musculos_esqueleticos", min_value=0.0, step=0.01),
                            "cintura": st.column_config.NumberColumn("cintura", min_value=0.0, step=0.01),
                            "peito": st.column_config.NumberColumn("peito", min_value=0.0, step=0.01),
                            "braco": st.column_config.NumberColumn("braco", min_value=0.0, step=0.01),
                            "coxa": st.column_config.NumberColumn("coxa", min_value=0.0, step=0.01)
                            #,"observacoes": st.column_config.TextColumn("observacoes", max_chars=500)
                        },
                        key="editor_medidas",
                    )
                if st.button("💾 Salvar medidas"):
                    edit.to_csv(PATH_EVOL, index=False)
                    st.success("Medidas salvas!")

        except Exception as e:
            st.warning(f"Erro ao carregar evolução: {e}")


# Gráficos de evolução
if os.path.exists(PATH_EVOL):
    dfe = pd.read_csv(PATH_EVOL)
    if not dfe.empty:
        dfe["data"] = pd.to_datetime(dfe["data"], format="%d/%m/%Y")
        dfe = dfe.sort_values("data")
        semanas = dfe["semana"]
        peso_s = dfe["peso"]
        gord_c = dfe["gordura_corporal"]
        gord_v = dfe["gordura_visceral"]
        musc = dfe["musculos_esqueleticos"]
        cintura_s = dfe["cintura"]
        peito_s = dfe["peito"]
        braco_s = dfe["braco"]
        coxa_s = dfe["coxa"]

        # Grafico 1: Peso + comp corporal (eixo secundário)
        fig, ax1 = plt.subplots(figsize=(10, 4))
        ax1.set_xlabel("Semanas")
        ax1.set_ylabel("Peso (kg)")
        ax1.plot(semanas, peso_s, marker="o", label="Peso (kg)")
        ax1.grid(True)

        if len(peso_s) > 1:
            var_total = float(peso_s.iloc[-1] - peso_s.iloc[0])
            ax1.annotate(f"Δ Peso: {var_total:.2f} kg", xy=(float(semanas.iloc[-1]), float(peso_s.iloc[-1])), xytext=(float(semanas.iloc[-1]), float(peso_s.iloc[-1])))

        ax2 = ax1.twinx()
        ax2.set_ylabel("%")
        ax2.plot(semanas, gord_c, marker="o", label="Gordura corporal (%)")
        ax2.plot(semanas, gord_v, marker="o", label="Gordura visceral (%)")
        ax2.plot(semanas, musc, marker="o", label="Músculos Esqueléticos (%)")
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2)
        st.pyplot(fig)

        # Grafico 2: Medidas corporais
        fig2, ax = plt.subplots(figsize=(10, 4))
        ax.plot(semanas, cintura_s, marker="o", label="Cintura")
        ax.plot(semanas, peito_s, marker="o", label="Peito")
        ax.plot(semanas, braco_s, marker="o", label="Braço")
        ax.plot(semanas, coxa_s, marker="o", label="Coxa")
        ax.set_title("Medidas corporais (cm)")
        ax.set_xlabel("Semanas")
        ax.set_ylabel("cm")
        ax.grid(True)
        ax.legend()
        st.pyplot(fig2)

# Rodapé
st.caption("© PLANO FIT app - Criado por Flávio Dias (2025)")