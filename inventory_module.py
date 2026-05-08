# inventory_module.py
from datetime import datetime
import streamlit as st
import pandas as pd
from database_engine import get_connection
from utils import format_rp, UNITS_MASTER, CATEGORIES_MASTER, render_luxury_table

def show_inventory():
    st.markdown("## 📦 Manajemen Inventaris & Gudang")
    
    tab_master, tab_movement, tab_register, tab_packaging = st.tabs([
        "📊 Gudang Utama (Master Stock)", 
        "🔄 Penyesuaian Stok (In/Out)", 
        "➕ Registrasi Material Baru",
        "📦 Pemetaan Kemasan Otomatis"
    ])

    # --- TAB 1: GUDANG UTAMA ---
    with tab_master:
        st.markdown("### Status Stok Real-Time")
        conn = get_connection()
        inv_df = pd.read_sql_query("""
            SELECT barcode as "ID Barang", name as "Nama Bahan", category as "Kategori", 
                   stock as "Stok Tersedia", unit_pakai as "Satuan",
                   price_per_unit_pakai as "Harga Satuan",
                   (stock * price_per_unit_pakai) as "Total Nilai Aset",
                   last_updated as "Terakhir Update"
            FROM inventory_master
            ORDER BY category, name
        """, conn)
        conn.close()
        
        if not inv_df.empty:
            # Check for Duplicates
            dupes = inv_df[inv_df.duplicated('Nama Bahan')]['Nama Bahan'].unique()
            if len(dupes) > 0:
                st.warning(f"⚠️ **PERHATIAN: Ada data ganda!** ({', '.join(dupes)}). Mohon hapus salah satu agar stok tidak membingungkan.")

            total_inv_value = inv_df['Total Nilai Aset'].sum()
            display_df = inv_df.copy()
            display_df['Harga Satuan'] = display_df['Harga Satuan'].apply(format_rp)
            display_df['Total Nilai Aset'] = display_df['Total Nilai Aset'].apply(format_rp)
            
            st.markdown(render_luxury_table(display_df), unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            c1.metric("Total Nilai Aset Gudang", format_rp(total_inv_value))
            c2.metric("Jumlah Item Terdaftar", len(inv_df))
            
            with st.expander("🗑️ Ajukan Penghapusan Material"):
                del_item = st.selectbox("Pilih Material", inv_df['Nama Bahan'].tolist())
                reason_del = st.text_input("Alasan Penghapusan (Wajib untuk Owner)")
                if st.button("🚨 AJUKAN PENGHAPUSAN KE OWNER"):
                    if reason_del:
                        import json
                        # Get ID
                        conn = get_connection()
                        item_id = conn.execute("SELECT id FROM inventory_master WHERE name = ?", (del_item,)).fetchone()[0]
                        payload = {"id": item_id, "name": del_item}
                        conn.execute("""
                            INSERT INTO pending_approvals (timestamp, user_requester, action_type, description, data_payload, reason)
                            VALUES (?,?,?,?,?,?)
                        """, (pd.Timestamp.now(), st.session_state.user, "HAPUS_MATERIAL", 
                             f"Menghapus Material: {del_item}", json.dumps(payload), reason_del))
                        conn.commit(); conn.close()
                        st.info("Permintaan penghapusan material terkirim ke Owner."); st.rerun()
                    else:
                        st.warning("Isi alasan dulu.")
        else:
            st.info("Gudang kosong.")

    # --- TAB 2: PERGERAKAN STOK ---
    with tab_movement:
        st.markdown("### 🔄 Penyesuaian Stok (Manual In/Out)")
        st.markdown("""
        <div style='background: rgba(212, 175, 55, 0.05); padding: 20px; border-radius: 10px; border-left: 5px solid #D4AF37; margin-bottom: 25px;'>
            <b>Kapan menggunakan fitur ini?</b><br>
            • <b>Stok Masuk (+):</b> Jika Anda menemukan sisa stok, mendapat bonus barang, atau koreksi data.<br>
            • <b>Stok Keluar (-):</b> Jika ada barang rusak, Stock Opname bulanan, atau pemakaian untuk tester/sampel.
        </div>
        """, unsafe_allow_html=True)
        
        conn = get_connection()
        items_df = pd.read_sql_query("SELECT id, name, unit_pakai, stock FROM inventory_master", conn)
        conn.close()
        
        if not items_df.empty:
            with st.form("manual_adj_form"):
                # ... (existing form code) ...
                c1, c2, c3 = st.columns([2, 1, 1])
                item_adj = c1.selectbox("Pilih Material", items_df['name'].tolist())
                adj_type = c2.selectbox("Arah Gerak", ["STOK MASUK (+)", "STOK KELUAR (-)"])
                qty_adj = c3.number_input("Jumlah", min_value=0.0)
                
                # --- LIVE PREVIEW LOGIC ---
                selected_row = items_df[items_df['name'] == item_adj].iloc[0]
                current_stock = selected_row['stock']
                unit_label = selected_row['unit_pakai']
                projected_stock = current_stock + (qty_adj if "MASUK" in adj_type else -qty_adj)
                
                st.markdown(f"""
                <div style='background: #FFFFFF; padding: 15px; border-radius: 10px; border: 1px solid #D4AF37; margin: 10px 0;'>
                    <table style='width: 100%;'>
                        <tr>
                            <td style='color: #8E8A85;'>Stok Saat Ini:</td>
                            <td style='text-align: right; font-weight: bold;'>{current_stock} {unit_label}</td>
                        </tr>
                        <tr>
                            <td style='color: #8E8A85;'>Penyesuaian:</td>
                            <td style='text-align: right; font-weight: bold; color: {"#28a745" if "MASUK" in adj_type else "#dc3545"};'>
                                {"+" if "MASUK" in adj_type else "-"}{qty_adj} {unit_label}
                            </td>
                        </tr>
                        <tr style='border-top: 1px solid #eee;'>
                            <td style='font-weight: 900; color: #1E1B18;'>ESTIMASI STOK AKHIR:</td>
                            <td style='text-align: right; font-weight: 900; color: #D4AF37; font-size: 1.2rem;'>{projected_stock} {unit_label}</td>
                        </tr>
                    </table>
                </div>
                """, unsafe_allow_html=True)
                
                c_a, c_b = st.columns(2)
                move_reason_list = ["Stock Opname", "Pemakaian Internal", "Bonus Supplier", "Koreksi Data", "Rusak/Kadaluarsa", "Lainnya"]
                m_type = c_a.selectbox("Alasan Penyesuaian", move_reason_list)
                m_detail = c_b.text_input("Keterangan Tambahan")
                
                if st.form_submit_button("KONFIRMASI & UPDATE STOK GUDANG"):
                    item_id = int(selected_row['id'])
                    final_qty = qty_adj if "MASUK" in adj_type else -qty_adj
                    
                    conn = get_connection()
                    conn.execute("UPDATE inventory_master SET stock = stock + ?, last_updated = CURRENT_TIMESTAMP WHERE id = ?", (final_qty, item_id))
                    conn.execute("INSERT INTO stock_movement_log (timestamp, inventory_id, qty, type, reason) VALUES (?,?,?,?,?)",
                                (datetime.now(), item_id, final_qty, m_type, m_detail))
                    conn.commit(); conn.close()
                    st.success(f"STOK BERHASIL DIUPDATE! Stok baru {item_adj}: {projected_stock} {unit_label}"); st.rerun()
        else:
            st.warning("⚠️ Gudang Utama Anda masih kosong. Anda tidak bisa menyesuaikan stok jika belum ada barang yang terdaftar.")
            st.info("💡 Silakan ke tab **'Registrasi Material Baru'** untuk mendaftarkan bahan baku Anda pertama kali.")
        
        st.write("---")
        conn = get_connection()
        logs_df = pd.read_sql_query("""
            SELECT l.timestamp as "Waktu", i.name as "Material", l.qty as "Jumlah", 
                   i.unit_pakai as "Satuan", l.type as "Jenis", l.reason as "Keterangan"
            FROM stock_movement_log l JOIN inventory_master i ON l.inventory_id = i.id
            ORDER BY l.timestamp DESC LIMIT 10
        """, conn)
        conn.close()
        if not logs_df.empty: 
            st.markdown(render_luxury_table(logs_df), unsafe_allow_html=True)
        else:
            st.info("Belum ada riwayat penyesuaian stok.")

    # --- TAB 3: REGISTRASI ---
    with tab_register:
        conn = get_connection()
        existing_cats = pd.read_sql_query("SELECT DISTINCT category FROM inventory_master", conn)['category'].tolist()
        conn.close()
        full_cat_list = sorted(list(set(["Bahan Baku", "Kemasan & Box"] + existing_cats)))
        
        # --- LIVE INPUTS (OUTSIDE FORM FOR REAL-TIME CALC) ---
        c1, c2, c3 = st.columns(3)
        name_in = c1.text_input("Nama Bahan")
        c2.info("ID: Auto-Generated")
        cat_choice = c3.selectbox("Kategori", full_cat_list + ["+ Tambah Kategori Baru"])
        new_cat = st.text_input("Kategori Baru") if cat_choice == "+ Tambah Kategori Baru" else ""
        cat_in = new_cat if new_cat else cat_choice
        
        c1b, c2b, c3b = st.columns(3)
        u_beli_in = c1b.selectbox("Satuan", UNITS_MASTER)
        
        # --- SIMPLE VS ADVANCED MODE ---
        use_conv = st.checkbox("Gunakan Konversi (Grosir ke Ecer)?", value=False)
        
        if use_conv:
            u_pakai_in = c2b.selectbox("Satuan Pakai (Ecer)", UNITS_MASTER)
            isi = c3b.number_input("Isi (Jumlah Ecer dalam 1 Grosir)", min_value=0.001, value=1.0)
        else:
            u_pakai_in = u_beli_in
            isi = 1.0
        
        c1c, c2c = st.columns(2)
        total_bayar = c1c.number_input("Total Harga di Nota (Rp)", min_value=0.0, step=500.0)
        jumlah_masuk = c2c.number_input(f"Total Jumlah {u_beli_in} yang Diterima", min_value=0.001, value=1.0)
        
        # --- SMART PREVIEW (LIVE CALCULATION) ---
        total_unit_ecer = jumlah_masuk * isi
        price_per_use = total_bayar / total_unit_ecer if total_unit_ecer > 0 else 0
        
        st.markdown(f"""
        <div style='background: #F8FAFC; padding: 15px; border-radius: 8px; border: 1px solid #E2E8F0; margin: 15px 0;'>
            <p style='margin: 0; color: #64748B; font-size: 0.75rem; font-weight: 700;'>📊 HASIL HITUNG OTOMATIS (HPP):</p>
            <h3 style='margin: 5px 0; color: #0F172A;'>{format_rp(price_per_use)} <span style='font-size: 0.9rem; font-weight: 400;'>per {u_pakai_in}</span></h3>
            <p style='margin: 0; color: #94A3B8; font-size: 0.7rem;'>Sistem akan mencatat modal <b>{u_pakai_in}</b> Bapak sebesar angka di atas.</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("KONFIRMASI PENDAFTARAN MATERIAL", use_container_width=True, type="primary"):
                import random, string
                fid = "NB-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
                fvol = isi * jumlah_masuk
                fppp = price_per_use
                conn = get_connection()
                try:
                    conn.execute("INSERT INTO inventory_master (name, barcode, category, unit_pakai, unit_beli, unit_conversion_rate, price_per_unit_pakai, stock) VALUES (?,?,?,?,?,?,?,?)",
                                (name_in, fid, cat_in, u_pakai_in, u_beli_in, isi, fppp, fvol))
                    
                    # AUDIT LOG
                    conn.execute("""
                        INSERT INTO audit_logs (timestamp, user_actor, action, table_name, old_value, new_value, reason)
                        VALUES (?,?,?,?,?,?,?)
                    """, (pd.Timestamp.now(), st.session_state.user, "CREATE", "inventory_master", "NEW", f"Item: {name_in}, Price: {fppp}", "Registrasi Material Baru"))
                    
                    conn.commit()
                    st.toast(f"✅ Tersimpan: {name_in}", icon='📦')
                    st.rerun()
                except Exception as e: st.error(f"Gagal! {e}")
                finally: conn.close()

    # --- TAB 4: PACKAGING MAPPING ---
    with tab_packaging:
        st.subheader("Pemetaan Kemasan Otomatis")
        st.info("Hubungkan Kategori Produk dengan Set Kemasan (Bundle).")
        
        conn = get_connection()
        pkgs = pd.read_sql_query("SELECT id, name FROM inventory_master WHERE category LIKE '%Kemasan%' OR category LIKE '%Box%'", conn)
        bundles = pd.read_sql_query("SELECT * FROM packaging_bundles", conn)
        mapping = pd.read_sql_query("""
            SELECT m.category_name, b.name as bundle_name 
            FROM category_packaging_map m JOIN packaging_bundles b ON m.bundle_id = b.id
        """, conn)
        conn.close()

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**1. Buat Set Kemasan (Bundle)**")
            with st.form("create_bundle"):
                b_name = st.text_input("Nama Set (Misal: Paket Box Small)")
                if st.form_submit_button("BUAT SET"):
                    if b_name:
                        c = get_connection(); c.execute("INSERT INTO packaging_bundles (name) VALUES (?)", (b_name,)); c.commit(); c.close(); st.rerun()
            
            if not pkgs.empty and not bundles.empty:
                sel_b = st.selectbox("Pilih Set untuk Isi", bundles['name'].tolist())
                # Safe indexing
                match = bundles[bundles['name']==sel_b]
                if not match.empty:
                    bid = match['id'].values[0]
                    with st.form("add_item_bundle"):
                        item_pkg = st.selectbox("Pilih Item Kemasan", pkgs['name'].tolist())
                        qty_pkg = st.number_input("Jumlah per Produk Terjual", min_value=0.01, value=1.0)
                        if st.form_submit_button("TAMBAH KE SET"):
                            filtered_pkg = pkgs[pkgs['name']==item_pkg]
                            if not filtered_pkg.empty:
                                iid = filtered_pkg['id'].values[0]
                                c = get_connection(); c.execute("INSERT INTO packaging_bundle_items (bundle_id, inventory_id, qty) VALUES (?,?,?)", (bid, iid, qty_pkg)); c.commit(); c.close(); st.rerun()
                            else:
                                st.error("Item kemasan tidak ditemukan.")
            else:
                st.warning("Belum ada item dengan kategori 'Kemasan' atau 'Box' di gudang.")

        with col_b:
            st.markdown("**2. Hubungkan ke Kategori Produk**")
            with st.form("map_category"):
                target_cat = st.selectbox("Pilih Kategori Produk", CATEGORIES_MASTER)
                target_bundle = st.selectbox("Pilih Set Kemasan", ["None"] + bundles['name'].tolist())
                if st.form_submit_button("SIMPAN PEMETAAN"):
                    if target_bundle != "None":
                        bid = bundles[bundles['name']==target_bundle]['id'].values[0]
                        c = get_connection(); c.execute("INSERT OR REPLACE INTO category_packaging_map (category_name, bundle_id) VALUES (?,?)", (target_cat, bid)); c.commit(); c.close(); st.rerun()
            
            if not mapping.empty:
                st.write("---")
                st.markdown("**Pemetaan Aktif (Kategori ➡️ Set Kemasan)**")
                for idx, row in mapping.iterrows():
                    c_map1, c_map2 = st.columns([3, 1])
                    c_map1.write(f"📦 {row['category_name']} ➡️ {row['bundle_name']}")
                    if c_map2.button("🗑️ Hapus", key=f"del_map_{idx}"):
                        c = get_connection()
                        c.execute("DELETE FROM category_packaging_map WHERE category_name = ?", (row['category_name'],))
                        c.commit(); c.close(); st.success("Pemetaan dihapus."); st.rerun()
            else:
                st.info("Belum ada pemetaan kemasan otomatis.")

    # --- QUICK BARCODE UPDATE ---
    with st.expander("🏷️ Global Barcode Manager (Update Cepat)"):
        st.info("Gunakan ini untuk mengisi semua barcode bahan baku dalam satu waktu.")
        conn = get_connection()
        inv_data = pd.read_sql_query("SELECT id, name, barcode FROM inventory_master", conn)
        conn.close()
        
        with st.form("bulk_barcode_inv"):
            edited_codes = []
            for idx, row in inv_data.iterrows():
                c1, c2 = st.columns([2, 2])
                c1.write(f"**{row['name']}**")
                new_bc = c2.text_input(f"Barcode untuk {row['name']}", value=row['barcode'] if row['barcode'] else "", key=f"bc_inv_{row['id']}", label_visibility="collapsed")
                edited_codes.append((new_bc, row['id']))
            
            if st.form_submit_button("SIMPAN SEMUA BARCODE GUDANG"):
                c = get_connection()
                for bc, iid in edited_codes:
                    c.execute("UPDATE inventory_master SET barcode = ? WHERE id = ?", (bc, iid))
                c.commit(); c.close(); st.success("Semua Barcode Gudang Diperbarui!"); st.rerun()

    # end of module...
