# -*- coding: utf-8 -*-
import itertools
import random
import time
import requests
import psycopg2

API_KEY = "123"
BASE_API = f"https://www.thesportsdb.com/api/v1/json/{API_KEY}"

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "copa2026",
    "user": "postgres",
    "password": "admin",
  #  "client_encoding": "utf8"
}

MAPA_SELECOES_API = {
    "Brasil": "Brazil",
    "Alemanha": "Germany",
    "Espanha": "Spain",
    "França": "France",
    "Inglaterra": "England",
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
    "África do Sul": "South Africa",
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
    "Cabo Verde": "Cape Verde",
    "Senegal": "Senegal",
    "Noruega": "Norway",
    "Áustria": "Austria",
    "Argélia": "Algeria",
    "Jordânia": "Jordan",
    "Colômbia": "Colombia",
    "Uzbequistão": "Uzbekistan",
    "Croácia": "Croatia",
    "Gana": "Ghana",
    "Panamá": "Panama",
}

def nome_selecao_api(nome: str) -> str:
    return MAPA_SELECOES_API.get(nome, nome)

def avatar_url(nome: str) -> str:
    nome = str(nome).replace(" ", "+")
    return f"https://ui-avatars.com/api/?name={nome}&background=1f2937&color=ffffff&size=128"

def buscar_foto_jogador_api(nome_jogador: str, selecao: str):
    try:
        response = requests.get(
            f"{BASE_API}/searchplayers.php",
            params={"p": nome_jogador},
            timeout=15
        )
        response.raise_for_status()
        data = response.json()
        players = data.get("player") if data else None

        if not players:
            return None

        selecao_api = nome_selecao_api(selecao).lower()

        for p in players:
            equipe = (p.get("strTeam") or "").lower()
            thumb = p.get("strThumb") or p.get("strCutout") or p.get("strRender")
            if thumb and selecao_api in equipe:
                return thumb

        for p in players:
            thumb = p.get("strThumb") or p.get("strCutout") or p.get("strRender")
            if thumb:
                return thumb

        return None
    except Exception:
        return None

grupos = {
    "A": [("México", "mx"), ("África do Sul", "za"), ("Coreia do Sul", "kr"), ("Haiti", "ht")],
    "B": [("Canadá", "ca"), ("Suíça", "ch"), ("Catar", "qa"), ("Curaçao", "cw")],
    "C": [("Brasil", "br"), ("Marrocos", "ma"), ("Escócia", "gb"), ("Arábia Saudita", "sa")],
    "D": [("Estados Unidos", "us"), ("Austrália", "au"), ("Paraguai", "py"), ("Jordânia", "jo")],
    "E": [("Alemanha", "de"), ("Equador", "ec"), ("Costa do Marfim", "ci"), ("Panamá", "pa")],
    "F": [("Países Baixos", "nl"), ("Japão", "jp"), ("Tunísia", "tn"), ("Uruguai", "uy")],
    "G": [("Bélgica", "be"), ("Peru", "pe"), ("Camarões", "cm"), ("Colômbia", "co")],
    "H": [("Espanha", "es"), ("Portugal", "pt"), ("França", "fr"), ("Argentina", "ar")]
}

