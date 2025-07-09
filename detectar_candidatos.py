import tweepy
import gspread
from google.oauth2.service_account import Credentials
import json
import os
import time
from datetime import datetime

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

def setup_twitter_api():
    bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
    if not bearer_token:
        print("❌ Error: TWITTER_BEARER_TOKEN no encontrado")
        return None
    return tweepy.Client(bearer_token=bearer_token, wait_on_rate_limit=True)

def connect_to_sheets():
    credentials = get_google_credentials()
    if credentials:
        return gspread.authorize(credentials)
    return None

def get_last_tweet_id(sheet):
    try:
        all_values = sheet.get_all_values()
        if len(all_values) > 1:
            last_row = all_values[-1]
            if len(last_row) >= 5:
                return last_row[4]
    except Exception as e:
        print(f"⚠️ Error obteniendo último tweet ID: {e}")
    return None

def monitor_tweets():
    print("🚀 Iniciando monitoreo continuo de tweets (todos, sin filtro)...")
    print(f"⏰ Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    twitter_client = setup_twitter_api()
    gc = connect_to_sheets()
    if not twitter_client or not gc:
        print("❌ Error: No se pudieron configurar las APIs")
        return

    try:
        sheet = gc.open("tweets_candidatos").sheet1
        print("✅ Hoja de cálculo encontrada")
    except gspread.SpreadsheetNotFound:
        print("📝 Creando nueva hoja de cálculo...")
        spreadsheet = gc.create("tweets_candidatos")
        sheet = spreadsheet.sheet1
        sheet.append_row(['usuario', 'contenido', 'fecha', 'url', 'id_tweet', 'estado', 'tipo'])
        print("✅ Hoja de cálculo creada")

    existing_ids = set()
    try:
        existing_data = sheet.col_values(5)
        existing_ids = set(existing_data[1:])
        print(f"📋 {len(existing_ids)} tweets ya en la base de datos")
    except:
        print("📋 Base de datos vacía")

    last_tweet_id = get_last_tweet_id(sheet)
    if last_tweet_id:
        print(f"🔄 Continuando desde tweet ID: {last_tweet_id}")
    else:
        print("🆕 Empezando desde ahora")

    ciclo = 0

    while True:
        ciclo += 1
        print(f"\n🔄 Ciclo #{ciclo} - {datetime.now().strftime('%H:%M:%S')}")
        candidatos_encontrados = 0
        tweets_procesados = 0

        try:
            # Query: todos los tweets y retweets con comentario en español
            query = '(lang:es) (-is:retweet OR is:quote)'
            search_params = {
                'query': query,
                'tweet_fields': ['created_at', 'author_id', 'public_metrics', 'context_annotations', 'referenced_tweets'],
                'user_fields': ['username', 'name', 'verified'],
                'expansions': ['author_id', 'referenced_tweets.id'],
                'max_results': 10
            }
            if last_tweet_id:
                search_params['since_id'] = last_tweet_id

            tweets = tweepy.Paginator(
                twitter_client.search_recent_tweets,
                **search_params
            ).flatten(limit=50)

            for tweet in tweets:
                tweets_procesados += 1
                if str(tweet.id) in existing_ids:
                    continue

                tweet_type = "original"
                if hasattr(tweet, 'referenced_tweets') and tweet.referenced_tweets:
                    for ref in tweet.referenced_tweets:
                        if ref.type == "quoted":
                            tweet_type = "retweet_con_comentario"
                            break

                if tweet_type in ["original", "retweet_con_comentario"]:
                    user = None
                    if hasattr(tweet, 'includes') and tweet.includes and 'users' in tweet.includes:
                        user = next((u for u in tweet.includes['users'] if u.id == tweet.author_id), None)
                    if user:
                        tweet_data = [
                            user.username,
                            tweet.text.replace('\n', ' ').replace('\r', ' ')[:500],
                            tweet.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                            f"https://twitter.com/{user.username}/status/{tweet.id}",
                            str(tweet.id),
                            'pendiente',
                            tweet_type
                        ]
                        sheet.append_row(tweet_data)
                        candidatos_encontrados += 1
                        existing_ids.add(str(tweet.id))
                        last_tweet_id = str(tweet.id)
                        print(f"✅ Guardado: @{user.username} ({tweet_type})")
                        print(f"   📝 {tweet.text[:80]}...")

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
    try:
        monitor_tweets()
    except KeyboardInterrupt:
        print("\n🛑 Monitoreo detenido por el usuario")
    except Exception as e:
        print(f"❌ Error crítico: {e}")
        print("🔄 Reiniciando en 60 segundos...")
        time.sleep(60)
        main()

if __name__ == "__main__":
    main()
