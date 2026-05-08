import streamlit as st
import pandas as pd
from database_engine import get_connection
from utils import render_luxury_table

def show_settings():
    
    st.markdown("## ⚙️ Pengaturan Sistem & Izin Akses")
    st.write("Kelola siapa saja yang berhak mengakses sistem Near Bakery Executive.")

    # --- ALL POSSIBLE MENUS ---
    available_menus = ["Dashboard", "Penjualan", "CustomOrder", "Resep", "Inventaris", "Logistik", "Tracking", "Waste", "Persetujuan", "Chat", "Integrasi"]

    # --- ADD NEW USER FORM ---
    with st.expander("➕ Tambah Akses Staf Baru (Gmail)"):
        with st.form("add_user_form"):
            new_name = st.text_input("Nama Lengkap Staf (Sesuai KTP)")
            new_email = st.text_input("Alamat Gmail (untuk Login)")
            new_role = st.selectbox("Role / Jabatan", ["Staff", "Logistik", "Manajer", "Kasir"])
            new_pass = st.text_input("Password Sementara", type="password")
            
            st.write("---")
            st.markdown("**🛡️ Izin Akses Menu (Pilih yang diperbolehkan):**")
            cols = st.columns(3)
            selected_permissions = []
            for idx, menu_item in enumerate(available_menus):
                with cols[idx % 3]:
                    if st.checkbox(menu_item, key=f"perm_{menu_item}"):
                        selected_permissions.append(menu_item)
            
            if st.form_submit_button("BERIKAN AKSES SEKARANG"):
                if new_email and new_name and selected_permissions:
                    import json
                    perm_json = json.dumps(selected_permissions)
                    conn = get_connection()
                    try:
                        conn.execute("INSERT INTO users (username, password, role, email, permissions) VALUES (?,?,?,?,?)",
                                     (new_name, new_pass, new_role, new_email, perm_json))
                        conn.commit()
                        st.success(f"Akses berhasil diberikan untuk {new_name}!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal menambah user: {e}")
                    finally:
                        conn.close()
                else:
                    st.warning("Mohon lengkapi Nama, Gmail, dan minimal 1 Izin Akses.")

    st.write("---")
    st.markdown("### 👥 Daftar Staf Aktif & Otoritas Akses")
    
    conn = get_connection()
    users_df = pd.read_sql_query('SELECT username as "Nama Lengkap", email as "Gmail", role as "Jabatan", permissions as "Akses Menu" FROM users WHERE role != \'OWNER\'', conn)
    conn.close()

    if not users_df.empty:
        st.markdown(render_luxury_table(users_df), unsafe_allow_html=True)
        
        # --- REMOVE USER ---
        st.write("")
        user_to_del = st.selectbox("Pilih Staf untuk Dicabut Aksesnya", ["-- Pilih Staf --"] + users_df['Gmail'].tolist())
        if user_to_del != "-- Pilih Staf --":
            if st.button("🔥 CABUT AKSES (HAPUS)", use_container_width=True):
                conn = get_connection()
                conn.execute("DELETE FROM users WHERE email = ?", (user_to_del,))
                conn.commit(); conn.close()
                st.success(f"Akses untuk {user_to_del} telah dihapus!")
                st.rerun()
    else:
        st.info("Belum ada staf yang terdaftar.")

    