estadios = [
    ("Atlanta Stadium", "Atlanta", "USA", "https://dynamic-media-cdn.tripadvisor.com/media/photo-o/10/91/f4/a6/images-from-chick-fil.jpg?w=1000&h=-1&s=1"),
    ("Boston Stadium", "Boston", "USA", "https://i2-prod.mirror.co.uk/article36338558.ece/ALTERNATES/s1200f/2_GettyImages-2226070081.jpg"),
    ("Dallas Stadium", "Dallas", "USA", "https://www.dallasfwc26.com/wp-content/uploads/2023/05/Dronegenuity-Dallas-Cowboys-11-1024x682.jpg"),
    ("Houston Stadium", "Houston", "USA", "https://cdn.houstonpublicmedia.org/wp-content/uploads/2019/08/22171208/IMG_0692copy.jpg?_gl=1*1wpmre1*_gcl_au*MjM5NTEyOTQ4LjE3ODA1ODY3NjY."),
    ("Kansas City Stadium", "Kansas City", "USA", "https://upload.wikimedia.org/wikipedia/commons/a/ac/Aerial_view_of_Arrowhead_Stadium_08-31-2013.jpg"),
    ("Los Angeles Stadium", "Los Angeles", "USA", "https://media-cdn.tripadvisor.com/media/attractions-splice-spp-674x446/12/37/0e/47.jpg"),
    ("Miami Stadium", "Miami", "USA", "https://upload.wikimedia.org/wikipedia/commons/f/f7/200127-H-PX819-0092.jpg"),
    ("New York Stadium", "New York", "USA", "https://upload.wikimedia.org/wikipedia/commons/e/ec/New_York_Stadium_-_geograph.org.uk_-_4179716.jpg"),
    ("Philadelphia Stadium", "Philadelphia", "USA", "https://upload.wikimedia.org/wikipedia/commons/a/a1/Lincoln_Financial_Field_%28Aerial_view%29.jpg"),
    ("San Francisco Stadium", "San Francisco", "USA", "https://collect.fifa.com/blog/wp-content/uploads/2025/10/photo_6036269466301172689_y.jpg"),
    ("Seattle Stadium", "Seattle", "USA", "https://blog.ticketmaster.com/wp-content/uploads/step-inside-lumen-field.png"),
    ("Toronto Stadium", "Toronto", "Canadá", "https://www.toronto.ca/wp-content/uploads/2026/03/96c3-SJ90025-scaled.jpg"),
    ("Vancouver Stadium", "Vancouver", "Canadá", "https://images.spaicelabs.com/images/flus6j8v/production/37d069f71f67b4591905dfab4aa98bb4c9703e07-2048x1360.jpg?w=3840&fm=webp&q=75&fit=max"),
    ("Guadalajara Stadium", "Guadalajara", "México", "https://xeniaevents.com/wp-content/uploads/2026/04/Estadio-Akron-tensile-membrane-structure-grandstand-04.jpg"),
    ("Mexico City Stadium", "Cidade do México", "México", "https://xeniaevents.com/wp-content/uploads/2026/04/20211012_Estadio_Azteca-copy.png"),
    ("Monterrey Stadium", "Monterrey", "México", "https://i0.wp.com/xeniaevents.com/wp-content/uploads/2026/04/Estadio_BBVA_Bancomer_1.jpg?w=1200&ssl=1"),
]

arbitros = [
    ("Raphael Claus", "Brasil"),
    ("Wilton Sampaio", "Brasil"),
    ("Facundo Tello", "Argentina"),
    ("Tori Penso", "Estados Unidos"),
    ("César Ramos", "México"),
    ("Danny Makkelie", "Países Baixos"),
    ("Szymon Marciniak", "Polônia"),
    ("Michael Oliver", "Inglaterra"),
    ("Ismail Elfath", "Estados Unidos"),
    ("Anderson Daronco", "Brasil"),
]

