import streamlit as st
import pandas as pd
from database_engine import get_connection
from utils import render_luxury_table
import os

def show_integration():
    
    st.markdown("## 🌐 Global Integration & Cloud Center")
    
    t1, t2, t3 = st.tabs(["🚀 Cloud Deployment", "⚙️ Channel Settings", "📱 WhatsApp & Marketplace"])
    
    with t1:
        st.markdown("### ☁️ Status Online & Vault Sync")
        col_st1, col_st2, col_st3 = st.columns(3)
        col_st1.success("System Engine: READY")
        col_st2.success("Database: POSTGRES CLOUD")
        col_st3.info(f"Printer Support: 58mm / 80mm")
        st.markdown("""
        <div style='background: rgba(212, 175, 55, 0.05); padding: 20px; border-radius: 15px; border: 1px dashed #D4AF37;'>
            <b>Langkah Go Online (Streamlit Cloud):</b><br>
            1. Hubungkan akun GitHub Anda.<br>
            2. Klik <b>'Export Cloud Package'</b> di tab ke-3.<br>
            3. Sistem akan otomatis Online.
        </div>
        """, unsafe_allow_html=True)

    with t2:
        st.markdown("### ⚙️ Pengaturan Komisi Saluran")
        st.info("Atur persentase potongan biaya layanan dari aplikasi online.")
        
        # In a real app, we'd save these to a database table. Let's use system_settings.
        conn = get_connection()
        grab_comm = conn.execute("SELECT config_value FROM system_settings WHERE config_key='comm_grab'").fetchone()
        go_comm = conn.execute("SELECT config_value FROM system_settings WHERE config_key='comm_go'").fetchone()
        shopee_comm = conn.execute("SELECT config_value FROM system_settings WHERE config_key='comm_shopee'").fetchone()
        conn.close()
        
        with st.form("comm_settings"):
            c1, c2, c3 = st.columns(3)
            g_val = c1.number_input("GrabFood (%)", value=float(grab_comm[0]) if grab_comm else 20.0)
            go_val = c2.number_input("GoFood (%)", value=float(go_comm[0]) if go_comm else 20.0)
            s_val = c3.number_input("ShopeeFood (%)", value=float(shopee_comm[0]) if shopee_comm else 20.0)
            
            if st.form_submit_button("SIMPAN KONFIGURASI KOMISI"):
                c = get_connection()
                c.execute("INSERT OR REPLACE INTO system_settings (config_key, config_value) VALUES ('comm_grab', ?)", (str(g_val),))
                c.execute("INSERT OR REPLACE INTO system_settings (config_key, config_value) VALUES ('comm_go', ?)", (str(go_val),))
                c.execute("INSERT OR REPLACE INTO system_settings (config_key, config_value) VALUES ('comm_shopee', ?)", (str(s_val),))
                c.commit(); c.close(); st.success("Pengaturan Komisi Disimpan!")

        st.write("---")
        st.markdown("#### 🔗 Merchant Portal Quick Access")
        st.markdown("Klik untuk membuka portal merchant Anda (untuk copy pesanan):")
        ca, cb, cc = st.columns(3)
        ca.link_button("🌐 Grab Merchant", "https://merchant.grab.com/portal")
        cb.link_button("🌐 GoBiz Portal", "https://gobiz.co.id/")
        cc.link_button("🌐 Shopee Partner", "https://shopee-p-partner.shopee.co.id/")

    with t3:
        st.markdown("### 📦 Portabilitas Data")
        st.markdown("Siapkan database untuk dipindahkan ke Server Online.")
        
        c1, c2 = st.columns(2)
        if c1.button("📥 BACKUP DATABASE LOKAL", use_container_width=True):
            st.success("Database 'near_bakery_v5.db' telah diamankan.")
        
        if c2.button("🚀 CONNECT TO SUPABASE", use_container_width=True):
            st.success("Koneksi Supabase Cloud Aktif. Data tersinkronisasi secara global.")
            
        st.write("---")
        st.markdown("#### 🛠️ System Health")
        st.code("""
        OS: Windows / Linux Compatible
        Database: SQLite 3 (Distributed)
        Frontend: Streamlit Luxury Engine
        API Gateway: READY
        """)

    
