# Instagram Scraper (Scrapy + Playwright)

Este proyecto es una herramienta de automatización diseñada para extraer información detallada de perfiles de Instagram de forma eficiente y segura. Utiliza una combinación de navegación real mediante navegador y peticiones optimizadas para obtener datos estructurados.

## 🚀 Funcionalidades Principales

- **Login Automatizado**: Manejo de sesiones para acceder a listas de seguidores privadas y públicas.
- **Scroll Inteligente**: Simulación de comportamiento humano para cargar listas largas de seguidores sin bloqueos.
- **Fase de Detalle**: No solo obtiene el nombre de usuario, sino que extrae biografía, conteo de seguidores y nombres completos.
- **Extracción de Posts y Comentarios**: Scrapeo avanzado de publicaciones, subtítulos y comentarios de perfiles específicos.
- **Análisis de Sentimientos con IA**: Integración con la API de Groq (Llama 3.1) para consolidar datos de interacción y generar conclusiones del sentimiento.
- **Manejo Seguro**: Implementación de archivos `.env` para proteger credenciales.
- **Exportación Automática**: Generación y almacenamiento de archivos JSON estructurados en una carpeta dedicada de resultados.

## 📂 Estructura de Archivos

```text
Scrapeo_Instagram/
├── .env                     # Credenciales y configuración (Usuario, Contraseña, Objetivo).
├── .gitignore               # Archivos excluidos del repositorio (Cache, CSVs, .env).
├── README.md                # Documentación del proyecto.
├── requirements.txt         # Librerías necesarias (Scrapy, Playwright, Dotenv, Groq).
└── instagram_scraper/       
    ├── resultados/          # Carpeta generada automáticamente para los archivos JSON y conclusiones.
    ├── sentiment_groq.py    # Script de Inteligencia Artificial para análisis de sentimiento con Llama 3.
    └── instagram_scraper/
        ├── spiders/
        │   ├── followers.py        # Crawler y lógica de extracción de seguidores.
        │   ├── instagram_posts.py  # Spider diseñado para extraer publicaciones, descripciones y comentarios.
        │   └── profile_info.py     # Spider orientado a la recolección de metadatos precisos del perfil.
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
3. Ejecuta el spider que necesites (dentro de la carpeta `instagram_scraper`):
   ```bash
  
   scrapy crawl profile_info
   scrapy crawl instagram_posts
   ```
4. Para realizar el análisis de sentimientos utilizando Groq, ejecuta el siguiente script pasando un archivo de publicaciones:
   ```bash
   python sentiment_groq.py resultados/posts_de_instagram_TU_ARCHIVO.json
   ```

Los datos extraídos y las conclusiones de la IA se almacenarán ordenadamente en la carpeta `instagram_scraper/resultados/`.
