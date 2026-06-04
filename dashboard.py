# -*- coding: utf-8 -*-
import os
import random
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import requests
import joblib
from sqlalchemy import create_engine, text

st.set_page_config(layout="wide", page_title="Copa do Mundo 2026")

if "partida_escolhida" not in st.session_state:
    st.session_state["partida_escolhida"] = None
if "fundo_time" not in st.session_state:
    st.session_state["fundo_time"] = None
if "mostrar_escalacao" not in st.session_state:
    st.session_state["mostrar_escalacao"] = False
if "formacao_casa" not in st.session_state:
    st.session_state["formacao_casa"] = None
if "formacao_fora" not in st.session_state:
    st.session_state["formacao_fora"] = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_PATH = os.path.join(BASE_DIR, "modelo_previsao.pkl")
SCALER_PATH = os.path.join(BASE_DIR, "scaler_previsao.pkl")
CLASSES_PATH = os.path.join(BASE_DIR, "classes_previsao.pkl")
FEATURES_PATH = os.path.join(BASE_DIR, "features_previsao.pkl")
CSV_PATH = os.path.join(BASE_DIR, "data_raw", "fifa-world-cup-2022", "international_matches.csv")

DATABASE_URL = "postgresql+psycopg2://postgres:admin@localhost:5432/copa2026"

MAPA_TIMES = {
    "Brazil": "Brasil",
    "Argentina": "Argentina",
    "France": "França",
    "Germany": "Alemanha",
    "Spain": "Espanha",
    "Portugal": "Portugal",
    "Mexico": "México",
    "United States": "Estados Unidos",
    "USA": "Estados Unidos",
    "Morocco": "Marrocos",
    "Scotland": "Escócia",
    "Haiti": "Haiti",
    "Canada": "Canadá",
    "Switzerland": "Suíça",
    "Qatar": "Catar",
    "South Africa": "Africa do Sul",
    "South Korea": "Coreia do Sul",
    "Australia": "Austrália",
    "Paraguay": "Paraguai",
    "Ecuador": "Equador",
    "Ivory Coast": "Costa do Marfim",
    "Curacao": "Curaçao",
    "Netherlands": "Países Baixos",
    "Japan": "Japão",
    "Tunisia": "Tunísia",
    "Belgium": "Bélgica",
    "Peru": "Peru",
    "Cameroon": "Camarões",
    "Saudi Arabia": "Arábia Saudita",
    "Uruguay": "Uruguai",
    "Cape Verde Islands": "Cabo Verde",
    "Cape Verde": "Cabo Verde",
    "Senegal": "Senegal",
    "Norway": "Noruega",
    "Austria": "Austria",
    "Algeria": "Argélia",
    "Jordan": "Jordânia",
    "Colombia": "Colômbia",
    "Uzbekistan": "Uzbequistão",
    "Croatia": "Croácia",
    "Ghana": "Gana",
    "Panama": "Panamá",
}

def normalizar_nome_time(nome: str) -> str:
    if pd.isna(nome):
        return nome
    return MAPA_TIMES.get(str(nome).strip(), str(nome).strip())

def classificar_tipo_jogo_hist(valor: str) -> int:
    if valor is None or pd.isna(valor):
        return 1

    txt = str(valor).strip().lower()

    if "friendly" in txt or "amistoso" in txt:
        return 0

    if "world cup" in txt or "copa do mundo" in txt:
        if "qualification" not in txt and "qualifier" not in txt and "qualifying" not in txt:
            return 3

    if (
        "qualification" in txt
        or "qualifier" in txt
        or "qualifying" in txt
        or "eliminat" in txt
        or "nations league" in txt
        or "euro" in txt
        or "copa america" in txt
        or "africa cup" in txt
        or "asian cup" in txt
        or "gold cup" in txt
        or "continental" in txt
    ):
        return 2

    return 1

FUNDO_PADRAO = "https://livesport-ott-images.ssl.cdn.cra.cz/r900xfq60/f5d97f56-8392-4885-bc98-15be6ac186b5.avif"
FUNDO_SELECOES = {
    "Brasil": "https://images.unsplash.com/photo-1547347298-4074fc3086f0?q=80&w=1600&auto=format&fit=crop",
    "Argentina": "https://images.unsplash.com/photo-1517466787929-bc90951d0974?q=80&w=1600&auto=format&fit=crop",
    "França": "https://images.unsplash.com/photo-1522778119026-d647f0596c20?q=80&w=1600&auto=format&fit=crop",
    "México": "https://images.unsplash.com/photo-1486286701208-1d58e9338013?q=80&w=1600&auto=format&fit=crop",
    "Alemanha": "https://images.unsplash.com/photo-1518604666860-9ed391f76460?q=80&w=1600&auto=format&fit=crop",
    "Espanha": "https://images.unsplash.com/photo-1497032205916-ac775f0649ae?q=80&w=1600&auto=format&fit=crop",
    "Portugal": "https://images.unsplash.com/photo-1508098682722-e99c643e7f94?q=80&w=1600&auto=format&fit=crop",
    "Marrocos": "https://images.unsplash.com/photo-1547347298-4074fc3086f0?q=80&w=1600&auto=format&fit=crop",
}

fundo_atual = FUNDO_SELECOES.get(st.session_state["fundo_time"], FUNDO_PADRAO)

