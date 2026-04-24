import scrapy
from scrapy_playwright.page import PageMethod
import json
import asyncio
import random
import os
import datetime
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

class ProfileInfoSpider(scrapy.Spider):
    name = "profile_info"
    
    # --- EXPORT CONFIGURATION ---

    timestamp = datetime.datetime.now().strftime("%d_%m_%Y_%H-%M-%S")

    
    custom_settings = {
        'FEEDS': {
            f'resultados/perfil_info_{timestamp}.json': {
                'format': 'json',
                'overwrite': False,
                'fields': ['Username', 'Name', 'Biography', 'Followers', 'Following'],
            },
        },
    }
    
    # --- DATA FROM .ENV ---
    target_user = os.getenv("TARGET_USER")
    session_id = os.getenv("INSTAGRAM_SESSION_ID")
    user_id_cookie = os.getenv("INSTAGRAM_USER_ID")
    csrf_token = os.getenv("INSTAGRAM_CSRF_TOKEN")

    def start_requests(self):
        self.logger.info(f" Iniciando extracción de información de perfil para: {self.target_user}")
        yield scrapy.Request(
            url="https://www.instagram.com/",
            meta={
                "playwright": True,
                "playwright_include_page": True,
                "playwright_context_kwargs": {
                    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                },
            },
            callback=self.login_and_extract
        )

    async def login_and_extract(self, response):
        page = response.meta["playwright_page"]
        
        try:
            # LOGIN MEDIANTE INYECCIÓN DE COOKIES
            self.logger.info("Inyectando cookies de sesión...")
            cookies = [
                {'name': 'sessionid', 'value': self.session_id, 'domain': '.instagram.com', 'path': '/'},
                {'name': 'ds_user_id', 'value': self.user_id_cookie, 'domain': '.instagram.com', 'path': '/'},
                {'name': 'csrftoken', 'value': self.csrf_token, 'domain': '.instagram.com', 'path': '/'},
            ]

            await page.context.add_cookies(cookies)

             # NAVIGATE TO TARGET PROFILE
            self.logger.info(f"Navegando al perfil de {self.target_user}...")
            await page.goto(f"https://www.instagram.com/{self.target_user}/")
            
            try:
                
                await page.wait_for_selector("header", timeout=15000)
                self.logger.info(f"Perfil de {self.target_user} cargado correctamente.")
            except:
                self.logger.error("No se pudo cargar el perfil. Verifique las cookies o el nombre de usuario.")
                return

            api_url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={self.target_user}"
            
            self.logger.info("Consultando API interna para obtener detalles...")
            profile_data = await page.evaluate(f"""
                async () => {{
                    const response = await fetch('{api_url}', {{
                        headers: {{ 'x-ig-app-id': '936619743392459' }}
                    }});
                    return response.json();
                }}
            """)
            
            if profile_data and 'data' in profile_data and profile_data['data']['user']:
                u = profile_data['data']['user']
                yield {
                    'Username': self.target_user,
                    'Name': u.get('full_name', ''),
                    'Biography': u.get('biography', '').replace('\n', ' '),
                    'Followers': u.get('edge_followed_by', {}).get('count', 0),
                    'Following': u.get('edge_follow', {}).get('count', 0)
                }
                self.logger.info(f"✓ Información de {self.target_user} extraída con éxito.")
            else:
                self.logger.error("No se pudieron obtener los datos de la API. Es posible que el perfil sea privado o la sesión haya expirado.")

        except Exception as e:
            self.logger.error(f" Error General: {str(e)}")
        finally:
            await page.close()
