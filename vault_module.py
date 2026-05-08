import streamlit as st
import pandas as pd
from database_engine import get_connection
from utils import format_rp, render_luxury_table
from datetime import datetime

def show_vault():
    
    st.markdown("## 🏛️ Khazanah Bisnis (The Vault)")
    st.info("Semua hasil penjualan mengalir ke sini sebelum ditarik ke Rekening Bank Pribadi Anda.")
    
    conn = get_connection()
    vault_data = conn.execute("SELECT current_balance, last_update FROM business_vault").fetchone()
    ledger = pd.read_sql_query("SELECT timestamp, amount, type, source, description FROM vault_ledger ORDER BY timestamp DESC LIMIT 20", conn)
    conn.close()
    
    balance = vault_data[0] if vault_data else 0.0
    
    # --- VAULT IDENTITY ---
    vault_id = "NB-VLT-2026-888"
    
    # --- HEADER DISPLAY ---
    c1, c2, c3 = st.columns([1.5, 1, 1])
    with c1:
        st.markdown(f"""
        <div style='background: #1E1B18; padding: 30px; border-radius: 20px; border: 2px solid #D4AF37;'>
            <div style='color: #8E8A85; font-size: 0.8rem; letter-spacing: 2px;'>TOTAL SALDO KHAZANAH</div>
            <div style='color: #D4AF37; font-size: 2.5rem; font-weight: 900; font-family: "Playfair Display", serif;'>{format_rp(balance)}</div>
            <div style='color: #8E8A85; font-size: 0.7rem; margin-top: 10px;'>ID REKENING: <b style='color:#D4AF37'>{vault_id}</b></div>
            <div style='color: #8E8A85; font-size: 0.7rem;'>Update: {vault_data[1] if vault_data else 'N/A'}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with c2:
        st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
        
        # --- SHOW REAL QRIS IF EXISTS ---
        import os
        qris_path = "qris_near_bakery.png"
        if os.path.exists(qris_path):
            st.image(qris_path, caption="QRIS RESMI TOKO", use_container_width=True)
        else:
            # Professional QR Code Placeholder using SVG
            qr_svg = f"""
            <svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
                <rect width="100" height="100" fill="white" />
                <path d="M10 10h30v30h-30z M60 10h30v30h-30z M10 60h30v30h-30z M60 60h30v30h-30z" fill="#1E1B18" />
                <path d="M20 20h10v10h-10z M70 20h10v10h-10z M20 70h10v10h-10z M70 70h10v10h-10z" fill="#D4AF37" />
                <rect x="45" y="45" width="10" height="10" fill="#D4AF37" />
            </svg>
            """
            st.markdown(f"<div style='width: 120px; margin: 0 auto;'>{qr_svg}</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='font-size: 0.6rem; color: #8E8A85; margin-top: 5px;'>QRIS BELUM DIUPLOAD</div>", unsafe_allow_html=True)
        
        # --- UPLOADER FOR OWNER ---
        with st.expander("📸 Update QRIS Asli"):
            uploaded_qris = st.file_uploader("Upload Foto QRIS Toko (PNG/JPG)", type=['png', 'jpg', 'jpeg'])
            if uploaded_qris:
                with open(qris_path, "wb") as f:
                    f.write(uploaded_qris.getbuffer())
                st.success("QRIS Berhasil Diperbarui!"); st.rerun()
        
        

    with c3:
        st.markdown("### 🏦 Transaksi Dana")
        
        mode = st.radio("Pilih Aksi", ["Tarik Dana (Payout)", "Top-up (Suntik Modal)"], horizontal=True)
        
        if mode == "Tarik Dana (Payout)":
            with st.form("payout_form"):
                target_bank = st.selectbox("Tujuan Transfer", ["Bank BCA", "Bank Mandiri", "E-Wallet (Dana/Ovo)"])
                amount_withdraw = st.number_input("Jumlah Penarikan (Rp)", min_value=0.0, max_value=balance)
                notes = st.text_input("Keterangan (Misal: Gaji Owner)")
                if st.form_submit_button("TRANSFER KE BANK SEKARANG"):
                    if amount_withdraw > 0:
                        c = get_connection()
                        c.execute("UPDATE business_vault SET current_balance = current_balance - ?, last_update = ?", (amount_withdraw, datetime.now()))
                        c.execute("INSERT INTO vault_ledger (timestamp, amount, type, source, description) VALUES (?,?,?,?,?)",
                                 (datetime.now(), -amount_withdraw, "WITHDRAWAL", "PAYOUT", f"Transfer ke {target_bank}: {notes}"))
                        c.commit(); c.close(); st.success(f"Berhasil! Dana {format_rp(amount_withdraw)} dipindahkan."); st.rerun()
        
        else:
            with st.form("topup_vault_form"):
                amount_topup = st.number_input("Jumlah Injeksi Modal (Rp)", min_value=0.0)
                notes_topup = st.text_input("Keterangan (Misal: Modal Awal)")
                if st.form_submit_button("KONFIRMASI TOP-UP KHAZANAH"):
                    if amount_topup > 0:
                        c = get_connection()
                        c.execute("UPDATE business_vault SET current_balance = current_balance + ?, last_update = ?", (amount_topup, datetime.now()))
                        c.execute("INSERT INTO vault_ledger (timestamp, amount, type, source, description) VALUES (?,?,?,?,?)",
                                 (datetime.now(), amount_topup, "INFLOW", "OWNER_INJECTION", f"Suntik Modal: {notes_topup}"))
                        c.commit(); c.close(); st.success(f"Berhasil! Saldo Khazanah bertambah {format_rp(amount_topup)}."); st.rerun()

    st.write("---")
    st.markdown("### 📜 Buku Besar Khazanah (Ledger)")
    if not ledger.empty:
        # Style the ledger
        ledger['amount'] = ledger.apply(lambda x: f"<span style='color:#28a745'>+{format_rp(x['amount'])}</span>" if x['amount'] > 0 else f"<span style='color:#dc3545'>{format_rp(x['amount'])}</span>", axis=1)
        st.markdown(render_luxury_table(ledger), unsafe_allow_html=True)
    else:
        st.info("Belum ada mutasi keuangan di Khazanah.")

    
