import json
import os
import sys
from dotenv import load_dotenv
from groq import Groq

def analyze_sentiments_groq(json_path):
   
    load_dotenv()
    
    # Verificar clave API
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("ERROR: No se encontró GROQ_API_KEY en el archivo .env")
        return
        
    if not os.path.exists(json_path):
        print(f" ERROR: El archivo {json_path} no existe.")
        return

    print(f"Cargando archivo: {json_path}")
    
    #  Leer archivo JSON
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error al leer el JSON: {e}")
        return

    if not data:
        print("El archivo JSON está vacío.")
        return

    #  Consolidar el contenido en un solo texto (para ahorrar tokens)
    print("Consolidando contenido para enviar a Groq...")
    
    texto_consolidado = "A continuación te presento los datos extraídos de un post de Instagram (y sus comentarios):\n\n"
    
    for idx, item in enumerate(data, 1):
        autor = item.get("Post_Author", "Desconocido")
        caption = item.get("Caption", "").strip()
        likes = item.get("Likes", "0")
       
        if not caption or caption == "No se pudo extraer el posteo ":
            continue
            
        texto_consolidado += f"[{idx}] Autor: {autor} | Likes: {likes} | Mensaje: {caption}\n"


    client = Groq(api_key=api_key)
    

    prompt = f"""
Actúa como un experto analista de datos de redes sociales. 
He extraído un post de Instagram y sus respectivos comentarios.

{texto_consolidado}

Basándote **exclusivamente** en el contenido proporcionado arriba:
1. Dame una conclusión general sobre el sentimiento predominante (Positivo, Negativo o Neutro).
2. Explica brevemente por qué llegaste a esa conclusión, mencionando las reacciones o comentarios más
 relevantes. **MUY IMPORTANTE: Cada vez que cites o des un ejemplo de un comentario, debes mencionar 
 explícitamente el nombre de su autor.**
3. Menciona qué impacto crees que tiene el número de "Likes" en el contexto de estos mensajes.

Sé conciso y directo en tu análisis.
"""

    print("Enviando petición a la API de Groq (Llama3)...")
    
  
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama-3.1-8b-instant", 
            temperature=0.3,
        )
        
        conclusion = chat_completion.choices[0].message.content
        
        print("RESULTADO DEL ANÁLISIS DE GROQ")
        print(conclusion)
        
        
        output_path = json_path.replace('.json', '_conclusion_groq.txt')
        with open(output_path, 'w', encoding='utf-8') as out_f:
            out_f.write("=== ANÁLISIS DE SENTIMIENTOS (GROQ) ===\n\n")
            out_f.write(conclusion)
            
        print(f"Conclusión guardada exitosamente en: {output_path}")

    except Exception as e:
        print(f" Error en la llamada a la API de Groq: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        analyze_sentiments_groq(sys.argv[1])
    else:
        print(" ERROR: Debes proporcionar la ruta de un archivo JSON.")
        print("Ejemplo: python sentiment_groq.py resultados/posts_de_instagram_24_04_2026_14-52-04.json")
