# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import joblib
from sqlalchemy import create_engine
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report
from xgboost import XGBClassifier

CSV_PATH = "data_raw/fifa-world-cup-2022/international_matches.csv"
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
    "South Africa": "África do Sul",
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
    "Austria": "Áustria",
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


def detectar_coluna_competicao(df: pd.DataFrame):
    candidatas = [
        "tournament",
        "competition",
        "competition_name",
        "match_type",
        "league_name",
        "cup_name",
    ]
    for col in candidatas:
        if col in df.columns:
            return col
    return None


def classificar_tipo_jogo(valor: str) -> int:
    """
    0 = amistoso
    1 = oficial genérico
    2 = continental / eliminatórias / nations league etc
    3 = copa do mundo
    """
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


def tier_time(rank: float) -> int:
    if rank <= 10:
        return 3
    if rank <= 30:
        return 2
    return 1


def carregar_ratings_elenco() -> pd.DataFrame:
    engine = create_engine(DATABASE_URL)
    df_jogadores = pd.read_sql_query("""
        SELECT nome, selecao, rating, titular
        FROM jogadores
    """, engine)

    df_jogadores["selecao"] = df_jogadores["selecao"].apply(normalizar_nome_time)

    rows = []
    for selecao, grupo in df_jogadores.groupby("selecao"):
        titulares = grupo[grupo["titular"] == 1]
        reservas = grupo[grupo["titular"] == 0]

        rows.append({
            "team": selecao,
            "rating_titulares": float(titulares["rating"].mean()) if not titulares.empty else 6.5,
            "rating_reservas": float(reservas["rating"].mean()) if not reservas.empty else 6.0,
            "rating_total": float(grupo["rating"].mean()) if not grupo.empty else 6.3,
        })

    return pd.DataFrame(rows)


def get_match_type_weight(row: pd.Series) -> int:
    if "match_type_weight" in row.index:
        return int(row["match_type_weight"])
    return 1


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
        tipo_jogo = get_match_type_weight(row)

        if row["home_team"] == team:
            gm = row["home_score"]
            gs = row["away_score"]
        else:
            gm = row["away_score"]
            gs = row["home_score"]

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
            gm = row["home_score"]
            gs = row["away_score"]
        else:
            gm = row["away_score"]
            gs = row["home_score"]

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
        tipo_jogo = get_match_type_weight(row)
        soma_peso += tipo_jogo

        if row["home_team"] == casa:
            gc = row["home_score"]
            gf = row["away_score"]
        else:
            gc = row["away_score"]
            gf = row["home_score"]

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


df = pd.read_csv(CSV_PATH)

competition_col = detectar_coluna_competicao(df)
if competition_col:
    print(f"Coluna de competição detectada: {competition_col}")
    df["match_type_weight"] = df[competition_col].apply(classificar_tipo_jogo)
else:
    print("Nenhuma coluna de competição detectada. Usando peso padrão.")
    df["match_type_weight"] = 1

colunas_necessarias = [
    "date",
    "home_team",
    "away_team",
    "home_team_fifa_rank",
    "away_team_fifa_rank",
    "home_team_total_fifa_points",
    "away_team_total_fifa_points",
    "home_team_score",
    "away_team_score",
    "home_team_mean_defense_score",
    "home_team_mean_offense_score",
    "home_team_mean_midfield_score",
    "away_team_mean_defense_score",
    "away_team_mean_offense_score",
    "away_team_mean_midfield_score",
    "match_type_weight",
]

df = df[colunas_necessarias].copy()
df = df.dropna().copy()
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)

for col in [
    "home_team_fifa_rank",
    "away_team_fifa_rank",
    "home_team_total_fifa_points",
    "away_team_total_fifa_points",
    "home_team_score",
    "away_team_score",
    "home_team_mean_defense_score",
    "home_team_mean_offense_score",
    "home_team_mean_midfield_score",
    "away_team_mean_defense_score",
    "away_team_mean_offense_score",
    "away_team_mean_midfield_score",
    "match_type_weight",
]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna().reset_index(drop=True)
df["home_team"] = df["home_team"].apply(normalizar_nome_time)
df["away_team"] = df["away_team"].apply(normalizar_nome_time)

print(f"Dataset carregado: {len(df)} linhas válidas")

df_hist = df[[
    "date",
    "home_team",
    "away_team",
    "home_team_score",
    "away_team_score",
    "match_type_weight",
]].copy()

df_hist = df_hist.rename(columns={
    "date": "data_ref",
    "home_team_score": "home_score",
    "away_team_score": "away_score",
}).sort_values("data_ref").reset_index(drop=True)

df_elenco = carregar_ratings_elenco()
rating_map = df_elenco.set_index("team").to_dict("index")

features = []

