# Instagram Scraper (Scrapy + Playwright)

Este proyecto es una herramienta de automatización diseñada para extraer información detallada de perfiles de Instagram de forma eficiente y segura. Utiliza una combinación de navegación real mediante navegador y peticiones optimizadas para obtener datos estructurados.

## 🚀 Funcionalidades Principales

- **Login Automatizado**: Manejo de sesiones para acceder a listas de seguidores privadas y públicas.
- **Scroll Inteligente**: Simulación de comportamiento humano para cargar listas largas de seguidores sin bloqueos.
- **Fase de Detalle**: No solo obtiene el nombre de usuario, sino que extrae biografía, conteo de seguidores y nombres completos.
- **Manejo Seguro**: Implementación de archivos `.env` para proteger credenciales.
- **Exportación Automática**: Generación de archivos CSV con los resultados.

## 📂 Estructura de Archivos

```text
Scrapeo_Instagram/
├── .env                     # Credenciales y configuración (Usuario, Contraseña, Objetivo).
├── .gitignore               # Archivos excluidos del repositorio (Cache, CSVs, .env).
├── README.md                # Documentación del proyecto.
├── requirements.txt         # Librerías necesarias (Scrapy, Playwright, Dotenv).
└── instagram_scraper/       
    └── instagram_scraper/
        ├── spiders/
        │   └── followers.py # Lógica principal del crawler y login.
        ├── settings.py      # Configuración de Playwright y tiempos de espera.
        ├── pipelines.py     # Procesamiento y limpieza de datos extraídos.
        └── middlewares.py   # Manejo de agentes de usuario y peticiones.
```

## 🛠️ Requisitos Técnicos

Para ejecutar este proyecto necesitas:

1. Python 3.10+
2. Las librerías listadas en `requirements.txt`.
3. Instalar los navegadores de Playwright:
   ```bash
   playwright install chromium
   ```

## 🏎️ Guía de Ejecución

1. Clona el repositorio.
2. Crea tu archivo `.env` basándote en la configuración de seguridad explicada.
3. Ejecuta el spider principal:
   ```bash
   scrapy crawl followers
   ```

Los resultados se guardarán automáticamente en `seguidores.csv`.
