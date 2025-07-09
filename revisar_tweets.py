import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
import json

# Configurar credenciales de Google
def get_google_credentials():
    try:
        # Leer desde secrets de Streamlit
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
        # Abrir la hoja de cálculo
        sheet = gc.open("tweets_candidatos").sheet1
        
        # Obtener datos
        data = sheet.get_all_records()
        
        if not data:
            st.info("📭 No hay tweets pendientes de revisión")
            return
        
        df = pd.DataFrame(data)
        
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
                
                col_info1, col_info2 = st.columns(2)
                with col_info1:
                    st.write(f"**👤 Autor:** @{tweet['usuario']}")
                with col_info2:
                    st.write(f"**📅 Fecha:** {tweet['fecha']}")
                
                st.write(f"**📝 Contenido:**")
                st.info(tweet['contenido'])
                
                st.write(f"**🔗 URL:** [Ver tweet]({tweet['url']})")
                
                # Botones de acción
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    if st.button(f"✅ Aprobar", key=f"approve_{idx}", type="primary"):
                        # Encontrar la fila correcta en Google Sheets
                        all_data = sheet.get_all_values()
                        for row_idx, row in enumerate(all_data[1:], start=2):  # Skip header
                            if row[4] == str(tweet['id_tweet']):  # Comparar por ID del tweet
                                sheet.update(f'F{row_idx}', 'aprobado')
                                st.success("✅ Tweet aprobado!")
                                st.rerun()
                                break
                
                with col2:
                    if st.button(f"❌ Rechazar", key=f"reject_{idx}", type="secondary"):
                        all_data = sheet.get_all_values()
                        for row_idx, row in enumerate(all_data[1:], start=2):
                            if row[4] == str(tweet['id_tweet']):
                                sheet.update(f'F{row_idx}', 'rechazado')
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
