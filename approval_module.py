import streamlit as st
import pandas as pd
import json
from database_engine import get_connection
from utils import format_rp, render_luxury_table
from datetime import datetime
import os

def show_approval():
    
    st.markdown("## 🛡️ Pusat Persetujuan (Approval Center)")
    st.info("Seluruh tindakan sensitif staf menunggu persetujuan Anda di sini.")
    conn = get_connection()
    pending = pd.read_sql_query("SELECT * FROM pending_approvals WHERE status = 'PENDING' ORDER BY timestamp DESC", conn)
    conn.close()

    if not pending.empty:
        # --- SHOW RECENTLY GENERATED CREDS ---
        if 'last_creds' in st.session_state and st.session_state.last_creds:
            creds = st.session_state.last_creds
            st.success(f"✅ AKUN BERHASIL DIBUAT UNTUK {creds['email']}!")
            st.code(f"Personnel ID: {creds['user']}\nAccess Key: {creds['pass']}", language="text")
            st.info("Silakan copy data di atas dan berikan kepada staf terkait.")
            if st.button("Tutup Notifikasi Akun"):
                st.session_state.last_creds = None
                st.rerun()

        for idx, row in pending.iterrows():
            with st.expander(f"⚠️ {row['action_type']} | {row['user_requester']} | {row['timestamp']}"):
                st.write(f"**Deskripsi:** {row['description']}")
                st.write(f"**Alasan Diajukan:** {row['reason']}")
                # SHOW IMAGE PREVIEW IF ANY
                try:
                    payload = json.loads(row['data_payload'])
                    if 'image' in payload and payload['image'] and os.path.exists(payload['image']):
                        st.image(payload['image'], caption="Bukti Foto")
                except: pass
                st.write("---")
                
                c1, c2 = st.columns(2)
                if c1.button("✅ SETUJUI (ACC)", key=f"acc_{row['id']}", use_container_width=True):
                    process_approval(row['id'], True)
                    st.success("Tindakan Disetujui & Sistem Terupdate!")
                    st.rerun()
                
                if c2.button("❌ TOLAK", key=f"rej_{row['id']}", use_container_width=True):
                    process_approval(row['id'], False)
                    st.warning("Tindakan Ditolak.")
                    st.rerun()
    else:
        st.success("Semua beres! Tidak ada permintaan persetujuan yang tertunda.")

    st.write("---")
    st.markdown("#### 📜 Riwayat Persetujuan")
    conn = get_connection()
    history = pd.read_sql_query("SELECT timestamp, user_requester, action_type, status, reason FROM pending_approvals WHERE status != 'PENDING' ORDER BY timestamp DESC LIMIT 10", conn)
    conn.close()
    if not history.empty:
        st.markdown(render_luxury_table(history), unsafe_allow_html=True)
    
    

def process_approval(approval_id, is_approved):
    conn = get_connection()
    req = conn.execute("SELECT * FROM pending_approvals WHERE id=?", (approval_id,)).fetchone()
    
    if is_approved:
        payload = json.loads(req[5]) # data_payload
        action = req[3] # action_type
        
        if action == "HAPUS_TRANSAKSI":
            conn.execute("DELETE FROM sales_log WHERE id=?", (payload['sales_id'],))
            
        elif action == "CATAT_WASTE_BAHAN":
            conn.execute("INSERT INTO waste_log (timestamp, inventory_id, qty_waste, loss_value, reason) VALUES (?,?,?,?,?)",
                        (req[1], payload['inv_id'], payload['qty'], payload['loss'], req[6]))
            conn.execute("UPDATE inventory_master SET stock = stock - ? WHERE id = ?", (payload['qty'], payload['inv_id']))
            conn.execute("INSERT INTO budget_usage_log (timestamp, room_name, amount, description) VALUES (?,?,?,?)",
                        (req[1], "Waste & Loss Reserve", payload['loss'], f"Waste: {payload['item_name']}"))

        elif action == "CATAT_WASTE_ALAT":
            conn.execute("INSERT INTO asset_waste_log (timestamp, asset_name, loss_value, reason, image_path) VALUES (?,?,?,?,?)",
                        (req[1], payload['asset_name'], payload['loss'], req[6], payload.get('image')))
            conn.execute("INSERT INTO budget_usage_log (timestamp, room_name, amount, description) VALUES (?,?,?,?)",
                        (req[1], "Waste & Loss Reserve", payload['loss'], f"Asset Loss: {payload['asset_name']}"))

        elif action == "RISET_PRODUK":
            conn.execute("INSERT INTO rd_trials (timestamp, name, total_cost) VALUES (?,?,?)", (req[1], payload['name'], payload['cost']))
            tid = conn.lastrowid
            for ing in payload['ingredients']:
                conn.execute("INSERT INTO rd_trial_ingredients (trial_id, inventory_id, qty_pakai) VALUES (?,?,?)", (tid, ing['inv_id'], ing['qty']))
                conn.execute("UPDATE inventory_master SET stock = stock - ? WHERE id = ?", (ing['qty'], ing['inv_id']))
            conn.execute("INSERT INTO budget_usage_log (timestamp, room_name, amount, description) VALUES (?,?,?,?)",
                        (req[1], "R&D (Riset Produk)", payload['cost'], f"Riset: {payload['name']}"))

        elif action == "PENGELUARAN_DANA":
            conn.execute("INSERT INTO budget_usage_log (timestamp, room_name, amount, description) VALUES (?,?,?,?)",
                        (req[1], payload['room'], payload['amount'], payload['desc']))

        elif action == "HAPUS_MATERIAL":
            conn.execute("DELETE FROM inventory_master WHERE id = ?", (payload['id'],))

        elif action == "HAPUS_RESEP":
            conn.execute("DELETE FROM recipe_ingredients WHERE recipe_id = ?", (payload['id'],))
            conn.execute("DELETE FROM recipe_master WHERE id = ?", (payload['id'],))

        elif action == "HAPUS_ADDON":
            conn.execute("DELETE FROM product_addons WHERE id = ?", (payload['id'],))

        elif action == "HAPUS_SUPPLIER":
            conn.execute("DELETE FROM suppliers WHERE id = ?", (payload['id'],))

        elif action == "HAPUS_PO":
            conn.execute("DELETE FROM purchase_order_log WHERE id = ?", (payload['id'],))

        elif action == "STAFF_SIGNUP":
            import random, string
            # Generate Random Password
            new_pass = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
            new_user = payload['name'].lower().replace(" ", "_") + str(random.randint(10,99))
            
            # Insert to Users
            conn.execute("INSERT INTO users (username, password, role, email) VALUES (?,?,?,?)",
                         (new_user, new_pass, payload['role'], payload['email']))
            
            # Simpan credentials ke session state biar bisa ditampilkan ke Owner
            st.session_state.last_creds = {"user": new_user, "pass": new_pass, "email": payload['email']}
            
        elif action == "ONLINE_ORDER":
            # Just move to sales log or mark as accepted
            pass

        # Log to Audit for every approval
        conn.execute("INSERT INTO audit_logs (timestamp, user_actor, action, table_name, reason) VALUES (?,?,?,?,?)",
                    (datetime.now(), "SYSTEM", f"APPROVED_{action}", "various", f"Owner approved action from {req[2]}"))
        
        conn.execute("UPDATE pending_approvals SET status = 'APPROVED' WHERE id = ?", (approval_id,))
    else:
        conn.execute("UPDATE pending_approvals SET status = 'REJECTED' WHERE id = ?", (approval_id,))
    
    conn.commit()
    conn.close()
