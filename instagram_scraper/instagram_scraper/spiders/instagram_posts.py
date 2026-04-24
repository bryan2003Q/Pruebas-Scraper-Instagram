import scrapy
from scrapy_playwright.page import PageMethod
import json
import asyncio
import random
import os
import re
from dotenv import load_dotenv

load_dotenv()

class InstagramPostsSpider(scrapy.Spider):
    name = "instagram_posts"
    
    # --- CONFIGURACIÓN DE EXPORTACIÓN ---
    custom_settings = {
        'FEEDS': {
            'posts_de_instagram_%(time)s.csv': {
                'format': 'csv',
                'overwrite': False,
                'fields': ['Post_URL', 'Caption', 'Post_Author', 'Likes'],
            },
        },
    }
    
    # --- DATOS DEL .ENV ---
    usuario_objetivo = os.getenv("TARGET_USER")
    limite_posts = int(os.getenv("POSTS_LIMIT", 10))
    limite_comentarios = int(os.getenv("COMMENTS_LIMIT", 5))
    
    # Cookies
    session_id = os.getenv("INSTAGRAM_SESSION_ID")
    user_id_cookie = os.getenv("INSTAGRAM_USER_ID")
    csrf_token = os.getenv("INSTAGRAM_CSRF_TOKEN")

    def start_requests(self):
        self.logger.info(" Iniciando Spider de Posts con Cookies...")
        yield scrapy.Request(
            url="https://www.instagram.com/",
            meta={
                "playwright": True,
                "playwright_include_page": True,
                "playwright_context_kwargs": {
                    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                },
            },
            callback=self.login_and_navigate
        )

    async def login_and_navigate(self, response):
        page = response.meta["playwright_page"]
        
        try:
            # 1. INYECTAR COOKIES
            self.logger.info(" Inyectando cookies para la sesión de posts...")
            cookies = [
                {'name': 'sessionid', 'value': self.session_id, 'domain': '.instagram.com', 'path': '/'},
                {'name': 'ds_user_id', 'value': self.user_id_cookie, 'domain': '.instagram.com', 'path': '/'},
                {'name': 'csrftoken', 'value': self.csrf_token, 'domain': '.instagram.com', 'path': '/'},
            ]
            await page.context.add_cookies(cookies)
            
            # 2. IR AL PERFIL
            self.logger.info(f" Navegando al perfil de {self.usuario_objetivo}...")
            await page.goto(f"https://www.instagram.com/{self.usuario_objetivo}/")
            
            # 3. VERIFICACIÓN
            try:
                await page.wait_for_selector("svg[aria-label='Inicio'], svg[aria-label='Home'], a[href='/']", timeout=15000)
                self.logger.info(" Sesión validada correctamente.")
            except:
                self.logger.warning(" No se pudo verificar la sesión. Asegúrate de que las cookies en .env sean vigentes.")
            
            # Esperar a que cargue el contenido del perfil
            await page.wait_for_selector("header")
            self.logger.info(f" Perfil de {self.usuario_objetivo} cargado. Listo para extraer posts.")
            
            # 4. FASE 2: IDENTIFICAR Y HACER CLIC EN EL PRIMER POST
            self.logger.info(" Buscando publicaciones en el perfil...")
            
            # Esperamos a que al menos una publicación sea visible
            await page.wait_for_selector("a[href*='/p/']", timeout=10000)
            
            # Obtenemos la lista de todos los posts cargados en la cuadrícula
            posts = await page.query_selector_all("a[href*='/p/']")
            
            if posts:
                self.logger.info(f" Se detectaron {len(posts)} publicaciones visibles.")
                
                # --- BUCLE PARA EXTRAER MÚLTIPLES POSTS (Definido por POSTS_LIMIT en .env) ---
                for i in range(self.limite_posts):
                    self.logger.info(f" \n>>> PROCESANDO PUBLICACIÓN {i+1} DE {self.limite_posts} <<<")
                    
                    if i == 0:
                        # Abrir la primera publicación
                        await page.evaluate("el => el.click()", posts[0])
                    else:
                        # Navegar a la siguiente publicación usando el botón "Siguiente" del modal
                        try:
                            # Selector para el botón "Siguiente" (funciona para español e inglés)
                            next_button_selector = " button:has(svg[aria-label='Next']), ._aaqg button"
                            await page.click(next_button_selector, timeout=8000)
                            # Esperamos a que el contenido cambie y se estabilice
                            await asyncio.sleep(4)
                        except Exception as e:
                            self.logger.warning(f" No se pudo navegar a la siguiente publicación: {e}")
                            break

                    # Esperamos a que aparezca el modal (el \"pop-up\") del post
                    try:
                        await page.wait_for_selector("article[role='presentation']", timeout=15000)
                        self.logger.info(f" Publicación {i+1} abierta con éxito.")
                    except:
                        self.logger.warning(f" El modal de la publicación {i+1} no cargó a tiempo.")
                        continue
                    
                    # Pausa para estabilizar la carga del contenido y comentarios
                    await asyncio.sleep(3)

                    # 5. FASE 3: EXTRAER DATOS
                    self.logger.info(" Extrayendo datos de la publicación...")
                    
                    # Extraer el AUTOR
                    try:
                        post_author = await page.inner_text("article header h2 a, article header a")
                        post_author = post_author.split('\n')[0].strip()
                        if not post_author:
                            post_author = self.usuario_objetivo
                        self.logger.info(f" [Autor] {post_author}")
                    except Exception as e:
                        self.logger.warning(f" Error al extraer autor: {e}")
                        post_author = self.usuario_objetivo

                    # Extraer el POSTEO (Caption)
                    try:
                        caption_text = await page.inner_text("article h1, article span._ap3a")
                        self.logger.info(f" [Posteo] {caption_text[:50]}...")
                    except:
                        caption_text = "No se pudo extraer el posteo principal"

                    # Extraer ME GUSTA (Likes) de la publicación
                    try:
                        likes_selector = "article section a[href*='/liked_by/'], article section span:has-text('me gusta'), article section span:has-text('likes'), article section span.x1vvkbs"
                        raw_likes = await page.inner_text(likes_selector, timeout=5000)
                        
                        # Extraer solo el número (ej: "4,580")
                        match = re.search(r'([\d\.,]+)', raw_likes)
                        likes_text = match.group(1) if match else "0"
                        
                        self.logger.info(f" [Me Gusta] {likes_text}")
                    except:
                        likes_text = "0"

                    # --- GUARDAR EN EL CSV (POST ORIGINAL) ---
                    yield {
                        'Post_URL': page.url,
                        'Caption': caption_text.replace('\n', ' ').strip(),
                        'Post_Author': post_author,
                        'Likes': likes_text
                    }

                    # --- EXTRAER Y GUARDAR COMENTARIOS ---
                    try:
                        self.logger.info(f" Extrayendo hasta {self.limite_comentarios} comentarios...")
                        comments_data = await page.evaluate(f"""(limit) => {{
                            const items = Array.from(document.querySelectorAll('article ul li'));
                            const results = [];
                            for (let i = 1; i < items.length; i++) {{
                                if (results.length >= limit) break;
                                const li = items[i];
                                const link = Array.from(li.querySelectorAll('a')).find(a => a.innerText.trim().length > 0);
                                const text = li.querySelector('span._ap3a');
                                
                                // Extraer likes del comentario
                                let cLikes = "0";
                                const likesBtn = li.querySelector('button._a9ze');
                                if (likesBtn) {{
                                    const btnText = likesBtn.innerText.trim();
                                    // Usar regex para extraer solo el número
                                    const match = btnText.match(/([\d\.,]+)/);
                                    cLikes = match ? match[1] : "0";
                                }}

                                if (link && text) {{
                                    results.push({{
                                        user: link.innerText.trim().split('\\n')[0],
                                        text: text.innerText.trim(),
                                        likes: cLikes
                                    }});
                                }}
                            }}
                            return results;
                        }}""", self.limite_comentarios)

                        for idx, c in enumerate(comments_data, 1):
                            yield {
                                'Post_URL': page.url,
                                'Caption': c['text'].replace('\n', ' ').strip(),
                                'Post_Author': c['user'],
                                'Likes': c.get('likes', '0')
                            }
                        
                        if not comments_data:
                            self.logger.warning(" No se encontraron comentarios adicionales válidos.")
                                
                    except Exception as e:
                        self.logger.warning(f" Error al extraer comentarios: {e}")

                self.logger.info(" Finalizada la extracción de las publicaciones.")
                
            else:
                self.logger.warning(" No se encontraron publicaciones visibles en este perfil.")
            
        except Exception as e:
            self.logger.error(f" Error en ejecución: {str(e)}")
        finally:
            await asyncio.sleep(2)
            await page.close()

    def closed(self, reason):
        """Este método se ejecuta automáticamente cuando el spider termina"""
        import glob
        import subprocess
        import sys
        
        self.logger.info("🤖 Iniciando integración con análisis de sentimientos...")
        try:
            # Buscar el archivo CSV más reciente
            list_of_files = glob.glob('posts_de_instagram_*.csv')
            if not list_of_files:
                self.logger.warning("No se encontró ningún archivo CSV para analizar.")
                return
                
            latest_file = max(list_of_files, key=os.path.getctime)
            self.logger.info(f"📂 Archivo a analizar: {latest_file}")
            
            # Ruta relativa al script asumiendo que se ejecuta desde la raíz de instagram_scraper
            script_path = os.path.join(os.getcwd(), 'sentiment_huggin_face.py')
            
            if os.path.exists(script_path):
                # Lanzar en un proceso separado para que la consola muestre su progreso
                self.logger.info("🚀 Lanzando análisis... Revisa la consola para ver el progreso.")
                subprocess.Popen([sys.executable, script_path, latest_file])
            else:
                self.logger.error(f"No se encontró el script en: {script_path}")
                
        except Exception as e:
            self.logger.error(f"Error al iniciar el análisis automático: {e}")
