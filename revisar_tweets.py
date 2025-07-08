import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# === Google Sheets ===
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
gc = gspread.authorize(creds)
SHEET_NAME = 'tweets_candidatos'
sh = gc.open(SHEET_NAME)
worksheet = sh.sheet1

st.title("Revisión de Tweets Candidatos")

# Leer datos
rows = worksheet.get_all_records()
if not rows:
    st.warning("No hay tweets candidatos para revisar.")
    st.stop()

for idx, row in enumerate(rows):
    if row['estado'] != "pendiente":
        continue
    st.markdown(f"**Tweet:** {row['texto']}")
    st.markdown(f"[Ver en X]({row['url']})")
    comentario = st.text_input(f"Comentario para RT (opcional) - Tweet {row['tweet_id']}", value=row['comentario'], key=row['tweet_id'])
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Aprobar y Publicar", key=f"aprobar_{row['tweet_id']}"):
            worksheet.update_cell(idx+2, 4, comentario)  # columna 'comentario'
            worksheet.update_cell(idx+2, 5, "aprobado")  # columna 'estado'
            st.success("Aprobado para publicar")
            st.experimental_rerun()
    with col2:
        if st.button("Rechazar", key=f"rechazar_{row['tweet_id']}"):
            worksheet.update_cell(idx+2, 5, "rechazado")
            st.warning("Tweet rechazado")
            st.experimental_rerun()
    with col3:
        if st.button("Editar comentario", key=f"editar_{row['tweet_id']}"):
            worksheet.update_cell(idx+2, 4, comentario)
            st.info("Comentario editado")

st.write("Fin de la lista.")