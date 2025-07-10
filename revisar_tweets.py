import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
import json


st.write("DEBUG: ¿GOOGLE_CREDENTIALS en secrets?", "GOOGLE_CREDENTIALS" in st.secrets)
st.write(st.secrets["GOOGLE_CREDENTIALS"])
if "GOOGLE_CREDENTIALS" in st.secrets:
    try:
        creds = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
        st.write("DEBUG: JSON cargado correctamente")
    except Exception as e:
        st.write(f"DEBUG: Error al cargar JSON: {e}")
else:
    st.write("DEBUG: No se encontró GOOGLE_CREDENTIALS en secrets")

# Configurar credenciales de Google
def get_google_credentials():
    try:
        creds_json = st.secrets["GOOGLE_CREDENTIALS"]
        creds_dict = json.loads(creds_json)
        credentials = Credentials.from_service_account_info(creds_dict)
        return credentials.with_scopes([
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ])
    except Exception as e:
        st.error(f"Error al cargar credenciales: {e}")
        return None

# Conectar a Google Sheets
@st.cache_resource
def connect_to_sheets():
    credentials = get_google_credentials()
    if credentials:
        return gspread.authorize(credentials)
    return None

def main():
    st.title("🐦 Revisor de Tweets")
    st.markdown("---")
    
    gc = connect_to_sheets()
    if not gc:
        st.error("❌ No se pudo conectar a Google Sheets")
        return
    
    try:
        # Abrir la hoja de cálculo (ajusta el nombre si es necesario)
        sheet = gc.open("tweets_candidatos").sheet1
        
        # Obtener datos
        data = sheet.get_all_records()
        st.write("Datos crudos:", data)  # DEBUG

        if not data:
            st.info("📭 No hay tweets pendientes de revisión (la hoja está vacía)")
            return
        
        df = pd.DataFrame(data)
        st.write("DataFrame:", df.head())  # DEBUG

        # Filtrar solo tweets pendientes
        pending_tweets = df[df['estado'] == 'pendiente']

        if pending_tweets.empty:
            st.success("🎉 ¡No hay tweets pendientes!")
            # Mostrar estadísticas finales
            st.markdown("---")
            st.subheader("📊 Estadísticas")
            total_tweets = len(df)
            aprobados = len(df[df['estado'] == 'aprobado'])
            rechazados = len(df[df['estado'] == 'rechazado'])
            col1, col2, col3 = st.columns(3)
            col1.metric("Total", total_tweets)
            col2.metric("Aprobados", aprobados)
            col3.metric("Rechazados", rechazados)
            return
        
        st.write(f"**{len(pending_tweets)} tweets pendientes de revisión**")
        
        # Mostrar tweets uno por uno
        for idx, tweet in pending_tweets.iterrows():
            with st.container():
                st.markdown("---")
                st.write(f"**Tweet #{idx + 1}**")
                st.write(f"**📝 Texto:**")
                st.info(tweet['texto'])
                st.write(f"**🔗 URL:** [Ver tweet]({tweet['url']})")
                st.write(f"**💬 Comentario:** {tweet['comentario']}")
                
                # Botones de acción
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    if st.button(f"✅ Aprobar", key=f"approve_{idx}", type="primary"):
                        all_data = sheet.get_all_values()
                        for row_idx, row in enumerate(all_data[1:], start=2):  # Skip header
                            if row[0] == str(tweet['tweet_id']):  # tweet_id es la primera columna
                                sheet.update(f'E{row_idx}', 'aprobado')  # 'estado' es la columna E
                                st.success("✅ Tweet aprobado!")
                                st.rerun()
                                break
                
                with col2:
                    if st.button(f"❌ Rechazar", key=f"reject_{idx}", type="secondary"):
                        all_data = sheet.get_all_values()
                        for row_idx, row in enumerate(all_data[1:], start=2):
                            if row[0] == str(tweet['tweet_id']):
                                sheet.update(f'E{row_idx}', 'rechazado')
                                st.success("❌ Tweet rechazado!")
                                st.rerun()
                                break
                
                with col3:
                    if st.button(f"⏭️ Saltar", key=f"skip_{idx}"):
                        st.info("⏭️ Tweet saltado")
                
                with col4:
                    if st.button(f"🔄 Recargar", key=f"reload_{idx}"):
                        st.rerun()
        
        # Estadísticas
        st.markdown("---")
        st.subheader("📊 Estadísticas")
        total_tweets = len(df)
        aprobados = len(df[df['estado'] == 'aprobado'])
        rechazados = len(df[df['estado'] == 'rechazado'])
        pendientes = len(df[df['estado'] == 'pendiente'])
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total", total_tweets)
        col2.metric("Aprobados", aprobados)
        col3.metric("Rechazados", rechazados)
        col4.metric("Pendientes", pendientes)
        
        # Progreso
        if total_tweets > 0:
            progress = (aprobados + rechazados) / total_tweets
            st.progress(progress)
            st.write(f"Progreso: {progress:.1%}")
        
    except gspread.SpreadsheetNotFound:
        st.error("❌ No se encontró la hoja 'tweets_candidatos'. Asegúrate de que el script de detección haya creado la hoja.")
    except Exception as e:
        st.error(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