for i in range(len(df)):
    row = df.iloc[i]
    data_jogo = row["date"]
    casa = row["home_team"]
    fora = row["away_team"]

    df_passado = df_hist[df_hist["data_ref"] < data_jogo].copy()
    if len(df_passado) < 50:
        continue

    casa_stats = stats_time_recente(df_passado, casa, n=10)
    fora_stats = stats_time_recente(df_passado, fora, n=10)

    casa_streaks = calcular_streaks(df_passado, casa, limite=10)
    fora_streaks = calcular_streaks(df_passado, fora, limite=10)

    h2h_stats = stats_h2h(df_passado, casa, fora, n=10)

    rating_casa = rating_map.get(casa, {"rating_titulares": 6.5, "rating_reservas": 6.0, "rating_total": 6.3})
    rating_fora = rating_map.get(fora, {"rating_titulares": 6.5, "rating_reservas": 6.0, "rating_total": 6.3})

    if row["home_team_score"] > row["away_team_score"]:
        target = 0
    elif row["home_team_score"] < row["away_team_score"]:
        target = 2
    else:
        target = 1

    forca_relativa = (
        (row["home_team_total_fifa_points"] + casa_stats["momentum"])
        - (row["away_team_total_fifa_points"] + fora_stats["momentum"])
    )

    equilibrio_forcas = abs(forca_relativa)

    rank_diff_abs = abs(float(row["home_team_fifa_rank"]) - float(row["away_team_fifa_rank"]))
    rank_ratio = (
        min(float(row["home_team_fifa_rank"]), float(row["away_team_fifa_rank"])) /
        max(float(row["home_team_fifa_rank"]), float(row["away_team_fifa_rank"]))
    )

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
    tier_casa = tier_time(float(row["home_team_fifa_rank"]))
    tier_fora = tier_time(float(row["away_team_fifa_rank"]))
    tier_diff = tier_casa - tier_fora

    features.append({
        "home_team_fifa_rank": row["home_team_fifa_rank"],
        "away_team_fifa_rank": row["away_team_fifa_rank"],
        "home_team_total_fifa_points": row["home_team_total_fifa_points"],
        "away_team_total_fifa_points": row["away_team_total_fifa_points"],

        "home_team_mean_offense_score": row["home_team_mean_offense_score"],
        "home_team_mean_defense_score": row["home_team_mean_defense_score"],
        "home_team_mean_midfield_score": row["home_team_mean_midfield_score"],
        "away_team_mean_offense_score": row["away_team_mean_offense_score"],
        "away_team_mean_defense_score": row["away_team_mean_defense_score"],
        "away_team_mean_midfield_score": row["away_team_mean_midfield_score"],

        "rank_diff": row["home_team_fifa_rank"] - row["away_team_fifa_rank"],
        "rank_diff_abs": rank_diff_abs,
        "rank_ratio": rank_ratio,
        "points_diff": row["home_team_total_fifa_points"] - row["away_team_total_fifa_points"],
        "attack_diff": row["home_team_mean_offense_score"] - row["away_team_mean_offense_score"],
        "defense_diff": row["home_team_mean_defense_score"] - row["away_team_mean_defense_score"],
        "midfield_diff": row["home_team_mean_midfield_score"] - row["away_team_mean_midfield_score"],

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

        "match_type_weight_atual": row["match_type_weight"],
        "mando": 1.0,
        "target": target,
    })

df_modelo = pd.DataFrame(features)
print(f"Dataset de features criado: {len(df_modelo)} linhas")

X = df_modelo.drop(columns=["target"])
y = df_modelo["target"]

split_idx = int(len(df_modelo) * 0.8)
X_train = X.iloc[:split_idx].copy()
X_test = X.iloc[split_idx:].copy()
y_train = y.iloc[:split_idx].copy()
y_test = y.iloc[split_idx:].copy()

print(f"Treino: {len(X_train)} linhas")
print(f"Teste: {len(X_test)} linhas")

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

weight_map = {
    0: 1.00,  # casa ##Neutro
    1: 2.50,  # empate
    2: 1.00   # fora ##Neutro
}
sample_weights = y_train.map(weight_map).values
print("Pesos por classe:", weight_map)

model = XGBClassifier(
    n_estimators=950,
    max_depth=5,
    learning_rate=0.025,
    subsample=0.92,
    colsample_bytree=0.92,
    gamma=0.10,
    min_child_weight=2,
    reg_lambda=1.3,
    reg_alpha=0.12,
    objective="multi:softprob",
    num_class=3,
    eval_metric="mlogloss",
    random_state=42
)

model.fit(X_train_scaled, y_train, sample_weight=sample_weights)

preds = model.predict(X_test_scaled)
acc = accuracy_score(y_test, preds)

print(f"\nAccuracy: {acc:.4f}\n")
print(classification_report(y_test, preds, target_names=["casa", "empate", "fora"]))

joblib.dump(model, "modelo_previsao.pkl")
joblib.dump(scaler, "scaler_previsao.pkl")
joblib.dump(["casa", "empate", "fora"], "classes_previsao.pkl")
joblib.dump(X.columns.tolist(), "features_previsao.pkl")

print(" Modelo salvo com sucesso.")