elencos_especiais = {
    "Brasil": [
        ("Alisson", 1, "Goleiro"),
        ("Danilo", 2, "Lateral"),
        ("Marquinhos", 3, "Zagueiro"),
        ("Gabriel Magalhães", 4, "Zagueiro"),
        ("Casemiro", 5, "Meio-campo"),
        ("Guilherme Arana", 6, "Lateral"),
        ("Vinícius Júnior", 7, "Atacante"),
        ("Bruno Guimarães", 8, "Meio-campo"),
        ("Richarlison", 9, "Atacante"),
        ("Lucas Paquetá", 10, "Meio-campo"),
        ("Rodrygo", 11, "Atacante"),
        ("Bento", 12, "Goleiro"),
        ("Bremer", 14, "Zagueiro"),
        ("André", 15, "Meio-campo"),
        ("Endrick", 18, "Atacante"),
    ],
    "Argentina": [
        ("Emiliano Martínez", 1, "Goleiro"),
        ("Molina", 4, "Lateral"),
        ("Cristian Romero", 13, "Zagueiro"),
        ("Otamendi", 19, "Zagueiro"),
        ("Tagliafico", 3, "Lateral"),
        ("De Paul", 7, "Meio-campo"),
        ("Enzo Fernández", 8, "Meio-campo"),
        ("Mac Allister", 20, "Meio-campo"),
        ("Messi", 10, "Atacante"),
        ("Julián Álvarez", 9, "Atacante"),
        ("Di María", 11, "Atacante"),
        ("Armani", 12, "Goleiro"),
        ("Paredes", 5, "Meio-campo"),
        ("Lisandro Martínez", 6, "Zagueiro"),
        ("Lautaro Martínez", 22, "Atacante"),
    ],
    "França": [
        ("Maignan", 1, "Goleiro"),
        ("Koundé", 5, "Lateral"),
        ("Upamecano", 4, "Zagueiro"),
        ("Saliba", 17, "Zagueiro"),
        ("Theo Hernández", 22, "Lateral"),
        ("Tchouaméni", 8, "Meio-campo"),
        ("Camavinga", 6, "Meio-campo"),
        ("Griezmann", 7, "Meio-campo"),
        ("Dembélé", 11, "Atacante"),
        ("Mbappé", 10, "Atacante"),
        ("Kolo Muani", 12, "Atacante"),
        ("Samba", 16, "Goleiro"),
        ("Konaté", 15, "Zagueiro"),
        ("Zaïre-Emery", 18, "Meio-campo"),
        ("Coman", 20, "Atacante"),
    ],
    "Marrocos": [
        ("Yassine Bounou", 1, "Goleiro"),
        ("Achraf Hakimi", 2, "Lateral"),
        ("Noussair Mazraoui", 3, "Lateral"),
        ("Sofyan Amrabat", 4, "Meio-campo"),
        ("Nayef Aguerd", 5, "Zagueiro"),
        ("Romain Saïss", 6, "Zagueiro"),
        ("Hakim Ziyech", 7, "Atacante"),
        ("Azzedine Ounahi", 8, "Meio-campo"),
        ("Youssef En-Nesyri", 9, "Atacante"),
        ("Sofiane Boufal", 17, "Atacante"),
        ("Munir El Kajoui", 12, "Goleiro"),
        ("Abde Ezzalzouli", 11, "Atacante"),
        ("Selim Amallah", 15, "Meio-campo"),
        ("Bilal El Khannouss", 23, "Meio-campo"),
        ("Ayoub El Kaabi", 19, "Atacante"),
    ]
}

conn = psycopg2.connect(**DB_CONFIG)
cursor = conn.cursor()

cursor.execute("DROP TABLE IF EXISTS favoritos CASCADE")
cursor.execute("DROP TABLE IF EXISTS jogadores CASCADE")
cursor.execute("DROP TABLE IF EXISTS partidas CASCADE")
cursor.execute("DROP TABLE IF EXISTS arbitros CASCADE")
cursor.execute("DROP TABLE IF EXISTS estadios CASCADE")
cursor.execute("DROP TABLE IF EXISTS selecoes CASCADE")

cursor.execute("""
CREATE TABLE selecoes (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome TEXT NOT NULL,
    codigo TEXT NOT NULL,
    grupo TEXT NOT NULL
)
""")

cursor.execute("""
CREATE TABLE estadios (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome TEXT NOT NULL,
    cidade TEXT NOT NULL,
    pais TEXT NOT NULL,
    foto_url TEXT
)
""")

cursor.execute("""
CREATE TABLE arbitros (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome TEXT NOT NULL,
    pais TEXT NOT NULL
)
""")

cursor.execute("""
CREATE TABLE partidas (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    selecao_casa TEXT NOT NULL,
    selecao_fora TEXT NOT NULL,
    gols_casa INTEGER DEFAULT 0,
    gols_fora INTEGER DEFAULT 0,
    grupo TEXT NOT NULL,
    estadio_id INTEGER,
    arbitro_id INTEGER,
    CONSTRAINT fk_estadio FOREIGN KEY (estadio_id) REFERENCES estadios(id),
    CONSTRAINT fk_arbitro FOREIGN KEY (arbitro_id) REFERENCES arbitros(id)
)
""")

cursor.execute("""
CREATE TABLE jogadores (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome TEXT NOT NULL,
    numero INTEGER NOT NULL,
    posicao TEXT NOT NULL,
    selecao TEXT NOT NULL,
    rating REAL NOT NULL,
    titular INTEGER NOT NULL,
    foto_url TEXT
)
""")

