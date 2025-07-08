import tweepy
import gspread
import pandas as pd
import os
import json
from google.oauth2.service_account import Credentials
import gspread


# === 1. Configuración de credenciales ===
BEARER_TOKEN = "AAAAAAAAAAAAAAAAAAAAAPTA2wEAAAAAKmpzcWqKNwk5bXTyQLqDVw%2FkbD4%3DV3cut6SLnP4XSM0kMtcghYeci7UlPBnzESlD6JBrH7bDONf6Kz"
client = tweepy.Client(bearer_token=BEARER_TOKEN, wait_on_rate_limit=True)

# === 2. Google Sheets ===
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])
creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
gc = gspread.authorize(creds)

# === 3. Usuario objetivo ===
usuario = "jmilei"  # Cambia esto por el usuario que quieres analizar
user = client.get_user(username=usuario)
user_id = user.data.id

# === 4. Leer IDs ya guardados ===
ids_existentes = set([row[0] for row in worksheet.get_all_values()[1:]])

# === 5. Leer el último tweet procesado (si existe) ===
ultimo_id_file = "ultimo_id.txt"
since_id = None
if os.path.exists(ultimo_id_file):
    with open(ultimo_id_file, "r") as f:
        since_id = f.read().strip() or None

# === 6. Descargar solo tweets nuevos ===
max_results = 100
params = {
    "id": user_id,
    "max_results": max_results,
    "tweet_fields": ["id", "text", "referenced_tweets", "created_at", "lang"],
    "expansions": ["referenced_tweets.id", "author_id"]
}
if since_id:
    params["since_id"] = since_id

print(f"Buscando tweets nuevos de @{usuario} desde ID {since_id}...")

response = client.get_users_tweets(**params)
nuevos_tweets = response.data if response.data else []

# === 7. Procesar y guardar solo originales y citas ===
max_id = since_id
for tweet in nuevos_tweets:
    tweet_id = str(tweet.id)
    es_cita = False
    es_original = True
    if hasattr(tweet, "referenced_tweets") and tweet.referenced_tweets:
        for ref in tweet.referenced_tweets:
            if ref.type == "quoted":
                es_cita = True
            else:
                es_original = False
    if (es_original or es_cita) and tweet_id not in ids_existentes:
        url = f"https://x.com/{usuario}/status/{tweet_id}"
        worksheet.append_row([tweet_id, tweet.text, url, "", "pendiente"])
        print(f"Agregado tweet {tweet_id}")
    if max_id is None or int(tweet_id) > int(max_id):
        max_id = tweet_id

# === 8. Guardar el último tweet procesado ===
if max_id:
    with open(ultimo_id_file, "w") as f:
        f.write(str(max_id))

print("Revisión de tweets nuevos finalizada.")