st.markdown(
    f"""
    <style>
    .stApp {{
        background-image: url("{fundo_atual}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}
    .stApp::before {{
        content: "";
        position: fixed;
        inset: 0;
        background: rgba(5, 10, 18, 0.82);
        z-index: -1;
    }}
    .block-container {{
        padding-top: 1.3rem;
        padding-bottom: 2rem;
    }}
    h1, h2, h3, h4, h5, h6, p, label, div, span {{
        color: white;
    }}
    .stTabs [data-baseweb="tab-list"] {{
        gap: 10px;
        background: rgba(8, 12, 20, 0.78);
        padding: 10px;
        border-radius: 16px;
        backdrop-filter: blur(8px);
        border: 1px solid rgba(255,255,255,0.06);
    }}
    .stTabs [data-baseweb="tab"] {{
        height: 42px;
        background: linear-gradient(180deg, rgba(22,27,34,0.95), rgba(11,15,20,0.95));
        border-radius: 12px;
        padding: 8px 16px;
        color: #d1d5db;
        font-weight: 600;
        border: 1px solid rgba(255,255,255,0.08);
        transition: all 0.22s ease;
    }}
    .stTabs [data-baseweb="tab"]:hover {{
        background: linear-gradient(180deg, rgba(30,36,46,0.98), rgba(14,18,26,0.98));
        color: #22c55e;
        border-color: rgba(34,197,94,0.65);
        transform: translateY(-2px);
        box-shadow: 0 6px 18px rgba(0,0,0,0.28);
    }}
    .stTabs [aria-selected="true"] {{
        background: linear-gradient(135deg,#0f172a,#14532d) !important;
        color: white !important;
        border: 1px solid rgba(34,197,94,0.7) !important;
        box-shadow: 0 0 18px rgba(34,197,94,0.25);
    }}
    .stTabs [data-baseweb="tab-highlight"] {{
        display: none;
    }}
    .stButton > button {{
        width: 100%;
        background: linear-gradient(180deg, #111827, #0b1220);
        color: #f9fafb;
        border: 1px solid rgba(255,255,255,0.10);
        border-radius: 12px;
        font-weight: 600;
        padding: 0.55rem 0.9rem;
        transition: all 0.22s ease;
        box-shadow: 0 4px 12px rgba(0,0,0,0.18);
    }}
    .stButton > button:hover {{
        background: linear-gradient(180deg, #172033, #0f172a);
        color: #22c55e;
        border-color: rgba(34,197,94,0.65);
        transform: translateY(-2px) scale(1.01);
        box-shadow: 0 8px 22px rgba(0,0,0,0.28);
    }}
    div[data-baseweb="select"] > div {{
        background: rgba(10, 15, 24, 0.85) !important;
        border-radius: 12px !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
    }}
    .custom-card {{
        background: linear-gradient(180deg, rgba(11,15,20,0.88), rgba(17,24,39,0.88));
        border-radius: 16px;
        border: 1px solid rgba(255,255,255,0.08);
        padding: 16px;
        text-align: center;
        margin-bottom: 12px;
        transition: all 0.22s ease;
        box-shadow: 0 6px 18px rgba(0,0,0,0.18);
    }}
    .custom-card:hover {{
        transform: translateY(-4px) scale(1.02);
        border-color: rgba(34,197,94,0.55);
        box-shadow: 0 10px 28px rgba(0,0,0,0.28);
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

def get_engine():
    return create_engine(DATABASE_URL)

@st.cache_data(show_spinner=False)
def carregar_dados():
    engine = get_engine()

    df_selecoes = pd.read_sql_query("SELECT * FROM selecoes", engine)

    df_partidas = pd.read_sql_query("""
        SELECT
            p.*,
            e.nome AS estadio_nome,
            e.cidade AS estadio_cidade,
            e.pais AS estadio_pais,
            e.foto_url AS estadio_foto,
            a.nome AS arbitro_nome,
            a.pais AS arbitro_pais
        FROM partidas p
        LEFT JOIN estadios e ON e.id = p.estadio_id
        LEFT JOIN arbitros a ON a.id = p.arbitro_id
        ORDER BY p.grupo, p.id
    """, engine)

    df_jogadores = pd.read_sql_query("""
        SELECT id, nome, numero, posicao, selecao, rating, titular, foto_url
        FROM jogadores
        ORDER BY selecao, titular DESC, numero
    """, engine)

    df_estadios = pd.read_sql_query("""
        SELECT * FROM estadios
        ORDER BY pais, cidade, nome
    """, engine)

    df_arbitros = pd.read_sql_query("""
        SELECT * FROM arbitros
        ORDER BY nome
    """, engine)

    df_hist = pd.read_csv(CSV_PATH)
    df_hist["date"] = pd.to_datetime(df_hist["date"], errors="coerce")
    df_hist = df_hist.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    df_hist["home_team"] = df_hist["home_team"].apply(normalizar_nome_time)
    df_hist["away_team"] = df_hist["away_team"].apply(normalizar_nome_time)

    if "tournament" in df_hist.columns:
        df_hist["match_type_weight"] = df_hist["tournament"].apply(classificar_tipo_jogo_hist)
    else:
        df_hist["match_type_weight"] = 1

    return df_selecoes, df_partidas, df_jogadores, df_estadios, df_arbitros, df_hist

def carregar_ids_favoritos():
    engine = get_engine()
    df_fav = pd.read_sql_query("SELECT partida_id FROM favoritos", engine)
    return set(df_fav["partida_id"].tolist()) if not df_fav.empty else set()

def favoritar_partida(partida_id: int):
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO favoritos (partida_id) VALUES (:partida_id) ON CONFLICT (partida_id) DO NOTHING"),
            {"partida_id": partida_id}
        )

def desfavoritar_partida(partida_id: int):
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM favoritos WHERE partida_id = :partida_id"),
            {"partida_id": partida_id}
        )

df_selecoes, df_partidas, df_jogadores, df_estadios, df_arbitros, df_hist = carregar_dados()
favoritos_ids = carregar_ids_favoritos()
map_codigos = dict(zip(df_selecoes["nome"], df_selecoes["codigo"]))

API_KEY = "123"
BASE_API = f"https://www.thesportsdb.com/api/v1/json/{API_KEY}"

MAPA_API_TIMES = {
    "Brasil": "Brazil",
    "Alemanha": "Germany",
    "Espanha": "Spain",
    "França": "France",
    "Portugal": "Portugal",
    "Argentina": "Argentina",
    "México": "Mexico",
    "Estados Unidos": "USA",
    "Marrocos": "Morocco",
    "Escócia": "Scotland",
    "Haiti": "Haiti",
    "Canadá": "Canada",
    "Suíça": "Switzerland",
    "Catar": "Qatar",
    "Africa do Sul": "South Africa",
    "Coreia do Sul": "South Korea",
    "Austrália": "Australia",
    "Paraguai": "Paraguay",
    "Equador": "Ecuador",
    "Costa do Marfim": "Ivory Coast",
    "Curaçao": "Curacao",
    "Países Baixos": "Netherlands",
    "Japão": "Japan",
    "Tunísia": "Tunisia",
    "Bélgica": "Belgium",
    "Peru": "Peru",
    "Camarões": "Cameroon",
    "Arábia Saudita": "Saudi Arabia",
    "Uruguai": "Uruguay",
    "Senegal": "Senegal",
    "Noruega": "Norway",
    "Argélia": "Algeria",
    "Jordânia": "Jordan",
    "Colômbia": "Colombia",
    "Uzbequistão": "Uzbekistan",
    "Croácia": "Croatia",
    "Gana": "Ghana",
    "Panamá": "Panama",
}

def nome_para_api(nome_time: str) -> str:
    return MAPA_API_TIMES.get(nome_time, nome_time)

def api_get(endpoint: str, params=None):
    try:
        r = requests.get(f"{BASE_API}/{endpoint}", params=params, timeout=15)
        r.raise_for_status()
        return r.json(), None
    except requests.RequestException as e:
        return None, str(e)

def buscar_time_api(nome_time: str):
    data, err = api_get("searchteams.php", {"t": nome_para_api(nome_time)})
    if err:
        return None, err
    teams = data.get("teams") if data else None
    if not teams:
        return None, "Time não encontrado"
    return teams[0], None

def buscar_ultimos_eventos_time(nome_time: str):
    team, err = buscar_time_api(nome_time)
    if err or not team:
        return None, err or "Time não encontrado"

    team_id = team.get("idTeam")
    if not team_id:
        return None, "ID do time não encontrado"

    data, err = api_get("eventslast.php", {"id": team_id})
    if err:
        return None, err

    return data.get("results", []), None

def carregar_modelo_previsao():
    if not (
        os.path.exists(MODEL_PATH)
        and os.path.exists(SCALER_PATH)
        and os.path.exists(CLASSES_PATH)
        and os.path.exists(FEATURES_PATH)
    ):
        return None, None, None, None

    return (
        joblib.load(MODEL_PATH),
        joblib.load(SCALER_PATH),
        joblib.load(CLASSES_PATH),
        joblib.load(FEATURES_PATH),
    )

def get_latest_team_base(team_name: str):
    jogos = df_hist[
        (df_hist["home_team"] == team_name) | (df_hist["away_team"] == team_name)
    ].sort_values("date")

    if jogos.empty:
        return {
            "fifa_rank": 50.0,
            "fifa_points": 1400.0,
            "offense": 70.0,
            "defense": 70.0,
            "midfield": 70.0,
        }

    row = jogos.iloc[-1]

    if row["home_team"] == team_name:
        return {
            "fifa_rank": float(row["home_team_fifa_rank"]),
            "fifa_points": float(row["home_team_total_fifa_points"]),
            "offense": float(row["home_team_mean_offense_score"]),
            "defense": float(row["home_team_mean_defense_score"]),
            "midfield": float(row["home_team_mean_midfield_score"]),
        }

    return {
        "fifa_rank": float(row["away_team_fifa_rank"]),
        "fifa_points": float(row["away_team_total_fifa_points"]),
        "offense": float(row["away_team_mean_offense_score"]),
        "defense": float(row["away_team_mean_defense_score"]),
        "midfield": float(row["away_team_mean_midfield_score"]),
    }

def get_team_ratings(team_name: str):
    grupo = df_jogadores[df_jogadores["selecao"] == team_name]

    if grupo.empty:
        return {
            "rating_titulares": 6.5,
            "rating_reservas": 6.0,
            "rating_total": 6.3,
        }

    titulares = grupo[grupo["titular"] == 1]
    reservas = grupo[grupo["titular"] == 0]

    return {
        "rating_titulares": float(titulares["rating"].mean()) if not titulares.empty else 6.5,
        "rating_reservas": float(reservas["rating"].mean()) if not reservas.empty else 6.0,
        "rating_total": float(grupo["rating"].mean()) if not grupo.empty else 6.3,
    }

def stats_time_recente(df_passado: pd.DataFrame, team: str, n: int = 10):
    jogos = df_passado[
        (df_passado["home_team"] == team) | (df_passado["away_team"] == team)
    ].tail(n)

    if jogos.empty:
        return {
            "vitorias": 0,
            "empates": 0,
            "derrotas": 0,
            "gols_marcados": 0.0,
            "gols_sofridos": 0.0,
            "win_rate": 0.0,
            "draw_rate": 0.0,
            "loss_rate": 0.0,
            "saldo": 0.0,
            "pontos": 0.0,
            "pontos_por_jogo": 0.0,
            "momentum": 0.0,
            "jogos_oficiais": 0,
            "jogos_amistosos": 0,
            "peso_medio_competicao": 0.0,
        }

    vitorias = empates = derrotas = 0
    gols_marcados = gols_sofridos = 0
    pontos = 0
    momentum = 0.0
    jogos_oficiais = 0
    jogos_amistosos = 0
    soma_peso_comp = 0.0

    pesos_recencia = np.linspace(0.6, 1.4, len(jogos))

    for idx, (_, row) in enumerate(jogos.iterrows()):
        peso_recente = float(pesos_recencia[idx])
        tipo_jogo = int(row["match_type_weight"]) if "match_type_weight" in row.index else 1

        if row["home_team"] == team:
            gm = row["home_team_score"]
            gs = row["away_team_score"]
        else:
            gm = row["away_team_score"]
            gs = row["home_team_score"]

        gols_marcados += gm
        gols_sofridos += gs
        soma_peso_comp += tipo_jogo

        if tipo_jogo == 0:
            jogos_amistosos += 1
        else:
            jogos_oficiais += 1

        if gm > gs:
            vitorias += 1
            pontos += 3
            momentum += 3 * peso_recente * max(1.0, tipo_jogo)
        elif gm == gs:
            empates += 1
            pontos += 1
            momentum += 1 * peso_recente * max(1.0, tipo_jogo)
        else:
            derrotas += 1

    total = len(jogos)

    return {
        "vitorias": vitorias,
        "empates": empates,
        "derrotas": derrotas,
        "gols_marcados": gols_marcados / total,
        "gols_sofridos": gols_sofridos / total,
        "win_rate": vitorias / total,
        "draw_rate": empates / total,
        "loss_rate": derrotas / total,
        "saldo": (gols_marcados - gols_sofridos) / total,
        "pontos": pontos,
        "pontos_por_jogo": pontos / total,
        "momentum": momentum / total,
        "jogos_oficiais": jogos_oficiais,
        "jogos_amistosos": jogos_amistosos,
        "peso_medio_competicao": soma_peso_comp / total,
    }

def calcular_streaks(df_passado: pd.DataFrame, team: str, limite: int = 10):
    jogos = df_passado[
        (df_passado["home_team"] == team) | (df_passado["away_team"] == team)
    ].tail(limite)

    if jogos.empty:
        return {
            "streak_vitorias": 0,
            "streak_invicto": 0,
            "streak_sem_vencer": 0,
        }

    resultados = []
    for _, row in jogos.iterrows():
        if row["home_team"] == team:
            gm = row["home_team_score"]
            gs = row["away_team_score"]
        else:
            gm = row["away_team_score"]
            gs = row["home_team_score"]

        if gm > gs:
            resultados.append("V")
        elif gm == gs:
            resultados.append("E")
        else:
            resultados.append("D")

    resultados = list(reversed(resultados))

    streak_vitorias = 0
    for r in resultados:
        if r == "V":
            streak_vitorias += 1
        else:
            break

    streak_invicto = 0
    for r in resultados:
        if r in ("V", "E"):
            streak_invicto += 1
        else:
            break

    streak_sem_vencer = 0
    for r in resultados:
        if r in ("E", "D"):
            streak_sem_vencer += 1
        else:
            break

    return {
        "streak_vitorias": streak_vitorias,
        "streak_invicto": streak_invicto,
        "streak_sem_vencer": streak_sem_vencer,
    }

def stats_h2h(df_passado: pd.DataFrame, casa: str, fora: str, n: int = 10):
    jogos = df_passado[
        ((df_passado["home_team"] == casa) & (df_passado["away_team"] == fora)) |
        ((df_passado["home_team"] == fora) & (df_passado["away_team"] == casa))
    ].tail(n)

    if jogos.empty:
        return {
            "h2h_vitorias_casa": 0,
            "h2h_empates": 0,
            "h2h_vitorias_fora": 0,
            "h2h_gols_casa": 0.0,
            "h2h_gols_fora": 0.0,
            "h2h_peso_comp": 0.0,
        }

    v_casa = empates = v_fora = 0
    gols_casa = gols_fora = 0
    soma_peso = 0

    for _, row in jogos.iterrows():
        tipo_jogo = int(row["match_type_weight"]) if "match_type_weight" in row.index else 1
        soma_peso += tipo_jogo

        if row["home_team"] == casa:
            gc = row["home_team_score"]
            gf = row["away_team_score"]
        else:
            gc = row["away_team_score"]
            gf = row["home_team_score"]

        gols_casa += gc
        gols_fora += gf

        if gc > gf:
            v_casa += 1
        elif gc < gf:
            v_fora += 1
        else:
            empates += 1

    total = len(jogos)

    return {
        "h2h_vitorias_casa": v_casa,
        "h2h_empates": empates,
        "h2h_vitorias_fora": v_fora,
        "h2h_gols_casa": gols_casa / total,
        "h2h_gols_fora": gols_fora / total,
        "h2h_peso_comp": soma_peso / total,
    }

def decidir_resultado(prob_casa, prob_empate, prob_fora, rank_casa, rank_fora):
    rank_diff = abs(rank_casa - rank_fora)

    if rank_diff > 35:
        return "casa" if rank_casa < rank_fora else "fora"

    if prob_empate > 0.35 and abs(prob_casa - prob_fora) < 0.15:
        return "empate"

    return "casa" if prob_casa > prob_fora else "fora"

def decidir_resultado(prob_casa, prob_empate, prob_fora, rank_casa, rank_fora):
    rank_diff = abs(rank_casa - rank_fora)

    if rank_diff > 35:
        return "casa" if rank_casa < rank_fora else "fora"

    if prob_empate > 0.35 and abs(prob_casa - prob_fora) < 0.15:
        return "empate"

    return "casa" if prob_casa > prob_fora else "fora"


def prever_partida(model, scaler, classes, feature_names, casa, fora):
    base_casa = get_latest_team_base(casa)
    base_fora = get_latest_team_base(fora)

    casa_stats = stats_time_recente(df_hist, casa, n=10)
    fora_stats = stats_time_recente(df_hist, fora, n=10)

    casa_streaks = calcular_streaks(df_hist, casa, limite=10)
    fora_streaks = calcular_streaks(df_hist, fora, limite=10)

    h2h_stats = stats_h2h(df_hist, casa, fora, n=10)

    rating_casa = get_team_ratings(casa)
    rating_fora = get_team_ratings(fora)

    forca_relativa = (
        (base_casa["fifa_points"] + casa_stats["momentum"]) -
        (base_fora["fifa_points"] + fora_stats["momentum"])
    )

    equilibrio_forcas = abs(forca_relativa)
    rank_diff_abs = abs(base_casa["fifa_rank"] - base_fora["fifa_rank"])
    rank_ratio = min(base_casa["fifa_rank"], base_fora["fifa_rank"]) / max(base_casa["fifa_rank"], base_fora["fifa_rank"])

    equilibrio_real = (
        rank_diff_abs +
        abs(casa_stats["win_rate"] - fora_stats["win_rate"]) * 20 +
        abs(casa_stats["momentum"] - fora_stats["momentum"]) * 5
    )

    chance_empate = (
        (1 - min(abs(casa_stats["win_rate"] - fora_stats["win_rate"]), 1.0)) *
        (1 - min(abs(casa_stats["saldo"] - fora_stats["saldo"]), 1.0))
    )

    desnivel_extremo = rank_diff_abs

    def tier_time(rank: float) -> int:
        if rank <= 10:
            return 3
        if rank <= 30:
            return 2
        return 1

    tier_casa = tier_time(base_casa["fifa_rank"])
    tier_fora = tier_time(base_fora["fifa_rank"])
    tier_diff = tier_casa - tier_fora

    X = pd.DataFrame([{
        "home_team_fifa_rank": base_casa["fifa_rank"],
        "away_team_fifa_rank": base_fora["fifa_rank"],
        "home_team_total_fifa_points": base_casa["fifa_points"],
        "away_team_total_fifa_points": base_fora["fifa_points"],

        "home_team_mean_offense_score": base_casa["offense"],
        "home_team_mean_defense_score": base_casa["defense"],
        "home_team_mean_midfield_score": base_casa["midfield"],
        "away_team_mean_offense_score": base_fora["offense"],
        "away_team_mean_defense_score": base_fora["defense"],
        "away_team_mean_midfield_score": base_fora["midfield"],

        "rank_diff": base_casa["fifa_rank"] - base_fora["fifa_rank"],
        "rank_diff_abs": rank_diff_abs,
        "rank_ratio": rank_ratio,
        "points_diff": base_casa["fifa_points"] - base_fora["fifa_points"],
        "attack_diff": base_casa["offense"] - base_fora["offense"],
        "defense_diff": base_casa["defense"] - base_fora["defense"],
        "midfield_diff": base_casa["midfield"] - base_fora["midfield"],

        "forca_relativa": forca_relativa,
        "equilibrio_forcas": equilibrio_forcas,
        "equilibrio_real": equilibrio_real,
        "chance_empate": chance_empate,
        "desnivel_extremo": desnivel_extremo,
        "tier_casa": tier_casa,
        "tier_fora": tier_fora,
        "tier_diff": tier_diff,

        "forma_vitorias_casa": casa_stats["vitorias"],
        "forma_empates_casa": casa_stats["empates"],
        "forma_derrotas_casa": casa_stats["derrotas"],
        "forma_gols_casa": casa_stats["gols_marcados"],
        "forma_sofridos_casa": casa_stats["gols_sofridos"],
        "forma_win_rate_casa": casa_stats["win_rate"],
        "forma_draw_rate_casa": casa_stats["draw_rate"],
        "forma_loss_rate_casa": casa_stats["loss_rate"],
        "forma_saldo_casa": casa_stats["saldo"],
        "forma_pontos_casa": casa_stats["pontos"],
        "forma_ppg_casa": casa_stats["pontos_por_jogo"],
        "forma_momentum_casa": casa_stats["momentum"],
        "forma_jogos_oficiais_casa": casa_stats["jogos_oficiais"],
        "forma_jogos_amistosos_casa": casa_stats["jogos_amistosos"],
        "forma_peso_comp_casa": casa_stats["peso_medio_competicao"],

        "forma_vitorias_fora": fora_stats["vitorias"],
        "forma_empates_fora": fora_stats["empates"],
        "forma_derrotas_fora": fora_stats["derrotas"],
        "forma_gols_fora": fora_stats["gols_marcados"],
        "forma_sofridos_fora": fora_stats["gols_sofridos"],
        "forma_win_rate_fora": fora_stats["win_rate"],
        "forma_draw_rate_fora": fora_stats["draw_rate"],
        "forma_loss_rate_fora": fora_stats["loss_rate"],
        "forma_saldo_fora": fora_stats["saldo"],
        "forma_pontos_fora": fora_stats["pontos"],
        "forma_ppg_fora": fora_stats["pontos_por_jogo"],
        "forma_momentum_fora": fora_stats["momentum"],
        "forma_jogos_oficiais_fora": fora_stats["jogos_oficiais"],
        "forma_jogos_amistosos_fora": fora_stats["jogos_amistosos"],
        "forma_peso_comp_fora": fora_stats["peso_medio_competicao"],

        "streak_vitorias_casa": casa_streaks["streak_vitorias"],
        "streak_invicto_casa": casa_streaks["streak_invicto"],
        "streak_sem_vencer_casa": casa_streaks["streak_sem_vencer"],

        "streak_vitorias_fora": fora_streaks["streak_vitorias"],
        "streak_invicto_fora": fora_streaks["streak_invicto"],
        "streak_sem_vencer_fora": fora_streaks["streak_sem_vencer"],

        "forma_diff_vitorias": casa_stats["vitorias"] - fora_stats["vitorias"],
        "forma_diff_empates": casa_stats["empates"] - fora_stats["empates"],
        "forma_diff_derrotas": casa_stats["derrotas"] - fora_stats["derrotas"],
        "forma_diff_gols": casa_stats["gols_marcados"] - fora_stats["gols_marcados"],
        "forma_diff_sofridos": casa_stats["gols_sofridos"] - fora_stats["gols_sofridos"],
        "forma_diff_win_rate": casa_stats["win_rate"] - fora_stats["win_rate"],
        "forma_diff_draw_rate": casa_stats["draw_rate"] - fora_stats["draw_rate"],
        "forma_diff_loss_rate": casa_stats["loss_rate"] - fora_stats["loss_rate"],
        "forma_diff_saldo": casa_stats["saldo"] - fora_stats["saldo"],
        "forma_diff_pontos": casa_stats["pontos"] - fora_stats["pontos"],
        "forma_diff_ppg": casa_stats["pontos_por_jogo"] - fora_stats["pontos_por_jogo"],
        "forma_diff_momentum": casa_stats["momentum"] - fora_stats["momentum"],
        "forma_diff_jogos_oficiais": casa_stats["jogos_oficiais"] - fora_stats["jogos_oficiais"],
        "forma_diff_jogos_amistosos": casa_stats["jogos_amistosos"] - fora_stats["jogos_amistosos"],
        "forma_diff_peso_comp": casa_stats["peso_medio_competicao"] - fora_stats["peso_medio_competicao"],

        "streak_diff_vitorias": casa_streaks["streak_vitorias"] - fora_streaks["streak_vitorias"],
        "streak_diff_invicto": casa_streaks["streak_invicto"] - fora_streaks["streak_invicto"],
        "streak_diff_sem_vencer": casa_streaks["streak_sem_vencer"] - fora_streaks["streak_sem_vencer"],

        "h2h_vitorias_casa": h2h_stats["h2h_vitorias_casa"],
        "h2h_empates": h2h_stats["h2h_empates"],
        "h2h_vitorias_fora": h2h_stats["h2h_vitorias_fora"],
        "h2h_gols_casa": h2h_stats["h2h_gols_casa"],
        "h2h_gols_fora": h2h_stats["h2h_gols_fora"],
        "h2h_peso_comp": h2h_stats["h2h_peso_comp"],

        "rating_titulares_casa": rating_casa["rating_titulares"],
        "rating_reservas_casa": rating_casa["rating_reservas"],
        "rating_total_casa": rating_casa["rating_total"],
        "rating_titulares_fora": rating_fora["rating_titulares"],
        "rating_reservas_fora": rating_fora["rating_reservas"],
        "rating_total_fora": rating_fora["rating_total"],
        "rating_diff_titulares": rating_casa["rating_titulares"] - rating_fora["rating_titulares"],
        "rating_diff_reservas": rating_casa["rating_reservas"] - rating_fora["rating_reservas"],
        "rating_diff_total": rating_casa["rating_total"] - rating_fora["rating_total"],

        "match_type_weight_atual": 3.0,
        "mando": 0.0,
    }])

    X = X[feature_names]
    X_scaled = scaler.transform(X)
    probs = model.predict_proba(X_scaled)[0]

    prob_casa = float(probs[0])
    prob_empate = float(probs[1])
    prob_fora = float(probs[2])

    # calibragem pós-modelo
    prob_empate *= 0.90

    if base_casa["fifa_rank"] < base_fora["fifa_rank"]:
        prob_casa *= 1.20
    else:
        prob_fora *= 1.20

    if rank_diff_abs > 35:
        if base_casa["fifa_rank"] < base_fora["fifa_rank"]:
            prob_casa *= 1.35
            prob_empate *= 0.60
            prob_fora *= 0.75
        else:
            prob_fora *= 1.35
            prob_empate *= 0.60
            prob_casa *= 0.75

    total = prob_casa + prob_empate + prob_fora
    prob_casa /= total
    prob_empate /= total
    prob_fora /= total

    pred_label = decidir_resultado(
        prob_casa,
        prob_empate,
        prob_fora,
        base_casa["fifa_rank"],
        base_fora["fifa_rank"],
    )

    return {
        "casa": prob_casa,
        "empate": prob_empate,
        "fora": prob_fora,
        "predicao_final": pred_label,
    }

def prever_partida_neutra(model, scaler, classes, feature_names, time_a, time_b):
    """
    Faz previsão em campo neutro.
    Executa a previsão nas duas ordens:
    A x B e B x A.
    Depois tira a média para remover o viés de mandante/visitante.
    """

    probs_ab = prever_partida(
        model, scaler, classes, feature_names,
        time_a, time_b
    )

    probs_ba = prever_partida(
        model, scaler, classes, feature_names,
        time_b, time_a
    )

    prob_a = (probs_ab["casa"] + probs_ba["fora"]) / 2
    prob_b = (probs_ab["fora"] + probs_ba["casa"]) / 2
    prob_empate = (probs_ab["empate"] + probs_ba["empate"]) / 2

    total = prob_a + prob_empate + prob_b

    prob_a /= total
    prob_empate /= total
    prob_b /= total

    if prob_empate > 0.35 and abs(prob_a - prob_b) < 0.15:
        pred_label = "empate"
    elif prob_a > prob_b:
        pred_label = "casa"
    else:
        pred_label = "fora"

    return {
        "casa": prob_a,
        "empate": prob_empate,
        "fora": prob_b,
        "predicao_final": pred_label,
    }

def resultado_curto(row, team_name: str):
    if row["home_team"] == team_name:
        gm = row["home_team_score"]
        gs = row["away_team_score"]
    else:
        gm = row["away_team_score"]
        gs = row["home_team_score"]

    if gm > gs:
        return "V"
    if gm == gs:
        return "E"
    return "D"

def ultimos_jogos_time(df_base: pd.DataFrame, team_name: str, n: int = 5):
    jogos = df_base[
        (df_base["home_team"] == team_name) | (df_base["away_team"] == team_name)
    ].sort_values("date").tail(n).copy()

    if jogos.empty:
        return jogos

    jogos["resultado_time"] = jogos.apply(lambda row: resultado_curto(row, team_name), axis=1)
    return jogos

def score_forma(df_base: pd.DataFrame, team_name: str, n: int = 5):
    jogos = ultimos_jogos_time(df_base, team_name, n=n)

    if jogos.empty:
        return 0, []

    pontos = 0
    sequencia = []

    for _, row in jogos.iterrows():
        r = row["resultado_time"]
        sequencia.append(r)
        if r == "V":
            pontos += 3
        elif r == "E":
            pontos += 1

    score_100 = round((pontos / (n * 3)) * 100)
    return score_100, sequencia

def confronto_direto_stats(df_base: pd.DataFrame, time_a: str, time_b: str):
    jogos = df_base[
        ((df_base["home_team"] == time_a) & (df_base["away_team"] == time_b)) |
        ((df_base["home_team"] == time_b) & (df_base["away_team"] == time_a))
    ].sort_values("date").copy()

    if jogos.empty:
        return {
            "partidas": 0,
            "desde": None,
            "vitorias_a": 0,
            "empates": 0,
            "vitorias_b": 0,
            "gols_a": 0,
            "gols_b": 0,
            "media_gols_a": 0.0,
            "media_gols_b": 0.0,
            "maior_vitoria_a": None,
            "maior_vitoria_b": None,
        }

    vitorias_a = 0
    empates = 0
    vitorias_b = 0
    gols_a = 0
    gols_b = 0
    maior_vitoria_a = None
    maior_vitoria_b = None
    maior_saldo_a = -999
    maior_saldo_b = -999

    for _, row in jogos.iterrows():
        if row["home_team"] == time_a:
            ga = int(row["home_team_score"])
            gb = int(row["away_team_score"])
        else:
            ga = int(row["away_team_score"])
            gb = int(row["home_team_score"])

        gols_a += ga
        gols_b += gb

        if ga > gb:
            vitorias_a += 1
            saldo = ga - gb
            if saldo > maior_saldo_a:
                maior_saldo_a = saldo
                maior_vitoria_a = f"{ga} x {gb} ({pd.to_datetime(row['date']).year})"
        elif ga < gb:
            vitorias_b += 1
            saldo = gb - ga
            if saldo > maior_saldo_b:
                maior_saldo_b = saldo
                maior_vitoria_b = f"{ga} x {gb} ({pd.to_datetime(row['date']).year})"
        else:
            empates += 1

    total = len(jogos)
    return {
        "partidas": total,
        "desde": pd.to_datetime(jogos.iloc[0]["date"]).year,
        "vitorias_a": vitorias_a,
        "empates": empates,
        "vitorias_b": vitorias_b,
        "gols_a": gols_a,
        "gols_b": gols_b,
        "media_gols_a": round(gols_a / total, 2),
        "media_gols_b": round(gols_b / total, 2),
        "maior_vitoria_a": maior_vitoria_a,
        "maior_vitoria_b": maior_vitoria_b,
    }

def montar_tabela_ultimos_jogos(df_base: pd.DataFrame, team_name: str, n: int = 5):
    jogos = ultimos_jogos_time(df_base, team_name, n=n)

    if jogos.empty:
        return pd.DataFrame()

    linhas = []
    for _, row in jogos.sort_values("date", ascending=False).iterrows():
        data = pd.to_datetime(row["date"]).strftime("%d/%m/%Y")

        if row["home_team"] == team_name:
            adversario = row["away_team"]
            placar = f"{int(row['home_team_score'])} x {int(row['away_team_score'])}"
            mando = "Casa"
        else:
            adversario = row["home_team"]
            placar = f"{int(row['away_team_score'])} x {int(row['home_team_score'])}"
            mando = "Fora"

        linhas.append({
            "Data": data,
            "Mando": mando,
            "Adversário": adversario,
            "Placar": placar,
            "Resultado": row["resultado_time"]
        })

    return pd.DataFrame(linhas)

def render_forma_badges(sequencia):
    mapa_cor = {"V": "#16a34a", "E": "#111827", "D": "#ea580c"}

    html = '<div style="display:flex; gap:8px; flex-wrap:wrap; margin-top:8px;">'

    for item in sequencia:
        cor = mapa_cor.get(item, "#374151")
        html += f'''
<div style="
width:34px;
height:34px;
border-radius:10px;
display:flex;
align-items:center;
justify-content:center;
background:{cor};
color:white;
font-weight:bold;
font-size:14px;
box-shadow:0 4px 10px rgba(0,0,0,0.18);
">{item}</div>
'''

    html += '</div>'

    components.html(html, height=60)

FORMACOES_DISPONIVEIS = [
    [4, 3, 3],
    [4, 4, 2],
    [4, 2, 3, 1],
    [4, 1, 4, 1],
    [4, 4, 1, 1],
    [3, 5, 2],
    [3, 4, 3],
    [5, 3, 2],
]

def formacao_para_texto(formacao):
    return " - ".join(str(x) for x in formacao)

def gerar_formacao_aleatoria():
    return random.choice(FORMACOES_DISPONIVEIS)

def posicoes_time_por_formacao(formacao, lado="esquerda"):
    if lado == "esquerda":
        x_gk, x_inicio, x_fim = 10, 24, 52
    else:
        x_gk, x_inicio, x_fim = 90, 76, 48

    coords = [(x_gk, 50, "centro")]
    qtd_linhas = len(formacao)

    if qtd_linhas == 1:
        xs = [x_inicio]
    else:
        passo = (x_fim - x_inicio) / (qtd_linhas - 1)
        xs = [x_inicio + i * passo for i in range(qtd_linhas)]

    for linha_idx, qtd in enumerate(formacao):
        x = xs[linha_idx]

        if qtd == 1:
            ys = [50]
        else:
            margem_topo = 18
            margem_base = 82
            passo_y = (margem_base - margem_topo) / (qtd - 1)
            ys = [margem_topo + i * passo_y for i in range(qtd)]

        for jogador_idx, y in enumerate(ys):
            if qtd == 1:
                setor = "centro"
            elif jogador_idx == 0:
                setor = "direita"
            elif jogador_idx == qtd - 1:
                setor = "esquerda"
            else:
                setor = "centro"

            coords.append((x, y, setor))

    return coords

def posicao_curta(posicao: str, numero: int, idx: int, setor: str = "") -> str:
    pos = (posicao or "").strip().lower()

    if "goleiro" in pos:
        return "GK"
    if "zagueiro" in pos:
        return "CB"
    if "lateral" in pos:
        return "RB" if idx in [1, 2] else "LB"
    if "meio" in pos:
        if setor == "centro":
            return "CM"
        if setor == "esquerda":
            return "LM"
        if setor == "direita":
            return "RM"
        return "CM"
    if "atac" in pos:
        if setor == "centro":
            return "ST"
        if setor == "esquerda":
            return "LW"
        if setor == "direita":
            return "RW"
        return "ST"

    mapa_numero = {
        1: "GK", 2: "RB", 3: "CB", 4: "CB", 5: "LB",
        6: "CM", 7: "RW", 8: "CM", 9: "ST", 10: "CM", 11: "LW"
    }
    return mapa_numero.get(numero, "PL")

def glow_por_rating(rating: float) -> str:
    try:
        r = float(rating)
    except Exception:
        r = 6.5

    if r >= 8.5:
        return "0 0 18px rgba(250,204,21,0.95), 0 0 34px rgba(250,204,21,0.45)"
    if r >= 8.0:
        return "0 0 14px rgba(34,197,94,0.85), 0 0 24px rgba(34,197,94,0.35)"
    if r >= 7.0:
        return "0 0 10px rgba(59,130,246,0.75), 0 0 18px rgba(59,130,246,0.25)"
    return "0 0 8px rgba(255,255,255,0.18)"

def melhor_jogador_do_time(titulares: list) -> int:
    if not titulares:
        return -1

    melhor_idx = 0
    melhor_nota = -999.0
    for i, j in enumerate(titulares):
        try:
            nota = float(j.get("rating", 0))
        except Exception:
            nota = 0.0

        if nota > melhor_nota:
            melhor_nota = nota
            melhor_idx = i

    return melhor_idx

def bandeira_url(codigo: str) -> str:
    codigo = (codigo or "").strip().lower()
    if len(codigo) != 2 or not codigo.isalpha():
        return "https://flagcdn.com/w40/un.png"
    return f"https://flagcdn.com/w40/{codigo}.png"

def render_card_partida(casa, fora, codigo_casa, codigo_fora, dia, hora, grupo, estadio, arbitro):
    html = f"""
    <div style="
        background:linear-gradient(135deg,#111827,#0b1220);
        padding:16px;border-radius:14px;border:1px solid rgba(255,255,255,0.08);
        color:white;font-family:Arial,sans-serif;min-height:140px;box-sizing:border-box;">
        <div style="display:flex;align-items:center;justify-content:space-between;font-size:15px;font-weight:600;gap:10px;">
            <div style="display:flex;align-items:center;gap:8px;">
                <img src="{bandeira_url(codigo_casa)}" width="28"><span>{casa}</span>
            </div>
            <div style="color:#9ca3af;font-weight:bold;">VS</div>
            <div style="display:flex;align-items:center;gap:8px;">
                <span>{fora}</span><img src="{bandeira_url(codigo_fora)}" width="28">
            </div>
        </div>
        <div style="text-align:right;font-size:12px;color:#9ca3af;margin-top:6px;">{dia} • {hora}</div>
        <div style="font-size:12px;color:#cbd5e1;margin-top:8px;">Grupo {grupo}</div>
        <div style="font-size:12px;color:#cbd5e1;margin-top:4px;">🝟 {estadio}</div>
        <div style="font-size:12px;color:#cbd5e1;margin-top:4px;">🧑”⚖︝ {arbitro}</div>
    </div>
    """
    components.html(html, height=170)

def get_elenco(selecao: str):
    elenco = df_jogadores[df_jogadores["selecao"] == selecao].copy()
    if elenco.empty:
        return [], []

    titulares = elenco[elenco["titular"] == 1].copy()
    reservas = elenco[elenco["titular"] == 0].copy()

    if len(titulares) < 11:
        faltam = 11 - len(titulares)
        completar = reservas.head(faltam)
        titulares = pd.concat([titulares, completar])
        reservas = reservas.iloc[faltam:]

    return titulares.head(11).to_dict("records"), reservas.to_dict("records")

def selecionar_partida(casa: str, fora: str):
    atual = st.session_state.get("partida_escolhida")

    mesma_partida_aberta = (
        atual and atual.get("casa") == casa and atual.get("fora") == fora
        and st.session_state.get("mostrar_escalacao") is True
    )

    if mesma_partida_aberta:
        st.session_state["mostrar_escalacao"] = False
        st.session_state["formacao_casa"] = None
        st.session_state["formacao_fora"] = None
    else:
        st.session_state["partida_escolhida"] = {"casa": casa, "fora": fora}
        st.session_state["mostrar_escalacao"] = True
        st.session_state["formacao_casa"] = gerar_formacao_aleatoria()
        st.session_state["formacao_fora"] = gerar_formacao_aleatoria()

def render_campo_duplo(casa: str, fora: str):
    titulares_casa, reservas_casa = get_elenco(casa)
    titulares_fora, reservas_fora = get_elenco(fora)

    if len(titulares_casa) < 11 or len(titulares_fora) < 11:
        st.warning("Não foi possível montar as duas escalações completas.")
        return

    formacao_casa = st.session_state.get("formacao_casa") or [4, 3, 3]
    formacao_fora = st.session_state.get("formacao_fora") or [4, 3, 3]

    st.markdown("---")
    head1, head2 = st.columns([7, 1])

    with head1:
        st.subheader(f"📋 Escalações: {casa} x {fora}")
        st.caption(f"{casa}: {formacao_para_texto(formacao_casa)} | {fora}: {formacao_para_texto(formacao_fora)}")

    with head2:
        if st.button("❌ Fechar escalação", key="fechar_escalacao_topo", use_container_width=True):
            st.session_state["mostrar_escalacao"] = False
            st.session_state["formacao_casa"] = None
            st.session_state["formacao_fora"] = None
            st.rerun()

    pos_esquerda = posicoes_time_por_formacao(formacao_casa, lado="esquerda")
    pos_direita = posicoes_time_por_formacao(formacao_fora, lado="direita")

    melhor_casa = melhor_jogador_do_time(titulares_casa)
    melhor_fora = melhor_jogador_do_time(titulares_fora)

    def player_html(jogador, left, top, bg, idx, melhor=False, setor="centro"):
        foto = str(jogador.get("foto_url") or "").strip()
        numero = jogador.get("numero", "")
        nome = jogador.get("nome", "Jogador")
        rating = jogador.get("rating", "")
        posicao = jogador.get("posicao", "")
        pos_curta = posicao_curta(posicao, int(numero) if str(numero).isdigit() else 0, idx, setor)
        glow = glow_por_rating(rating)

        melhor_badge = ""
        if melhor:
            melhor_badge = """
            <div style="
                position:absolute;
                top:-10px;
                right:-10px;
                width:24px;
                height:24px;
                border-radius:50%;
                background:linear-gradient(135deg,#fde68a,#f59e0b);
                color:#111827;
                display:flex;
                align-items:center;
                justify-content:center;
                font-size:14px;
                font-weight:900;
                box-shadow:0 0 16px rgba(250,204,21,0.85);
                z-index:8;
            ">★</div>
            """

        if foto:
            foto_html = f"""
            <img src="{foto}" style="
                width:42px;
                height:42px;
                border-radius:50%;
                object-fit:cover;
                border:2px solid rgba(255,255,255,0.85);
                box-shadow:{glow};
                background:#0f172a;
            ">
            """
        else:
            foto_html = f"""
            <div style="
                width:42px;
                height:42px;
                border-radius:50%;
                background:#0f172a;
                border:2px solid rgba(255,255,255,0.85);
                box-shadow:{glow};
            "></div>
            """

        return f"""
        <div style="
            position:absolute;
            left:{left}%;
            top:{top}%;
            transform:translate(-50%, -50%);
            text-align:center;
            width:96px;
            font-family:Arial, sans-serif;
            color:white;
            animation: fadeUp 0.45s ease;
            z-index:6;
        ">
            <div style="position:relative; display:inline-block;">
                {foto_html}
                {melhor_badge}
            </div>

            <div style="
                margin-top:6px;
                display:inline-flex;
                align-items:center;
                gap:6px;
                justify-content:center;
                background:{bg};
                color:white;
                border-radius:999px;
                padding:5px 10px;
                font-size:11px;
                font-weight:800;
                box-shadow:0 8px 16px rgba(0,0,0,0.25);
            ">
                <span>#{numero}</span>
                <span>{pos_curta}</span>
            </div>

            <div style="
                margin-top:6px;
                font-size:11px;
                line-height:1.15;
                background:rgba(3, 7, 18, 0.76);
                border-radius:10px;
                padding:5px 6px;
                white-space:nowrap;
                overflow:hidden;
                text-overflow:ellipsis;
                box-shadow:0 6px 12px rgba(0,0,0,0.18);
            ">
                {nome}
            </div>

            <div style="
                margin-top:4px;
                display:inline-block;
                background:#0f172a;
                color:#facc15;
                border-radius:8px;
                padding:2px 6px;
                font-weight:800;
                font-size:11px;
                box-shadow:{glow};
            ">
                ⭝ {rating}
            </div>
        </div>
        """

    def substitutions_html(reservas, titulo, alinhamento):
        itens = ""
        for j in reservas[:5]:
            numero = j.get("numero", "")
            nome = j.get("nome", "")
            rating = j.get("rating", "")
            posicao = posicao_curta(j.get("posicao", ""), int(numero) if str(numero).isdigit() else 0, 0, "centro")

            itens += f"""
            <div style="
                display:flex;
                align-items:center;
                justify-content:space-between;
                background:rgba(255,255,255,0.06);
                border-radius:10px;
                padding:6px 8px;
                margin-bottom:6px;
                font-size:11px;
                gap:8px;
            ">
                <div style="display:flex; flex-direction:column; text-align:left;">
                    <span><b>{numero}</b> {nome}</span>
                    <span style="color:#93c5fd; font-size:10px;">{posicao}</span>
                </div>
                <div style="
                    background:#0f172a;
                    color:#facc15;
                    border-radius:8px;
                    padding:2px 6px;
                    font-weight:bold;
                ">
                    {rating}
                </div>
            </div>
            """

        side = "left:12px;" if alinhamento == "left" else "right:12px;"
        return f"""
        <div style="
            position:absolute;
            {side}
            bottom:12px;
            width:230px;
            background:rgba(0,0,0,0.30);
            border:1px solid rgba(255,255,255,0.10);
            border-radius:14px;
            padding:10px;
            color:white;
            font-family:Arial, sans-serif;
            backdrop-filter: blur(4px);
            z-index:7;
        ">
            <div style="font-weight:bold; margin-bottom:8px;">🔝 {titulo}</div>
            {itens}
        </div>
        """

    jogadores_html = ""
    for idx, (jogador, (left, top, setor)) in enumerate(zip(titulares_casa, pos_esquerda)):
        jogadores_html += player_html(
            jogador, left, top,
            "linear-gradient(135deg, #22c55e, #16a34a)",
            idx=idx,
            melhor=(idx == melhor_casa),
            setor=setor
        )

    for idx, (jogador, (left, top, setor)) in enumerate(zip(titulares_fora, pos_direita)):
        jogadores_html += player_html(
            jogador, left, top,
            "linear-gradient(135deg, #f59e0b, #ef4444)",
            idx=idx,
            melhor=(idx == melhor_fora),
            setor=setor
        )

    heatspots = """
    <div style="
        position:absolute;
        left:28%;
        top:28%;
        width:150px;
        height:150px;
        border-radius:50%;
        background:radial-gradient(circle, rgba(250,204,21,0.22) 0%, rgba(250,204,21,0.08) 35%, rgba(250,204,21,0.0) 72%);
        filter: blur(10px);
        z-index:1;
    "></div>

    <div style="
        position:absolute;
        left:58%;
        top:18%;
        width:180px;
        height:180px;
        border-radius:50%;
        background:radial-gradient(circle, rgba(239,68,68,0.18) 0%, rgba(239,68,68,0.07) 35%, rgba(239,68,68,0.0) 75%);
        filter: blur(12px);
        z-index:1;
    "></div>

    <div style="
        position:absolute;
        left:43%;
        top:52%;
        width:220px;
        height:220px;
        border-radius:50%;
        background:radial-gradient(circle, rgba(59,130,246,0.13) 0%, rgba(59,130,246,0.05) 38%, rgba(59,130,246,0.0) 78%);
        filter: blur(14px);
        z-index:1;
    "></div>
    """

    campo_html = f"""
    <html>
    <head>
    <style>
        body {{
            margin:0;
            background:transparent;
        }}
        @keyframes fadeUp {{
            from {{ opacity:0; transform:translate(-50%, -44%); }}
            to {{ opacity:1; transform:translate(-50%, -50%); }}
        }}
    </style>
    </head>
    <body>
    <div style="
        position:relative;
        width:100%;
        height:760px;
        border-radius:20px;
        overflow:hidden;
        background:
            linear-gradient(rgba(0,0,0,0.08), rgba(0,0,0,0.08)),
            repeating-linear-gradient(
                90deg,
                #14532d 0%,
                #14532d 7%,
                #166534 7%,
                #166534 14%
            );
        border:1px solid rgba(255,255,255,0.12);
        box-shadow:0 12px 28px rgba(0,0,0,0.25);
        font-family:Arial, sans-serif;
    ">
        {heatspots}

        <div style="position:absolute; inset:0; z-index:2;">
            <div style="position:absolute; left:50%; top:0; width:2px; height:100%; background:rgba(255,255,255,0.75); transform:translateX(-50%);"></div>
            <div style="position:absolute; left:50%; top:50%; width:110px; height:110px; border:2px solid rgba(255,255,255,0.75); border-radius:50%; transform:translate(-50%, -50%);"></div>

            <div style="position:absolute; left:0; top:22%; width:15%; height:56%; border:2px solid rgba(255,255,255,0.75); border-left:none;"></div>
            <div style="position:absolute; left:0; top:36%; width:5.5%; height:28%; border:2px solid rgba(255,255,255,0.75); border-left:none;"></div>

            <div style="position:absolute; right:0; top:22%; width:15%; height:56%; border:2px solid rgba(255,255,255,0.75); border-right:none;"></div>
            <div style="position:absolute; right:0; top:36%; width:5.5%; height:28%; border:2px solid rgba(255,255,255,0.75); border-right:none;"></div>
        </div>

        <div style="
            position:absolute;
            left:1%;
            top:2%;
            background:rgba(6, 18, 28, 0.72);
            color:white;
            padding:6px 12px;
            border-radius:10px;
            font-weight:700;
            z-index:8;
        ">{casa}</div>

        <div style="
            position:absolute;
            right:1%;
            top:2%;
            background:rgba(6, 18, 28, 0.72);
            color:white;
            padding:6px 12px;
            border-radius:10px;
            font-weight:700;
            z-index:8;
        ">{fora}</div>

        {jogadores_html}
        {substitutions_html(reservas_casa, "Reservas", "left")}
        {substitutions_html(reservas_fora, "Reservas", "right")}
    </div>
    </body>
    </html>
    """
    components.html(campo_html, height=780, scrolling=False)

def render_lista_partidas(df_filtrado: pd.DataFrame, origem: str):
    global favoritos_ids

    if df_filtrado.empty:
        st.info("Nenhum jogo encontrado.")
        return

    grupos = sorted(df_filtrado["grupo"].dropna().unique())

    for i in range(0, len(grupos), 2):
        col1, col2 = st.columns(2)

        for idx, col in enumerate([col1, col2]):
            if i + idx >= len(grupos):
                continue

            grupo = grupos[i + idx]

            with col:
                st.markdown(f"### Grupo {grupo}")
                jogos = df_filtrado[df_filtrado["grupo"] == grupo].reset_index(drop=True)

                for j, row in jogos.iterrows():
                    partida_id = int(row["id"])
                    casa = row["selecao_casa"]
                    fora = row["selecao_fora"]

                    dia = f"{10 + (j % 10):02d}/06"
                    hora = f"{14 + (j % 6):02d}:00"

                    estadio = f"{row['estadio_nome']} - {row['estadio_cidade']}" if pd.notna(row["estadio_nome"]) else "Estádio a definir"
                    arbitro = row["arbitro_nome"] if pd.notna(row["arbitro_nome"]) else "Arbitro a definir"

                    codigo_casa = map_codigos.get(casa, "")
                    codigo_fora = map_codigos.get(fora, "")

                    c1, c2, c3 = st.columns([4, 1.1, 1.1])

                    with c1:
                        render_card_partida(casa, fora, codigo_casa, codigo_fora, dia, hora, grupo, estadio, arbitro)

                    with c2:
                        atual = st.session_state.get("partida_escolhida")
                        aberta = (
                            atual and atual.get("casa") == casa and atual.get("fora") == fora
                            and st.session_state.get("mostrar_escalacao") is True
                        )
                        texto_botao = "❌ Fechar" if aberta else "📋 Escalação"

                        if st.button(texto_botao, key=f"{origem}_esc_{partida_id}", use_container_width=True):
                            selecionar_partida(casa, fora)
                            st.rerun()

                    with c3:
                        eh_favorito = partida_id in favoritos_ids
                        texto = "★ Favorito" if eh_favorito else "☆ Favoritar"

                        if st.button(texto, key=f"{origem}_fav_{partida_id}", use_container_width=True):
                            if eh_favorito:
                                desfavoritar_partida(partida_id)
                            else:
                                favoritar_partida(partida_id)

                            st.cache_data.clear()
                            st.rerun()

if st.session_state["partida_escolhida"] and st.session_state["mostrar_escalacao"]:
    render_campo_duplo(
        st.session_state["partida_escolhida"]["casa"],
        st.session_state["partida_escolhida"]["fora"]
    )

st.title("🝆 Copa do Mundo 2026")
st.caption("Plataforma interativa de análise da Copa do Mundo FIFA")

abas = st.tabs([
    "Todos", "Favoritos", "Competições", "Seleções",
    "Estatísticas", "API", "Previsão", "Estádios", "Arbitros", "Jogadores"
])

with abas[0]:
    st.subheader("⚽ Todos os jogos")
    render_lista_partidas(df_partidas, "todos")

with abas[1]:
    st.subheader("⭝ Favoritos")
    favoritos_ids = carregar_ids_favoritos()
    if not favoritos_ids:
        st.info("Você ainda não favoritou nenhuma partida.")
    else:
        df_fav = df_partidas[df_partidas["id"].isin(list(favoritos_ids))].copy()
        render_lista_partidas(df_fav, "favoritos")

with abas[2]:
    st.subheader("🝆 Competições")
    grupos = sorted(df_partidas["grupo"].dropna().unique())
    grupo_sel = st.selectbox("Filtrar por grupo", ["Todos"] + grupos)
    df_comp = df_partidas if grupo_sel == "Todos" else df_partidas[df_partidas["grupo"] == grupo_sel]
    render_lista_partidas(df_comp, "competicoes")

with abas[3]:
    st.subheader("🌝 Seleções interativas")
    #st.caption("Passe o mouse para destacar. Clique para trocar o fundo.")

    cols = st.columns(4)
    idx = 0
    for _, row in df_selecoes.iterrows():
        nome = row["nome"]
        codigo = row["codigo"]

        with cols[idx % 4]:
            st.markdown(f"""
            <div class="custom-card">
                <img src="{bandeira_url(codigo)}" width="60">
                <div style="margin-top:8px;color:white;font-weight:600;">{nome}</div>
            </div>
            """, unsafe_allow_html=True)

            if st.button(f"Selecionar {nome}", key=f"sel_{nome}", use_container_width=True):
                st.session_state["fundo_time"] = nome
                st.rerun()
        idx += 1

    if st.button("Restaurar fundo padrão", use_container_width=True):
        st.session_state["fundo_time"] = None
        st.rerun()

with abas[4]:
    st.subheader("📊 Estatísticas comparativas")

    selecoes_validas_stats = sorted(df_selecoes["nome"].unique())

    c1, c2 = st.columns(2)
    with c1:
        time_a = st.selectbox("Seleção A", selecoes_validas_stats, key="stats_a")
    with c2:
        idx_b = 1 if len(selecoes_validas_stats) > 1 else 0
        time_b = st.selectbox("Seleção B", selecoes_validas_stats, index=idx_b, key="stats_b")

    if time_a == time_b:
        st.info("Escolha duas seleções diferentes para comparar.")
    else:
        forma_a, seq_a = score_forma(df_hist, time_a, n=5)
        forma_b, seq_b = score_forma(df_hist, time_b, n=5)
        h2h = confronto_direto_stats(df_hist, time_a, time_b)

        st.markdown("### Forma recente")
        f1, f2 = st.columns(2)

        with f1:
            st.markdown(f"#### {time_a}")
            st.metric("Overall Form", f"{forma_a}/100")
            render_forma_badges(seq_a)

        with f2:
            st.markdown(f"#### {time_b}")
            st.metric("Overall Form", f"{forma_b}/100")
            render_forma_badges(seq_b)

        st.markdown("---")
        st.markdown("### Confronto direto")

        if h2h["partidas"] == 0:
            st.info("Não há confrontos diretos suficientes entre essas seleções no histórico carregado.")
        else:
            st.caption(f"Partidas jogadas: {h2h['partidas']} | Desde {h2h['desde']}")

            a1, a2, a3 = st.columns(3)
            with a1:
                st.metric(f"Vitórias {time_a}", h2h["vitorias_a"])
            with a2:
                st.metric("Empates", h2h["empates"])
            with a3:
                st.metric(f"Vitórias {time_b}", h2h["vitorias_b"])

            b1, b2 = st.columns(2)
            with b1:
                st.markdown(f"""
                <div class="custom-card">
                    <h4 style="margin-bottom:10px;">{time_a}</h4>
                    <p><b>Maior vitória:</b> {h2h["maior_vitoria_a"] or "N/A"}</p>
                    <p><b>Total de gols:</b> {h2h["gols_a"]}</p>
                    <p><b>Média de gols:</b> {h2h["media_gols_a"]}</p>
                </div>
                """, unsafe_allow_html=True)

            with b2:
                st.markdown(f"""
                <div class="custom-card">
                    <h4 style="margin-bottom:10px;">{time_b}</h4>
                    <p><b>Maior vitória:</b> {h2h["maior_vitoria_b"] or "N/A"}</p>
                    <p><b>Total de gols:</b> {h2h["gols_b"]}</p>
                    <p><b>Média de gols:</b> {h2h["media_gols_b"]}</p>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### Últimos jogos")

        ult_a = montar_tabela_ultimos_jogos(df_hist, time_a, n=5)
        ult_b = montar_tabela_ultimos_jogos(df_hist, time_b, n=5)

        u1, u2 = st.columns(2)
        with u1:
            st.markdown(f"#### {time_a}")
            if ult_a.empty:
                st.info("Sem jogos suficientes.")
            else:
                st.dataframe(ult_a, use_container_width=True, hide_index=True)

        with u2:
            st.markdown(f"#### {time_b}")
            if ult_b.empty:
                st.info("Sem jogos suficientes.")
            else:
                st.dataframe(ult_b, use_container_width=True, hide_index=True)

with abas[5]:
    st.subheader("📡 API TheSportsDB")
    st.caption("Fonte: TheSportsDB (API gratuita).")

    opcoes_times = sorted(df_selecoes["nome"].unique())
    time_sel = st.selectbox("Seleção para consultar na API", opcoes_times)

    if st.button("Buscar estatísticas", key="buscar_api", use_container_width=True):
        team_info, err_team = buscar_time_api(time_sel)

        if err_team:
            st.error(f"Erro ao buscar time: {err_team}")
        else:
            c1, c2 = st.columns([1, 3])

            with c1:
                badge = team_info.get("strBadge")
                if badge:
                    st.image(badge, use_container_width=True)

            with c2:
                st.markdown(f"### {team_info.get('strTeam', time_sel)}")
                st.write(f"País: {team_info.get('strCountry', 'N/A')}")
                st.write(f"Liga: {team_info.get('strLeague', 'N/A')}")
                st.write(f"Estádio: {team_info.get('strStadium', 'N/A')}")

            eventos, err_eventos = buscar_ultimos_eventos_time(time_sel)
            st.markdown("#### Últimos jogos")

            if err_eventos:
                st.warning(err_eventos)
            elif not eventos:
                st.info("Nenhum evento encontrado.")
            else:
                linhas = []
                for ev in eventos[:8]:
                    linhas.append({
                        "Data": ev.get("dateEvent"),
                        "Competição": ev.get("strLeague"),
                        "Casa": ev.get("strHomeTeam"),
                        "Placar": f"{ev.get('intHomeScore', '-')}" + " x " + f"{ev.get('intAwayScore', '-')}",
                        "Fora": ev.get("strAwayTeam"),
                    })
                st.dataframe(pd.DataFrame(linhas), use_container_width=True, hide_index=True)

with abas[6]:
    st.subheader("🔮 Previsão com IA")

    model, scaler, classes, feature_names = carregar_modelo_previsao()

    if model is None:
        st.warning("Modelo ainda não treinado. Rode: python treinar_modelo_xgboost.py")
    else:
        selecoes_validas = sorted(df_jogadores["selecao"].unique())

        c1, c2 = st.columns(2)
        with c1:
            time_casa = st.selectbox("Seleção A", selecoes_validas, key="pred_casa")
        with c2:
            time_fora = st.selectbox(
                 "Seleção B",
                selecoes_validas,
                index=1 if len(selecoes_validas) > 1 else 0,
                key="pred_fora"
            )

        if time_casa == time_fora:
            st.info("Escolha seleções diferentes.")
        else:
            if st.button("Gerar previsão", use_container_width=True):
                probs = prever_partida_neutra(model, scaler, classes, feature_names, time_casa, time_fora)

                st.markdown(f"### {time_casa} x {time_fora}")

                d1, d2, d3 = st.columns(3)
                with d1:
                    st.metric(f"Vitória {time_casa}", f"{probs['casa'] * 100:.1f}%")
                with d2:
                    st.metric("Empate", f"{probs['empate'] * 100:.1f}%")
                with d3:
                    st.metric(f"Vitória {time_fora}", f"{probs['fora'] * 100:.1f}%")

                st.markdown("### 📊 Probabilidades")

                st.progress(probs["casa"])
                st.caption(f"{time_casa}: {probs['casa'] * 100:.1f}%")

                st.progress(probs["empate"])
                st.caption(f"Empate: {probs['empate'] * 100:.1f}%")

                st.progress(probs["fora"])
                st.caption(f"{time_fora}: {probs['fora'] * 100:.1f}%")

                mapa_final = {
                    "casa": f"✅ Tendência: {time_casa}",
                    "empate": "🤝 Tendência: Empate",
                    "fora": f"✅ Tendência: {time_fora}",
                }

                st.success(mapa_final[probs["predicao_final"]])

                maior_prob = max(probs["casa"], probs["empate"], probs["fora"])

                if maior_prob >= 0.75:
                    confianca = "Muito Alta"
                elif maior_prob >= 0.60:
                    confianca = "Alta"
                elif maior_prob >= 0.45:
                    confianca = "Média"
                else:
                    confianca = "Baixa"

                st.info(f"🎯 Confiança da previsão: {confianca}")

                df_probs = pd.DataFrame({
                    "Resultado": [f"Vitória {time_casa}", "Empate", f"Vitória {time_fora}"],
                    "Probabilidade": [probs["casa"], probs["empate"], probs["fora"]]
                })
                st.bar_chart(df_probs.set_index("Resultado"))
#CORRIGIDO
with abas[7]:
    st.subheader("🏟️ Estádios")
    ##st.caption("Enciclopédia visual dos estádios da Copa do Mundo 2026")

    busca_estadio = st.text_input(
        "🔎 Buscar estádio",
        placeholder="Digite nome, cidade ou país..."
    )

    df_wiki = df_estadios.copy()

    if busca_estadio:
        termo = busca_estadio.lower()
        df_wiki = df_wiki[
            df_wiki["nome"].str.lower().str.contains(termo, na=False) |
            df_wiki["cidade"].str.lower().str.contains(termo, na=False) |
            df_wiki["pais"].str.lower().str.contains(termo, na=False)
        ]

    if df_wiki.empty:
        st.info("Nenhum estádio encontrado.")
    else:
        cols = st.columns(3)

        for i, (_, row) in enumerate(df_wiki.iterrows()):
            with cols[i % 3]:

                foto = row["foto_url"] if row["foto_url"] else "https://images.unsplash.com/photo-1577223625816-7546f13df25d?w=1200"

                html_card = f"""
<div style="
    background: linear-gradient(180deg, rgba(15,23,42,0.96), rgba(3,7,18,0.96));
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 18px;
    overflow: hidden;
    margin-bottom: 16px;
    box-shadow: 0 10px 28px rgba(0,0,0,0.35);
    font-family: Arial, sans-serif;
">
    <img src="{foto}" style="
        width: 100%;
        height: 210px;
        object-fit: cover;
        display: block;
    ">

    <div style="padding: 16px;">
        <h3 style="margin: 0 0 8px 0; color: white;">
            {row["nome"]}
        </h3>

        <p style="margin: 4px 0; color: #cbd5e1;">
            📍 <b>Cidade:</b> {row["cidade"]}
        </p>

        <p style="margin: 4px 0; color: #cbd5e1;">
            🌎 <b>País:</b> {row["pais"]}
        </p>

        <hr style="border: none; border-top: 1px solid rgba(255,255,255,0.10); margin: 14px 0;">

        <p style="font-size: 13px; color: #94a3b8; line-height: 1.5;">
            Estádio sede da Copa do Mundo FIFA 2026. Clique abaixo para abrir a ficha completa.
        </p>
    </div>
</div>
"""

                components.html(html_card, height=430, scrolling=False)

                with st.expander(f"📖 Ver ficha wiki - {row['nome']}"):
                    st.image(foto, use_container_width=True)

                    c1, c2 = st.columns(2)

                    with c1:
                        st.metric("Cidade", row["cidade"])

                    with c2:
                        st.metric("País", row["pais"])

                    st.markdown("### 🏟️ Informações gerais")
                    st.write(f"**Nome:** {row['nome']}")
                    st.write(f"**Localização:** {row['cidade']} - {row['pais']}")

                    st.markdown("### ⚽ Jogos cadastrados neste estádio")

                    jogos_estadio = df_partidas[
                        df_partidas["estadio_nome"] == row["nome"]
                    ].copy()

                    if jogos_estadio.empty:
                        st.info("Nenhuma partida cadastrada para este estádio.")
                    else:
                        jogos_estadio = jogos_estadio.rename(columns={
                            "selecao_casa": "Casa",
                            "selecao_fora": "Fora",
                            "grupo": "Grupo",
                            "arbitro_nome": "Árbitro"
                        })

                        st.dataframe(
                            jogos_estadio[["Casa", "Fora", "Grupo", "Árbitro"]],
                            use_container_width=True,
                            hide_index=True
                        )

                    st.markdown("### 📌 Resumo Wiki")
                    st.info(
                        f"O {row['nome']} está localizado em {row['cidade']}, "
                        f"{row['pais']}, e faz parte da lista de estádios utilizados "
                        f"no projeto interativo da Copa do Mundo 2026."
                    )
#CORRIGDO
with abas[8]:
    st.subheader("🧑‍⚖️ Árbitros")
    #st.caption("Ficha dos árbitros e partidas vinculadas na Copa do Mundo 2026")

    busca_arbitro = st.text_input(
        "🔎 Buscar árbitro",
        placeholder="Digite nome ou país..."
    )

    df_wiki_arbitros = df_arbitros.copy()

    if busca_arbitro:
        termo = busca_arbitro.lower()
        df_wiki_arbitros = df_wiki_arbitros[
            df_wiki_arbitros["nome"].str.lower().str.contains(termo, na=False) |
            df_wiki_arbitros["pais"].str.lower().str.contains(termo, na=False)
        ]

    if df_wiki_arbitros.empty:
        st.info("Nenhum árbitro encontrado.")
    else:
        cols = st.columns(3)

        for i, (_, arb) in enumerate(df_wiki_arbitros.iterrows()):
            with cols[i % 3]:

                nome = arb["nome"]
                pais = arb["pais"]

                jogos = df_partidas[df_partidas["arbitro_nome"] == nome].copy()
                qtd_jogos = len(jogos)

                foto = f"https://ui-avatars.com/api/?name={nome.replace(' ', '+')}&background=111827&color=ffffff&size=256"

                html_card = f"""
<div style="
    background: linear-gradient(180deg, rgba(15,23,42,0.96), rgba(3,7,18,0.96));
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 18px;
    overflow: hidden;
    margin-bottom: 16px;
    box-shadow: 0 10px 28px rgba(0,0,0,0.35);
    font-family: Arial, sans-serif;
">
    <div style="
        padding: 22px 16px 12px 16px;
        text-align: center;
        background: radial-gradient(circle at top, rgba(34,197,94,0.20), rgba(15,23,42,0.96));
    ">
        <img src="{foto}" style="
            width: 96px;
            height: 96px;
            border-radius: 50%;
            object-fit: cover;
            border: 3px solid rgba(34,197,94,0.75);
            box-shadow: 0 0 22px rgba(34,197,94,0.35);
        ">

        <h3 style="margin: 12px 0 4px 0; color: white;">
            {nome}
        </h3>

        <p style="margin: 0; color: #94a3b8;">
            Árbitro FIFA
        </p>
    </div>

    <div style="padding: 16px;">
        <p style="margin: 4px 0; color: #cbd5e1;">
            🌎 <b>País:</b> {pais}
        </p>

        <p style="margin: 4px 0; color: #cbd5e1;">
            ⚽ <b>Jogos vinculados:</b> {qtd_jogos}
        </p>

        <hr style="border: none; border-top: 1px solid rgba(255,255,255,0.10); margin: 14px 0;">

        <p style="font-size: 13px; color: #94a3b8; line-height: 1.5;">
            Ficha resumida do árbitro com país de origem e partidas atribuídas no projeto.
        </p>
    </div>
</div>
"""

                components.html(html_card, height=365, scrolling=False)

                with st.expander(f"📖 Ver ficha wiki - {nome}"):

                    st.markdown(f"### 🧑‍⚖️ {nome}")

                    c1, c2, c3 = st.columns(3)

                    with c1:
                        st.metric("País", pais)

                    with c2:
                        st.metric("Jogos", qtd_jogos)

                    with c3:
                        st.metric("Função", "Árbitro")

                    st.markdown("### ⚽ Partidas vinculadas")

                    if jogos.empty:
                        st.info("Nenhuma partida vinculada.")
                    else:
                        jogos_exibir = jogos.rename(columns={
                            "selecao_casa": "Casa",
                            "selecao_fora": "Fora",
                            "grupo": "Grupo",
                            "estadio_nome": "Estádio"
                        })

                        st.dataframe(
                            jogos_exibir[["Casa", "Fora", "Grupo", "Estádio"]],
                            use_container_width=True,
                            hide_index=True
                        )

                    st.markdown("### 📌 Resumo Wiki")
                    st.info(
                        f"{nome} representa {pais} e está vinculado a "
                        f"{qtd_jogos} partida(s) no calendário do projeto da Copa do Mundo 2026."
                    )

with abas[9]:
    st.subheader("👥 Wiki dos Jogadores")
    st.caption("Elenco, titulares, reservas e notas por seleção")

    selecao_sel = st.selectbox(
        "Seleção",
        sorted(df_jogadores["selecao"].unique())
    )

    elenco = df_jogadores[df_jogadores["selecao"] == selecao_sel].copy()

    if elenco.empty:
        st.info("Nenhum jogador encontrado.")
    else:
        titulares = elenco[elenco["titular"] == 1].sort_values("numero")
        reservas = elenco[elenco["titular"] == 0].sort_values("numero")

        media_geral = elenco["rating"].mean()
        media_titulares = titulares["rating"].mean()
        melhor_jogador = elenco.sort_values("rating", ascending=False).iloc[0]

        c1, c2, c3 = st.columns(3)

        with c1:
            st.metric("Jogadores", len(elenco))

        with c2:
            st.metric("Média geral", f"{media_geral:.1f}")

        with c3:
            st.metric("Melhor jogador", melhor_jogador["nome"])

        st.markdown("---")

        busca_jogador = st.text_input(
            "🔎 Buscar jogador",
            placeholder="Digite nome, posição ou número..."
        )

        df_cards = elenco.copy()

        if busca_jogador:
            termo = busca_jogador.lower()
            df_cards = df_cards[
                df_cards["nome"].str.lower().str.contains(termo, na=False) |
                df_cards["posicao"].str.lower().str.contains(termo, na=False) |
                df_cards["numero"].astype(str).str.contains(termo, na=False)
            ]

        filtro_status = st.radio(
            "Filtrar elenco",
            ["Todos", "Titulares", "Reservas"],
            horizontal=True
        )

        if filtro_status == "Titulares":
            df_cards = df_cards[df_cards["titular"] == 1]
        elif filtro_status == "Reservas":
            df_cards = df_cards[df_cards["titular"] == 0]

        cols = st.columns(4)

        for i, (_, jogador) in enumerate(df_cards.sort_values(["titular", "numero"], ascending=[False, True]).iterrows()):
            with cols[i % 4]:

                nome = jogador["nome"]
                numero = jogador["numero"]
                posicao = jogador["posicao"]
                rating = float(jogador["rating"])
                titular = int(jogador["titular"]) == 1
                foto = jogador["foto_url"] if jogador["foto_url"] else f"https://ui-avatars.com/api/?name={nome.replace(' ', '+')}&background=111827&color=ffffff&size=256"

                status = "Titular" if titular else "Reserva"
                cor_status = "#22c55e" if titular else "#f59e0b"

                if rating >= 8.5:
                    nivel = "Craque"
                    cor_rating = "#facc15"
                elif rating >= 8.0:
                    nivel = "Destaque"
                    cor_rating = "#22c55e"
                elif rating >= 7.0:
                    nivel = "Regular"
                    cor_rating = "#60a5fa"
                else:
                    nivel = "Apoio"
                    cor_rating = "#94a3b8"

                html_card = f"""
<div style="
    background: linear-gradient(180deg, rgba(15,23,42,0.96), rgba(3,7,18,0.96));
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 18px;
    overflow: hidden;
    margin-bottom: 16px;
    box-shadow: 0 10px 28px rgba(0,0,0,0.35);
    font-family: Arial, sans-serif;
">
    <div style="
        padding: 20px 14px 12px 14px;
        text-align: center;
        background: radial-gradient(circle at top, rgba(34,197,94,0.18), rgba(15,23,42,0.96));
        position: relative;
    ">
        <div style="
            position:absolute;
            top:12px;
            left:12px;
            background:{cor_status};
            color:white;
            padding:5px 9px;
            border-radius:999px;
            font-size:11px;
            font-weight:800;
        ">
            {status}
        </div>

        <div style="
            position:absolute;
            top:12px;
            right:12px;
            background:#020617;
            color:{cor_rating};
            padding:5px 9px;
            border-radius:999px;
            font-size:12px;
            font-weight:900;
            box-shadow: 0 0 14px rgba(250,204,21,0.25);
        ">
            {rating:.1f}
        </div>

        <img src="{foto}" style="
            width: 105px;
            height: 105px;
            border-radius: 50%;
            object-fit: cover;
            border: 3px solid rgba(255,255,255,0.80);
            box-shadow: 0 0 22px rgba(34,197,94,0.28);
            margin-top: 20px;
        ">

        <h3 style="
            margin: 12px 0 4px 0;
            color: white;
            font-size: 18px;
            line-height: 1.2;
        ">
            {nome}
        </h3>

        <p style="margin: 0; color: #94a3b8;">
            #{numero} • {posicao}
        </p>
    </div>

    <div style="padding: 14px;">
        <p style="margin: 4px 0; color: #cbd5e1;">
            🇺🇳 <b>Seleção:</b> {selecao_sel}
        </p>

        <p style="margin: 4px 0; color: #cbd5e1;">
            ⭐ <b>Nível:</b> {nivel}
        </p>

        <hr style="border: none; border-top: 1px solid rgba(255,255,255,0.10); margin: 12px 0;">

        <p style="font-size: 13px; color: #94a3b8; line-height: 1.5;">
            Ficha wiki do jogador com número, posição, status no elenco e nota técnica.
        </p>
    </div>
</div>
"""

                components.html(html_card, height=390, scrolling=False)

                with st.expander(f"📖 Ver ficha - {nome}"):

                    st.image(foto, width=180)

                    st.markdown(f"### 👤 {nome}")

                    a1, a2, a3 = st.columns(3)

                    with a1:
                        st.metric("Número", numero)

                    with a2:
                        st.metric("Posição", posicao)

                    with a3:
                        st.metric("Nota", f"{rating:.1f}")

                    b1, b2 = st.columns(2)

                    with b1:
                        st.metric("Status", status)

                    with b2:
                        st.metric("Nível", nivel)

                    st.markdown("### 📌 Resumo Wiki")
                    st.info(
                        f"{nome} atua como {posicao} pela seleção {selecao_sel}. "
                        f"No elenco atual, está marcado como {status.lower()} "
                        f"e possui nota técnica {rating:.1f}."
                    )

        st.markdown("---")
        st.markdown("### 📋 Tabela completa do elenco")

        tabela = elenco.rename(columns={
            "nome": "Jogador",
            "numero": "Número",
            "posicao": "Posição",
            "rating": "Nota",
            "titular": "Titular"
        })

        tabela["Titular"] = tabela["Titular"].map({1: "Sim", 0: "Reserva"})

        st.dataframe(
            tabela[["Número", "Jogador", "Posição", "Nota", "Titular"]],
            use_container_width=True,
            hide_index=True
        )
