import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.parse
from database_engine import get_connection
from utils import format_rp, UNITS_MASTER, render_luxury_table
from pdf_utils import create_po_pdf
import json

def show_purchase():
    
    st.markdown("## 🛒 Manajemen Logistik & Pengadaan (Purchase Order)")
    
    tab_po, tab_supplier = st.tabs(["📋 Pesanan Pembelian (PO)", "🏢 Manajemen Supplier"])

    # --- TAB 2: MANAJEMEN SUPPLIER ---
    with tab_supplier:
        with st.expander("➕ Tambah Supplier Baru"):
            with st.form("supplier_form"):
                s_name = st.text_input("Nama Supplier")
                s_contact = st.text_input("Nama Kontak (PIC)")
                s_phone = st.text_input("Nomor WhatsApp (Contoh: 628...)")
                if st.form_submit_button("SIMPAN SUPPLIER"):
                    if s_name and s_phone:
                        conn = get_connection()
                        conn.execute("INSERT INTO suppliers (name, contact_person, phone) VALUES (?,?,?)", (s_name, s_contact, s_phone))
                        conn.commit(); conn.close(); st.success(f"Supplier {s_name} ditambahkan."); st.rerun()
                    else: st.error("Nama dan Nomor WA wajib diisi.")

        conn = get_connection()
        supp_df = pd.read_sql_query("SELECT id, name as \"Supplier\", contact_person as \"PIC\", phone as \"WhatsApp\" FROM suppliers", conn)
        conn.close()
        if not supp_df.empty:
            st.markdown("### 🏢 Daftar Supplier Aktif")
            st.markdown(render_luxury_table(supp_df), unsafe_allow_html=True)
            with st.expander("🗑️ Ajukan Penghapusan Supplier"):
                del_s = st.selectbox("Pilih Supplier", supp_df['Supplier'].tolist())
                reason = st.text_input("Alasan Hapus Supplier")
                if st.button("🚨 AJUKAN HAPUS SUPPLIER"):
                    if reason:
                        sid = int(supp_df[supp_df['Supplier'] == del_s].iloc[0]['id'])
                        payload = {"id": sid, "name": del_s}
                        c = get_connection()
                        c.execute("INSERT INTO pending_approvals (timestamp, user_requester, action_type, description, data_payload, reason) VALUES (?,?,?,?,?,?)",
                                 (pd.Timestamp.now(), st.session_state.user, "HAPUS_SUPPLIER", f"Menghapus Supplier: {del_s}", json.dumps(payload), reason))
                        c.commit(); c.close(); st.info("Pengajuan hapus supplier dikirim ke Owner."); st.rerun()
        else: st.info("Belum ada data supplier.")

    # --- TAB 1: PO ---
    with tab_po:
        conn = get_connection()
        inv_items = pd.read_sql_query("SELECT id, name, unit_beli FROM inventory_master", conn)
        suppliers = pd.read_sql_query("SELECT id, name, phone FROM suppliers", conn)
        conn.close()
        
        with st.expander("📝 Buat Pesanan Pembelian Baru (PO)"):
            if inv_items.empty or suppliers.empty: st.warning("Isi data Gudang dan Supplier dulu.")
            else:
                with st.form("po_form"):
                    c1, c2 = st.columns(2)
                    item_name = c1.selectbox("Pilih Material", inv_items['name'].tolist())
                    supp_id = c2.selectbox("Pilih Supplier", suppliers['id'].tolist(), format_func=lambda x: suppliers[suppliers['id']==x]['name'].values[0])
                    c3, c4 = st.columns(2); qty = c3.number_input("Jumlah Pesanan", min_value=1.0); unit_po = c4.selectbox("Satuan", UNITS_MASTER)
                    price_est = st.number_input("Estimasi Harga Total (Rp)", min_value=0.0); note = st.text_area("Catatan Tambahan")
                    if st.form_submit_button("KONFIRMASI & SIMPAN PO"):
                        item_id = inv_items[inv_items['name'] == item_name].iloc[0]['id']
                        row_s = suppliers[suppliers['id'] == supp_id]
                        c = get_connection(); c.execute("INSERT INTO purchase_order_log (timestamp, inventory_id, supplier_id, qty_order, unit_order, price_total, status) VALUES (?,?,?,?,?,?,?)",
                                 (datetime.now(), int(item_id), int(supp_id), qty, unit_po, price_est, 'Dikirim')); c.commit(); c.close()
                        
                        msg = f"*PO NEAR BAKERY*\n\nMaterial: {item_name}\nQty: {qty} {unit_po}\nEstimasi: {format_rp(price_est)}\nCatatan: {note}"
                        wa_link = f"https://wa.me/{row_s['phone'].values[0]}?text={urllib.parse.quote(msg)}"
                        st.session_state.last_wa_link = wa_link
                        st.toast("✅ PO Berhasil Dicatat!")
                        st.rerun()

                if 'last_wa_link' in st.session_state:
                    st.markdown(f'<a href="{st.session_state.last_wa_link}" target="_blank"><button style="background-color:#25D366; color:white; border:none; padding:15px; border-radius:10px; width:100%; font-weight:bold; margin-bottom:20px;">📲 KIRIM PO TERAKHIR KE WHATSAPP</button></a>', unsafe_allow_html=True)
                    if st.button("❌ TUTUP LINK WHATSAPP"): del st.session_state.last_wa_link; st.rerun()

        conn = get_connection()
        po_df = pd.read_sql_query("SELECT p.id, p.timestamp, i.name as Material, s.name as Supplier, p.qty_order as Qty, p.unit_order as Unit, p.price_total as Total, p.status, p.inventory_id FROM purchase_order_log p JOIN inventory_master i ON p.inventory_id = i.id JOIN suppliers s ON p.supplier_id = s.id ORDER BY p.timestamp DESC", conn)
        conn.close()
        
        if not po_df.empty:
            st.markdown("### 📋 Riwayat Semua Pesanan (PO)")
            disp = po_df.copy(); disp['Total'] = disp['Total'].apply(format_rp)
            st.markdown(render_luxury_table(disp.drop(columns=['inventory_id'])), unsafe_allow_html=True)
            for _, row in po_df.iterrows():
                with st.expander(f"⚙️ Kelola PO #{row['id']} - {row['Material']}"):
                    if row['status'] == 'Dikirim':
                        if st.button("TANDAI DITERIMA", key=f"rec_{row['id']}", use_container_width=True):
                            c = get_connection(); res = c.execute("SELECT unit_conversion_rate, stock, price_per_unit_pakai FROM inventory_master WHERE id=?", (row['inventory_id'],)).fetchone()
                            if res:
                                rate, old_s, old_p = res; new_p_qty = row['Qty'] * rate; tot_s = old_s + new_p_qty
                                new_p = ((old_s * old_p) + row['Total']) / tot_s if tot_s > 0 else 0
                                c.execute("UPDATE inventory_master SET stock = ?, price_per_unit_pakai = ? WHERE id = ?", (tot_s, new_p, row['inventory_id']))
                                c.execute("UPDATE purchase_order_log SET status = 'Diterima' WHERE id = ?", (row['id'],))
                                c.commit(); c.close(); st.success("Stok Terupdate!"); st.rerun()
                    
                    reason_po = st.text_input("Alasan Hapus PO", key=f"rs_po_{row['id']}")
                    if st.button("AJUKAN HAPUS PO", key=f"del_po_{row['id']}", use_container_width=True):
                        if reason_po:
                            payload = {"id": row['id']}; c = get_connection()
                            c.execute("INSERT INTO pending_approvals (timestamp, user_requester, action_type, description, data_payload, reason) VALUES (?,?,?,?,?,?)",
                                     (pd.Timestamp.now(), st.session_state.user, "HAPUS_PO", f"Menghapus PO #{row['id']}", json.dumps(payload), reason_po))
                            c.commit(); c.close(); st.info("Pengajuan hapus PO terkirim."); st.rerun()
        else: st.info("Belum ada riwayat pesanan.")
    
