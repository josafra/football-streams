import requests
import json
import os
import base64
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import re
import time

# ============================================================
# CONFIGURACIÓN - PON AQUÍ TUS CLAVES
# ============================================================
API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_KEY", "TU_API_KEY_AQUI")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "TU_GITHUB_TOKEN_AQUI")
GITHUB_USER = "josafra"
GITHUB_REPO = "football-streams"
GITHUB_FILE = "data/partidos.json"
CONFIG_FILE = "data/config.json"

# ============================================================
# LIGAS DISPONIBLES (ID de API-Football)
# ============================================================
LIGAS_DISPONIBLES = {
    "LaLiga": 140,
    "Premier League": 39,
    "Champions League": 2,
    "Europa League": 3,
    "Serie A": 135,
    "Bundesliga": 78,
    "Ligue 1": 61
}

# ============================================================
# WEBS DE STREAMING A BUSCAR
# ============================================================
WEBS_STREAMING = [
    "https://streamed.pk/category/football",
    "https://livetv.sx/es/allupcomingsports/1/",
    "https://dlhd.link/index.php?cat=Soccer",
    "https://sportsbite.live/football",
    "https://sportyhunter.com/sport/football",
    "https://es2.sportplus.live/",
    "https://watchsports.to/",
    "https://crackstreams.blog/",
    "https://www.viprow.co/",
    "https://720pstreams.tv/",
    "https://hoofoot.ru/tv/",
    "https://ntvstream.cx/",
    "https://lmao.love/channels/",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def get_config_from_github():
    """Lee la configuración de ligas desde GitHub"""
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{CONFIG_FILE}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            content = base64.b64decode(r.json()["content"]).decode("utf-8")
            return json.loads(content)
    except:
        pass
    # Config por defecto: todas las ligas activas
    return {"ligas_activas": list(LIGAS_DISPONIBLES.keys())}

def get_partidos_semana(ligas_activas):
    """Obtiene los partidos de la semana actual de la API"""
    partidos = []
    hoy = datetime.now()
    fin_semana = hoy + timedelta(days=7)
    fecha_desde = hoy.strftime("%Y-%m-%d")
    fecha_hasta = fin_semana.strftime("%Y-%m-%d")
    temporada = hoy.year if hoy.month >= 7 else hoy.year - 1

    for liga_nombre in ligas_activas:
        if liga_nombre not in LIGAS_DISPONIBLES:
            continue
        liga_id = LIGAS_DISPONIBLES[liga_nombre]
        url = f"https://v3.football.api-sports.io/fixtures"
        params = {
            "league": liga_id,
            "season": temporada,
            "from": fecha_desde,
            "to": fecha_hasta
        }
        headers_api = {
            "x-apisports-key": API_FOOTBALL_KEY
        }
        try:
            r = requests.get(url, headers=headers_api, params=params, timeout=15)
            data = r.json()
            for fixture in data.get("response", []):
                home = fixture["teams"]["home"]["name"]
                away = fixture["teams"]["away"]["name"]
                fecha = fixture["fixture"]["date"]
                estado = fixture["fixture"]["status"]["short"]
                partidos.append({
                    "liga": liga_nombre,
                    "partido": f"{home} vs {away}",
                    "home": home,
                    "away": away,
                    "fecha": fecha,
                    "estado": estado,
                    "streams": []
                })
            time.sleep(0.5)
        except Exception as e:
            print(f"Error obteniendo partidos de {liga_nombre}: {e}")

    return partidos

def buscar_streams_en_web(url_web, terminos_busqueda):
    """Busca un partido en una web de streaming"""
    resultados = []
    try:
        r = requests.get(url_web, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        texto_pagina = soup.get_text().lower()

        for termino in terminos_busqueda:
            if termino.lower() in texto_pagina:
                # Buscar enlaces relevantes
                enlaces = []
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    texto = a.get_text().lower()
                    if termino.lower() in texto or termino.lower() in href.lower():
                        if href.startswith("http"):
                            enlaces.append(href)
                        elif href.startswith("/"):
                            base = "/".join(url_web.split("/")[:3])
                            enlaces.append(base + href)

                # Buscar iframes y streams m3u8
                for iframe in soup.find_all("iframe", src=True):
                    src = iframe["src"]
                    if src.startswith("http"):
                        enlaces.append(src)

                # Buscar m3u8 en el código fuente
                m3u8_links = re.findall(r'https?://[^\s"\']+\.m3u8[^\s"\']*', r.text)
                enlaces.extend(m3u8_links)

                if enlaces:
                    resultados.append({
                        "fuente": url_web.split("/")[2],
                        "pagina": url_web,
                        "enlaces": list(set(enlaces))[:5]
                    })
                break

    except Exception as e:
        print(f"Error en {url_web}: {e}")

    return resultados

def buscar_todos_streams(partidos):
    """Para cada partido busca streams en todas las webs"""
    for i, partido in enumerate(partidos):
        print(f"Buscando streams para: {partido['partido']}")
        home = partido["home"].lower().split()[0]
        away = partido["away"].lower().split()[0]
        terminos = [home, away, partido["partido"].lower()]

        streams_encontrados = []
        for web in WEBS_STREAMING:
            resultado = buscar_streams_en_web(web, terminos)
            streams_encontrados.extend(resultado)
            time.sleep(0.3)

        partidos[i]["streams"] = streams_encontrados
        partidos[i]["ultima_actualizacion"] = datetime.now().isoformat()

    return partidos

def subir_json_github(datos, filepath):
    """Sube el JSON al repositorio de GitHub"""
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{filepath}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Content-Type": "application/json"
    }

    contenido = json.dumps(datos, ensure_ascii=False, indent=2)
    contenido_b64 = base64.b64encode(contenido.encode("utf-8")).decode("utf-8")

    # Obtener SHA si el archivo ya existe
    sha = None
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        sha = r.json()["sha"]

    payload = {
        "message": f"Actualización automática {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "content": contenido_b64
    }
    if sha:
        payload["sha"] = sha

    r = requests.put(url, headers=headers, json=payload)
    if r.status_code in [200, 201]:
        print(f"✅ JSON subido correctamente a GitHub: {filepath}")
    else:
        print(f"❌ Error subiendo JSON: {r.status_code} - {r.text}")

def main():
    print("🚀 Iniciando Football Streams Scraper...")

    # 1. Leer configuración de ligas desde GitHub
    config = get_config_from_github()
    ligas_activas = config.get("ligas_activas", list(LIGAS_DISPONIBLES.keys()))
    print(f"📋 Ligas activas: {', '.join(ligas_activas)}")

    # 2. Obtener partidos de la semana
    print("📅 Obteniendo partidos de la semana...")
    partidos = get_partidos_semana(ligas_activas)
    print(f"⚽ {len(partidos)} partidos encontrados")

    # 3. Buscar streams para cada partido
    print("🔍 Buscando streams...")
    partidos = buscar_todos_streams(partidos)

    # 4. Crear estructura final del JSON
    resultado = {
        "ultima_actualizacion": datetime.now().isoformat(),
        "ligas_activas": ligas_activas,
        "total_partidos": len(partidos),
        "partidos": partidos
    }

    # 5. Subir a GitHub
    subir_json_github(resultado, GITHUB_FILE)
    print("✅ Proceso completado!")

if __name__ == "__main__":
    main()
