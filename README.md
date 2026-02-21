# ⚽ Football Streams

Buscador automático de streams de fútbol. Obtiene los partidos de la semana y busca enlaces de streaming automáticamente.

## 🚀 Configuración en 3 pasos

### Paso 1 - Añadir secretos en GitHub
Ve a tu repositorio → Settings → Secrets and variables → Actions → New repository secret

Añade estos dos secretos:
- `API_FOOTBALL_KEY` → tu clave de api-sports.io
- `GITHUB_TOKEN` → se genera automáticamente, no hace falta añadirlo

### Paso 2 - Activar GitHub Actions
Ve a la pestaña **Actions** de tu repositorio y activa los workflows.

### Paso 3 - Ejecutar manualmente la primera vez
En Actions → Football Streams Scraper → Run workflow

## 📱 URL del JSON para la app
```
https://raw.githubusercontent.com/josafra/football-streams/main/data/partidos.json
```

## ⏰ Ejecución automática
El script se ejecuta automáticamente cada día a las 7:00 AM (hora España).

## 🏆 Ligas incluidas
- LaLiga
- Premier League  
- Champions League
- Europa League
- Serie A
- Bundesliga
- Ligue 1
