import tweepy
import gspread
from google.oauth2.service_account import Credentials
import json
import os
import time
from datetime import datetime

# --- CONFIGURACIÓN GOOGLE SHEETS ---
def get_google_credentials():
    creds_json = os.getenv('GOOGLE_CREDENTIALS')
    if creds_json:
        creds_dict = json.loads(creds_json)
        credentials = Credentials.from_service_account_info(creds_dict)
        return credentials.with_scopes([
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ])
    return None

def connect_to_sheets():
    credentials = get_google_credentials()
    if credentials:
        return gspread.authorize(credentials)
    return None

# --- CONFIGURACIÓN TWITTER ---
def setup_twitter_api():
    bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
    if not bearer_token:
        print("❌ Error: TWITTER_BEARER_TOKEN no encontrado")
        return None
    return tweepy.Client(bearer_token=bearer_token, wait_on_rate_limit=True)

# --- OBTENER ÚLTIMO TWEET GUARDADO ---
def get_last_tweet_id(sheet):
    try:
        all_values = sheet.get_all_values()
        if len(all_values) > 1:
            last_row = all_values[-1]
            if len(last_row) >= 1:
                return last_row[0]  # tweet_id es la primera columna
    except Exception as e:
        print(f"⚠️ Error obteniendo último tweet ID: {e}")
    return None

# --- MONITOREO Y ESCRITURA ---
def monitor_user_tweets(username):
    print(f"🚀 Iniciando monitoreo de tweets de @{username} ...")
    print(f"⏰ Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    twitter_client = setup_twitter_api()
    gc = connect_to_sheets()
    if not twitter_client or not gc:
        print("❌ Error: No se pudieron configurar las APIs")
        return

    # --- ABRIR O CREAR HOJA ---
    try:
        sheet = gc.open("tweets_candidatos").sheet1
        print("✅ Hoja de cálculo encontrada")
    except gspread.SpreadsheetNotFound:
        print("📝 Creando nueva hoja de cálculo...")
        spreadsheet = gc.create("tweets_candidatos")
        sheet = spreadsheet.sheet1
        sheet.append_row(['tweet_id', 'texto', 'url', 'comentario', 'estado'])
        print("✅ Hoja de cálculo creada")

    # --- OBTENER IDS EXISTENTES ---
    existing_ids = set()
    try:
        existing_data = sheet.col_values(1)  # tweet_id es la primera columna
        existing_ids = set(existing_data[1:])  # saltar cabecera
        print(f"📋 {len(existing_ids)} tweets ya en la base de datos")
    except:
        print("📋 Base de datos vacía")

    # --- OBTENER USER ID ---
    try:
        user = twitter_client.get_user(username=username)
        user_id = user.data.id
        print(f"👤 User ID de @{username}: {user_id}")
    except Exception as e:
        print(f"❌ Error obteniendo user_id de @{username}: {e}")
        return

    ciclo = 0

    while True:
        ciclo += 1
        print(f"\n🔄 Ciclo #{ciclo} - {datetime.now().strftime('%H:%M:%S')}")
        candidatos_encontrados = 0

        try:
            # --- OBTENER TWEETS DEL USUARIO ---
            tweets = twitter_client.get_users_tweets(
                id=user_id,
                max_results=20,  # máximo permitido por la API en cada llamada
                tweet_fields=['created_at', 'author_id']
            )

            if not tweets.data:
                print("⚠️ No se encontraron tweets nuevos.")
            else:
                for tweet in tweets.data:
                    tweet_id = str(tweet.id)
                    if tweet_id in existing_ids:
                        continue

                    texto = tweet.text.replace('\n', ' ').replace('\r', ' ')[:500]
                    url = f"https://twitter.com/{username}/status/{tweet.id}"
                    comentario = ""
                    estado = "pendiente"

                    # --- ESCRIBIR EN LA HOJA ---
                    sheet.append_row([tweet_id, texto, url, comentario, estado])
                    candidatos_encontrados += 1
                    existing_ids.add(tweet_id)
                    print(f"✅ Guardado: {tweet_id}")

            print(f"🎯 Ciclo #{ciclo}: {candidatos_encontrados} nuevos tweets guardados")
            print(f"⏳ Esperando 5 minutos hasta el próximo ciclo...")
            time.sleep(300)  # 5 minutos

        except tweepy.TooManyRequests:
            print(f"⏸️ Rate limit alcanzado. Esperando 15 minutos...")
            time.sleep(900)
            continue
        except Exception as e:
            print(f"❌ Error general: {e}")
            print("🔄 Esperando 1 minuto antes de reintentar...")
            time.sleep(60)
            continue

def main():
    # Cambia aquí el usuario que quieres monitorizar (sin @)
    username = "jmilei"  # <-- REEMPLAZA por el usuario deseado
    monitor_user_tweets(username)

if __name__ == "__main__":
    main()
