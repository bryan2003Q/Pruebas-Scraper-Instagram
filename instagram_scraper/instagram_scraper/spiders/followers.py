import scrapy
from scrapy_playwright.page import PageMethod
import json
import asyncio
import random
import os
from dotenv import load_dotenv

load_dotenv()

class FollowersSpider(scrapy.Spider):
    name = "followers"
    
    # --- CONFIGURACIÓN DE EXPORTACIÓN ---
    custom_settings = {
        'FEEDS': {
            'seguidores.csv': {
                'format': 'csv',
                'overwrite': True,
                'fields': ['Username', 'Name', 'Biography', 'Followers', 'Following'],
            },
        },
    }
    
    # --- TUS DATOS (Cargados desde .env) ---
    mi_usuario = os.getenv("INSTAGRAM_USER")
    mi_contrasena = os.getenv("INSTAGRAM_PASSWORD")
    usuario_objetivo = os.getenv("TARGET_USER")
    limite_seguidores = int(os.getenv("FOLLOWERS_LIMIT", 20))

    def start_requests(self):
        self.logger.info("🚀 Iniciando Proyecto con Scroll Inteligente...")
        yield scrapy.Request(
            url="https://www.instagram.com/accounts/login/",
            meta={
                "playwright": True,
                "playwright_include_page": True,
                "playwright_context_kwargs": {
                    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                },
            },
            callback=self.login_execution
        )

    async def login_execution(self, response):
        page = response.meta["playwright_page"]
        
        try:
            # 1. LOGIN
            await page.wait_for_selector("input[name='email']", timeout=15000)
            await page.fill("input[name='email']", self.mi_usuario)
            await page.fill("input[name='pass']", self.mi_contrasena)
            await page.click("div[aria-label='Log in'], div[aria-label='Log In']")
            
            # 2. VERIFICACIÓN
            await page.wait_for_selector("svg[aria-label='Inicio'], svg[aria-label='Home'], a[href='/']", timeout=20000)
            self.logger.info("✅ Login exitoso.")

            # 3. IR AL PERFIL Y ABRIR MODAL
            await page.goto(f"https://www.instagram.com/{self.usuario_objetivo}/")
            await page.wait_for_selector("header")
            await page.click(f"a[href='/{self.usuario_objetivo}/followers/']")
            await page.wait_for_selector("div[role='dialog']")
            await asyncio.sleep(2)

            # 4. FASE 1: EXTRAER USERNAMES CON SCROLL INTELIGENTE
            encontrados = set()
            intentos_sin_progreso = 0
            
            self.logger.info(f"🚀 Iniciando extracción con scroll inteligente (Objetivo: {self.limite_seguidores})")
            
            while len(encontrados) < self.limite_seguidores and intentos_sin_progreso < 10:
                conteo_inicial = len(encontrados)
                
                # Extraer nombres actuales parseando los links de forma robusta
                nuevos_nombres = await page.evaluate('''() => {
                    const dialog = document.querySelector('div[role="dialog"]');
                    if (!dialog) return [];
                    const links = Array.from(dialog.querySelectorAll('a[href*="/"]'));
                    return links.map(link => {
                        const href = link.getAttribute('href');
                        if (href && href.includes('/')) {
                            const parts = href.split('/').filter(p => p.length > 0);
                            const username = parts[0];
                            const ignore = ["explore", "reels", "direct", "accounts", "p", "legal", "help"];
                            if (username && !ignore.includes(username)) return username;
                        }
                        return null;
                    }).filter(name => name !== null);
                }''')
                
                for nombre in nuevos_nombres:
                    if len(encontrados) < self.limite_seguidores:
                        encontrados.add(nombre)
                
                if len(encontrados) > conteo_inicial:
                    intentos_sin_progreso = 0
                    self.logger.info(f"  ✓ Progreso: {len(encontrados)}/{self.limite_seguidores}")
                else:
                    intentos_sin_progreso += 1
                
                if len(encontrados) >= self.limite_seguidores:
                    break
                
                # --- EJECUTAR SCROLL INTELIGENTE ---
                # Busca qué div es el que realmente tiene el scroll habilitado
                scroll_success = await page.evaluate('''() => {
                    const dialog = document.querySelector('div[role="dialog"]');
                    if (!dialog) return false;
                    const divs = dialog.querySelectorAll('div');
                    for (let div of divs) {
                        if (div.scrollHeight > div.clientHeight * 1.1) {
                            div.scrollTop = div.scrollHeight;
                            return true;
                        }
                    }
                    return false;
                }''')
                
                if not scroll_success:
                    # Intento de respaldo manual
                    await page.evaluate("document.querySelector('div[role=\"dialog\"] ._aano').scrollTop += 1000")
                
                await asyncio.sleep(random.uniform(1.5, 2.5))

            lista_final = list(encontrados)
            self.logger.info(f"✨ Fase 1 Completada. Detallando {len(lista_final)} usuarios...")

            # 5. FASE 2: OBTENER DETALLES DE CADA UNO
            for user in lista_final:
                self.logger.info(f"🔍 Extrayendo datos de: {user}")
                api_url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={user}"
                
                try:
                    profile_data = await page.evaluate(f"""
                        async () => {{
                            const response = await fetch('{api_url}', {{
                                headers: {{ 'x-ig-app-id': '936619743392459' }}
                            }});
                            return response.json();
                        }}
                    """)
                    
                    u = profile_data['data']['user']
                    yield {
                        'Username': user,
                        'Name': u.get('full_name', ''),
                        'Biography': u.get('biography', '').replace('\n', ' '),
                        'Followers': u.get('edge_followed_by', {}).get('count', 0),
                        'Following': u.get('edge_follow', {}).get('count', 0)
                    }
                except Exception:
                    self.logger.warning(f"⚠️ Salteando {user} (perfil privado o error)")
                    yield {'Username': user, 'Name': 'N/A'}
                
                await asyncio.sleep(random.uniform(2, 4))

            self.logger.info("🏁 ¡Proceso completado! Archivo: seguidores.csv")

        except Exception as e:
            self.logger.error(f"❌ Error General: {str(e)}")
        finally:
            await page.close()
