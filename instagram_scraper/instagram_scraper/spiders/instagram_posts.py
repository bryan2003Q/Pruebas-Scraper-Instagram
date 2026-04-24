import scrapy
from scrapy_playwright.page import PageMethod
import json
import asyncio
import os
import re
import datetime
from dotenv import load_dotenv

load_dotenv()

class InstagramPostsSpider(scrapy.Spider):
    name = "instagram_posts"
    
    # --- EXPORT CONFIGURATION ---
    # We generate a readable timestamp: Day_Month_Year_Hour-Minutes-Seconds
    timestamp = datetime.datetime.now().strftime("%d_%m_%Y_%H-%M-%S")
    
    custom_settings = {
        'FEEDS': {
            f'resultados/posts_de_instagram_{timestamp}.json': {
                'format': 'json',
                'overwrite': False,
                'fields': ['Post_URL', 'Caption', 'Post_Author', 'Likes'],
            },
        },
    }
    
    # --- TARGET DATA FROM .ENV ---
    target_user = os.getenv("TARGET_USER")
    posts_limit = int(os.getenv("POSTS_LIMIT", 10))
    comments_limit = int(os.getenv("COMMENTS_LIMIT", 5))
    
    # Cookies for Authentication
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
            self.logger.info(" Inyectando cookies para la sesión de posts...")
            cookies = [
                {'name': 'sessionid', 'value': self.session_id, 'domain': '.instagram.com', 'path': '/'},
                {'name': 'ds_user_id', 'value': self.user_id_cookie, 'domain': '.instagram.com', 'path': '/'},
                {'name': 'csrftoken', 'value': self.csrf_token, 'domain': '.instagram.com', 'path': '/'},
            ]
            await page.context.add_cookies(cookies)
            
            self.logger.info(f" Navegando al perfil de {self.target_user}...")
            await page.goto(f"https://www.instagram.com/{self.target_user}/")
            
            try:
                await page.wait_for_selector("svg[aria-label='Inicio'], svg[aria-label='Home'], a[href='/']", timeout=15000)
                self.logger.info(" Sesión validada correctamente.")
            except:
                self.logger.warning(" No se pudo verificar la sesión. Asegúrate de que las cookies en .env sean vigentes.")
            
            await page.wait_for_selector("header")
            self.logger.info(f" Perfil de {self.target_user} cargado. Listo para extraer posts.")
            
            self.logger.info(" Buscando publicaciones en el perfil...")
            
            await page.wait_for_selector("a[href*='/p/']", timeout=10000)
            
            post_elements = await page.query_selector_all("a[href*='/p/']")
            
            if post_elements:
                self.logger.info(f" Se detectaron {len(post_elements)} publicaciones visibles.")
                
                for post_index in range(self.posts_limit):
                    self.logger.info(f" \n>>> PROCESANDO PUBLICACIÓN {post_index + 1} DE {self.posts_limit} <<<")
                    
                    if post_index == 0:
                        await page.evaluate("el => el.click()", post_elements[0])
                    else:
                        try:
                            next_button_selector = " button:has(svg[aria-label='Next']), ._aaqg button"
                            await page.click(next_button_selector, timeout=8000)
                            await asyncio.sleep(4)
                        except Exception as e:
                            self.logger.warning(f" No se pudo navegar a la siguiente publicación: {e}")
                            break

                    try:
                        await page.wait_for_selector("article[role='presentation']", timeout=15000)
                        self.logger.info(f" Publicación {post_index + 1} abierta con éxito.")
                    except:
                        self.logger.warning(f" El modal de la publicación {post_index + 1} no cargó a tiempo.")
                        continue
                    
                    await asyncio.sleep(3)

                    self.logger.info(" Extrayendo datos de la publicación...")
                    
                    try:
                        post_author = await page.inner_text("article header h2 a, article header a")
                        post_author = post_author.split('\n')[0].strip()
                        if not post_author:
                            post_author = self.target_user
                        self.logger.info(f" [Autor] {post_author}")
                    except Exception as e:
                        self.logger.warning(f" Error al extraer autor: {e}")
                        post_author = self.target_user

                    try:
                        caption_text = await page.inner_text("article h1, article span._ap3a")
                        self.logger.info(f" [Posteo] {caption_text[:50]}...")
                    except:
                        caption_text = "No se pudo extraer el posteo principal"

                    try:
                        likes_selector = "article section a[href*='/liked_by/'], article section span:has-text('me gusta'), article section span:has-text('likes'), article section span.x1vvkbs"
                        raw_likes = await page.inner_text(likes_selector, timeout=5000)
                        
                        match = re.search(r'([\d\.,]+)', raw_likes)
                        likes_text = match.group(1) if match else "0"
                        
                        self.logger.info(f" [Me Gusta] {likes_text}")
                    except:
                        likes_text = "0"

                    yield {
                        'Post_URL': page.url,
                        'Caption': caption_text.replace('\n', ' ').strip(),
                        'Post_Author': post_author,
                        'Likes': likes_text
                    }

                    try:
                        self.logger.info(f" Extrayendo hasta {self.comments_limit} comentarios...")
                        comments_data = await page.evaluate(f"""(limit) => {{
                            const comment_items = Array.from(document.querySelectorAll('article ul li'));
                            const extracted_comments = [];
                            for (let i = 1; i < comment_items.length; i++) {{
                                if (extracted_comments.length >= limit) break;
                                const comment_element = comment_items[i];
                                const author_link = Array.from(comment_element.querySelectorAll('a')).find(a => a.innerText.trim().length > 0);
                                const comment_text_element = comment_element.querySelector('span._ap3a');
                                
                                let comment_likes_count = "0";
                                const likes_button = comment_element.querySelector('button._a9ze');
                                if (likes_button) {{
                                    const button_text = likes_button.innerText.trim();
                                    const match = button_text.match(/([\d\.,]+)/);
                                    comment_likes_count = match ? match[1] : "0";
                                }}
                                
                                if (author_link && comment_text_element) {{
                                    extracted_comments.push({{
                                        user: author_link.innerText.trim().split('\\n')[0],
                                        text: comment_text_element.innerText.trim(),
                                        likes: comment_likes_count
                                    }});
                                }}
                            }}
                            return extracted_comments;
                        }}""", self.comments_limit)

                        for comment_index, comment in enumerate(comments_data, 1):
                            yield {
                                'Post_URL': page.url,
                                'Caption': comment['text'].replace('\n', ' ').strip(),
                                'Post_Author': comment['user'],
                                'Likes': comment.get('likes', '0')
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