cursor.execute("""
CREATE TABLE favoritos (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    partida_id INTEGER NOT NULL UNIQUE,
    CONSTRAINT fk_partida_favorita FOREIGN KEY (partida_id) REFERENCES partidas(id) ON DELETE CASCADE
)
""")

for grupo, times in grupos.items():
    for nome, codigo in times:
        cursor.execute(
            "INSERT INTO selecoes (nome, codigo, grupo) VALUES (%s, %s, %s)",
            (nome, codigo, grupo)
        )

for estadio in estadios:
    cursor.execute("""
        INSERT INTO estadios (nome, cidade, pais, foto_url)
        VALUES (%s, %s, %s, %s)
    """, estadio)

for arbitro in arbitros:
    cursor.execute("""
        INSERT INTO arbitros (nome, pais)
        VALUES (%s, %s)
    """, arbitro)

cursor.execute("SELECT id FROM estadios ORDER BY id")
estadios_ids = [row[0] for row in cursor.fetchall()]

cursor.execute("SELECT id FROM arbitros ORDER BY id")
arbitros_ids = [row[0] for row in cursor.fetchall()]

idx_estadio = 0
idx_arbitro = 0

for grupo, times in grupos.items():
    nomes = [t[0] for t in times]
    for casa, fora in itertools.combinations(nomes, 2):
        estadio_id = estadios_ids[idx_estadio % len(estadios_ids)]
        arbitro_id = arbitros_ids[idx_arbitro % len(arbitros_ids)]

        cursor.execute("""
            INSERT INTO partidas (
                selecao_casa, selecao_fora, gols_casa, gols_fora, grupo, estadio_id, arbitro_id
            )
            VALUES (%s, %s, 0, 0, %s, %s, %s)
        """, (casa, fora, grupo, estadio_id, arbitro_id))

        idx_estadio += 1
        idx_arbitro += 1

cursor.execute("SELECT nome FROM selecoes ORDER BY nome")
selecoes_db = [row[0] for row in cursor.fetchall()]

for selecao in selecoes_db:
    jogadores = elencos_especiais.get(selecao)

    if jogadores is None:
        jogadores = [
            (f"{selecao} Goleiro", 1, "Goleiro"),
            (f"{selecao} Lateral D", 2, "Lateral"),
            (f"{selecao} Zagueiro 1", 3, "Zagueiro"),
            (f"{selecao} Zagueiro 2", 4, "Zagueiro"),
            (f"{selecao} Meio 1", 5, "Meio-campo"),
            (f"{selecao} Lateral E", 6, "Lateral"),
            (f"{selecao} Atacante 1", 7, "Atacante"),
            (f"{selecao} Meio 2", 8, "Meio-campo"),
            (f"{selecao} Atacante 2", 9, "Atacante"),
            (f"{selecao} Meio 3", 10, "Meio-campo"),
            (f"{selecao} Atacante 3", 11, "Atacante"),
            (f"{selecao} Reserva 1", 12, "Goleiro"),
            (f"{selecao} Reserva 2", 13, "Zagueiro"),
            (f"{selecao} Reserva 3", 14, "Meio-campo"),
            (f"{selecao} Reserva 4", 15, "Atacante"),
        ]

    for idx, (nome, numero, posicao) in enumerate(jogadores):
        titular = 1 if idx < 11 else 0
        rating = round(random.uniform(6.2, 8.9), 1)

        cursor.execute("""
            INSERT INTO jogadores (nome, numero, posicao, selecao, rating, titular, foto_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (nome, numero, posicao, selecao, rating, titular, None))

conn.commit()

print("Buscando fotos dos jogadores na API...")
cursor.execute("SELECT id, nome, selecao, foto_url FROM jogadores")
todos_jogadores = cursor.fetchall()

for jogador_id, nome_jogador, selecao, foto_atual in todos_jogadores:
    if foto_atual:
        continue

    foto = buscar_foto_jogador_api(nome_jogador, selecao)
    if not foto:
        foto = avatar_url(nome_jogador)

    cursor.execute(
        "UPDATE jogadores SET foto_url = %s WHERE id = %s",
        (foto, jogador_id)
    )
    print(f"✔ {selecao} - {nome_jogador}")
    time.sleep(0.15)

conn.commit()
cursor.close()
conn.close()

print("Banco PostgreSQL criado com sucesso.")
