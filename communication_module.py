import streamlit as st
import pandas as pd
from database_engine import get_connection
from datetime import datetime

def show_communication():
    
    st.markdown("## 💬 Papan Komunikasi Internal")
    st.info("Gunakan ruang ini untuk koordinasi, masukan, dan instruksi tim.")

    # --- SEND MESSAGE FORM ---
    with st.form("msg_form", clear_on_submit=True):
        st.markdown(f"**Kirim Pesan Baru sebagai: `{st.session_state.user}`**")
        msg_text = st.text_area("Pesan / Masukan", placeholder="Ketik laporan atau saran Anda di sini...", height=100)
        if st.form_submit_button("🚀 KIRIM KE SEMUA"):
            if msg_text:
                conn = get_connection()
                conn.execute("INSERT INTO internal_messages (timestamp, sender, message) VALUES (?,?,?)",
                             (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), st.session_state.user, msg_text))
                conn.commit(); conn.close()
                st.success("Pesan terkirim!")
                st.rerun()

    st.write("---")
    st.markdown("### 📜 Riwayat Obrolan & Instruksi")
    
    # --- FETCH MESSAGES ---
    conn = get_connection()
    messages = pd.read_sql_query("SELECT timestamp, sender, message FROM internal_messages ORDER BY timestamp DESC LIMIT 50", conn)
    conn.close()

    if not messages.empty:
        for idx, row in messages.iterrows():
            is_me = row['sender'] == st.session_state.user
            color = "#DBEAFE" if row['sender'] == 'admin' else "#F1F5F9"
            align = "right" if is_me else "left"
            
            st.markdown(f"""
            <div style="background: {color}; padding: 15px; border-radius: 15px; margin-bottom: 10px; border-left: 5px solid #1E3A8A;">
                <div style="font-size: 0.7rem; color: #64748B;">{row['timestamp']} • <b>{row['sender']}</b></div>
                <div style="font-size: 0.9rem; margin-top: 5px; color: #1E293B;">{row['message']}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.write("Belum ada percakapan.")

    
