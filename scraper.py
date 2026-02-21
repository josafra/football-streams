import requests
import json
import os
import base64
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import re
import time

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_USER = "josafra"
GITHUB_REPO = "football-streams"
GITHUB_FILE = "data/partidos.json"
CONFIG_FILE = "data/config.json"

LIGAS_DISPONIBLES = {
    "LaLiga": 4335,
    "Premier League": 4328,
    "Champions League": 4480,
    "Europa League": 4481,
    "Serie A": 4332,
    "Bundesliga": 4331,
    "Ligue 1": 4334
}

WEBS_STREAMING = [
    "https://streamed.pk/category/football",
    "https://dlhd.link/index.php?cat=Soccer",
    "https://sportsbite.live/football",
    "https://sportyhunter.com/sport/football",
    "https://watchsports.to/",
    "https://crackstreams.blog/",
    "https://www.viprow.co/",
    "https://720pstreams.tv/",
    "https://hoofoot.ru/tv/",
    "https://ntvstream.cx/",
    "https://lmao.love/channels/",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def get_config_from_github():
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{CONFIG_FILE}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            content = base64.b64decode(r.json()["content"]).decode("utf-8")
            return json.loads(content)
    except Exception as e:
        print(f"Error leyendo config: {e}")
    return {"ligas_activas": list(LIGAS_DISPONIBLES.keys())}


def get_partidos_semana(ligas_activas):
    partidos = []
    hoy = datetime.now()
    fin_semana = hoy + timedelta(days=7)

    for liga_nombre in ligas_activas:
        if liga_nombre not in LIGAS_DISPONIBLES:
            continue
        liga_id = LIGAS_DISPONIBLES[liga_nombre]
        url = f"https://www.thesportsdb.com/api/v1/json/3/eventsnextleague.php?id={liga_id}"
        try:
            r = requests.get(url, timeout=15)
            data = r.json()
            eventos = data.get("events") or []
            print(f"Liga: {liga_nombre} | Partidos proximos: {len(eventos)}")
            for evento in eventos:
                fecha_str = evento.get("dateEvent", "")
                hora_str = evento.get("strTime", "00:00:00")
                if not fecha_str:
                    continue
                try:
                    fecha_dt = datetime.strptime(f"{fecha_str} {hora_str[:5]}", "%Y-%m-%d %H:%M")
                except:
                    fecha_dt = datetime.strptime(fecha_str, "%Y-%m-%d")
                if fecha_dt < hoy or fecha_dt > fin_semana:
                    continue
                home = evento.get("strHomeTeam", "")
                away = evento.get("strAwayTeam", "")
                partidos.append({
                    "liga": liga_nombre,
                    "partido": f"{home} vs {away}",
                    "home": home,
                    "away": away,
                    "fecha": fecha_dt.isoformat(),
                    "estado": "NS",
                    "streams": []
                })
            time.sleep(0.5)
        except Exception as e:
            print(f"Error obteniendo partidos de {liga_nombre}: {e}")

    return partidos


def buscar_streams_en_web(url_web, terminos_busqueda):
    resultados = []
    try:
        r = requests.get(url_web, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        texto_pagina = soup.get_text().lower()
        for termino in terminos_busqueda:
            if termino.lower() in texto_pagina:
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
                for iframe in soup.find_all("iframe", src=True):
                    src = iframe["src"]
                    if src.startswith("http"):
                        enlaces.append(src)
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
    for i, partido in enumerate(partidos):
        print(f"Buscando streams para: {partido['partido']}")
        home = partido["home"].lower().split()[0]
        away = partido["away"].lower().split()[0]
        terminos = [home, away]
        streams_encontrados = []
        for web in WEBS_STREAMING:
            resultado = buscar_streams_en_web(web, terminos)
            streams_encontrados.extend(resultado)
            time.sleep(0.3)
        partidos[i]["streams"] = streams_encontrados
        partidos[i]["ultima_actualizacion"] = datetime.now().isoformat()
    return partidos


def subir_json_github(datos, filepath):
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{filepath}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Content-Type": "application/json"
    }
    contenido = json.dumps(datos, ensure_ascii=False, indent=2)
    contenido_b64 = base64.b64encode(contenido.encode("utf-8")).decode("utf-8")
    sha = None
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        sha = r.json()["sha"]
    payload = {
        "message": f"Actualizacion {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "content": contenido_b64
    }
    if sha:
        payload["sha"] = sha
    r = requests.put(url, headers=headers, json=payload)
    if r.status_code in [200, 201]:
        print("JSON subido correctamente a GitHub")
    else:
        print(f"Error subiendo JSON: {r.status_code} - {r.text}")


def main():
    print("Iniciando Football Streams Scraper...")
    config = get_config_from_github()
    ligas_activas = config.get("ligas_activas", list(LIGAS_DISPONIBLES.keys()))
    print(f"Ligas activas: {', '.join(ligas_activas)}")
    print("Obteniendo partidos de la semana...")
    partidos = get_partidos_semana(ligas_activas)
    print(f"Total partidos encontrados: {len(partidos)}")
    print("Buscando streams...")
    partidos = buscar_todos_streams(partidos)
    resultado = {
        "ultima_actualizacion": datetime.now().isoformat(),
        "ligas_activas": ligas_activas,
        "total_partidos": len(partidos),
        "partidos": partidos
    }
    subir_json_github(resultado, GITHUB_FILE)
    print("Proceso completado!")


if __name__ == "__main__":
    main()
