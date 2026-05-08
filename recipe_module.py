# recipe_module.py
from datetime import datetime
import streamlit as st
import pandas as pd
from database_engine import get_connection
from utils import format_rp, UNITS_MASTER, CATEGORIES_MASTER, render_luxury_table
import json

def show_recipes():
    
    st.markdown("## 👨‍🍳 Manajemen Resep & Produksi")
    
    tab_recipes, tab_addons, tab_scaling = st.tabs([
        "🧁 Resep Produk Utama", 
        "✨ Manajemen Add-ons",
        "⚖️ Kalkulator Produksi (Scaling)"
    ])
    
    conn = get_connection()
    inv_list = pd.read_sql_query("SELECT id, name, price_per_unit_pakai, unit_pakai, stock FROM inventory_master", conn)
    res_m = conn.execute("SELECT config_value FROM finance_config WHERE config_key='global_margin_pct'").fetchone()
    global_margin = res_m[0] if res_m else 100.0
    conn.close()

    with tab_recipes:
        st.markdown("### 📜 Manajemen Resep Produk")
        
        with st.expander("📝 Buat Resep Produk Baru", expanded=True):
            c1, c2, r3 = st.columns(3)
            r_name = c1.text_input("Nama Produk")
            c2.info("🆔 ID Produk: Auto-Generated")
            r_cat = r3.selectbox("Kategori", CATEGORIES_MASTER)
            
            c4, c5, r6 = st.columns(3)
            r_yield = c4.number_input("Hasil Produksi (Jumlah)", min_value=0.01, value=1.0)
            r_unit = c5.selectbox("Satuan Hasil", ["Pcs", "Loyang", "Box", "Slice", "Gram"], key="res_unit")
            r_image = r6.file_uploader("📸 Foto Produk", type=['png', 'jpg', 'jpeg'])

            st.markdown("---")
            st.markdown("**Komposisi Bahan Baku**")
            
            if 'recipe_rows' not in st.session_state: st.session_state.recipe_rows = 1
            
            ings_data = []
            for i in range(st.session_state.recipe_rows):
                ca, cb, cc = st.columns([3, 2, 2])
                ing_name = ca.selectbox(f"Bahan {i+1}", ["-- Pilih Bahan --"] + inv_list['name'].tolist(), key=f"ing_{i}")
                ing_qty = cb.number_input(f"Jumlah", min_value=0.0, key=f"qty_{i}")
                
                # Dropdown Satuan
                options = UNITS_MASTER
                default_idx = 0
                
                filtered_inv = inv_list[inv_list['name'] == ing_name]
                if not filtered_inv.empty:
                    iid = int(filtered_inv['id'].values[0])
                    d_unit = filtered_inv['unit_pakai'].values[0]
                    if d_unit in options: default_idx = options.index(d_unit)
                    
                    ing_unit = cc.selectbox(f"Satuan {i+1}", options, index=default_idx, key=f"unit_{i}")
                    ings_data.append((iid, ing_qty, ing_unit))
                else:
                    st.session_state[f"unit_{i}"] = "Gram (gr)" # Fallback
                    cc.selectbox(f"Satuan {i+1}", options, index=1, key=f"unit_{i}")

            # --- PROFESSIONAL ACTION BUTTONS AT THE BOTTOM ---
            st.write("")
            b1, b2, b3 = st.columns([1, 1, 2])
            if b1.button("➕ TAMBAH BAHAN", use_container_width=True):
                st.session_state.recipe_rows += 1
                st.rerun()
            if b2.button("❌ HAPUS BARIS", use_container_width=True):
                if st.session_state.recipe_rows > 1:
                    st.session_state.recipe_rows -= 1
                    st.rerun()
            
            st.write("---")
            if b3.button("✨ SIMPAN RESEP PRODUK", use_container_width=True):
                if r_name and ings_data:
                    import random, string, os
                    fid = "NB-PROD-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
                    
                    # Handle Image
                    img_path = None
                    if r_image:
                        if not os.path.exists("uploads"): os.makedirs("uploads")
                        img_path = f"uploads/prod_{fid}.png"
                        with open(img_path, "wb") as f: f.write(r_image.getbuffer())
                    
                    conn = get_connection()
                    conn.execute("INSERT INTO recipe_master (name, barcode, category, yield_qty, yield_unit, image_path) VALUES (?,?,?,?,?,?)", (r_name, fid, r_cat, r_yield, r_unit, img_path))
                    rid = conn.lastrowid
                    for i_id, i_qty, i_unit in ings_data: 
                        conn.execute("INSERT INTO recipe_ingredients (recipe_id, inventory_id, qty_pakai, unit) VALUES (?,?,?,?)", (rid, i_id, i_qty, i_unit))
                    conn.commit(); conn.close()
                    st.success(f"Resep {r_name} tersimpan!"); st.session_state.recipe_rows = 1; st.rerun()
                else:
                    st.error("Lengkapi data dan pilih bahan baku.")

        st.subheader("📋 Daftar Resep Produksi Aktif")
        conn = get_connection()
        recs = pd.read_sql_query("SELECT * FROM recipe_master", conn)
        conn.close()
        if not recs.empty:
            for _, r in recs.iterrows():
                with st.expander(f"📁 {r['name']} (ID: {r['barcode']})"):
                    c_info, c_img = st.columns([2, 1])
                    with c_info:
                        st.write(f"**Kategori:** {r['category']}")
                        st.write(f"**Hasil:** {r['yield_qty']} {r['yield_unit']}")
                        
                        # --- LIST INGREDIENTS ---
                        st.markdown("**Komposisi Bahan:**")
                        c_ing = get_connection()
                        ings_list = pd.read_sql_query("""
                            SELECT i.name, ri.qty_pakai, ri.unit 
                            FROM recipe_ingredients ri
                            JOIN inventory_master i ON ri.inventory_id = i.id
                            WHERE ri.recipe_id = ?
                        """, c_ing, params=(int(r['id']),))
                        c_ing.close()
                        
                        if not ings_list.empty:
                            for _, ing in ings_list.iterrows():
                                st.markdown(f"- {ing['name']}: {ing['qty_pakai']} {ing['unit'] if ing['unit'] else ''}")
                        else:
                            st.write("No ingredients listed.")
                    with c_img:
                        if r['image_path'] and os.path.exists(r['image_path']):
                            st.image(r['image_path'], width=150)
                        else:
                            st.write("No Image")
                    
                    if st.session_state.role == 'OWNER':
                        if st.button("🗑️ HAPUS PERMANEN", key=f"direct_del_rec_{r['id']}", use_container_width=True):
                            c = get_connection()
                            c.execute("DELETE FROM recipe_master WHERE id = ?", (int(r['id']),))
                            c.execute("DELETE FROM recipe_ingredients WHERE recipe_id = ?", (int(r['id']),))
                            c.commit(); c.close(); st.success(f"Resep {r['name']} dihapus!"); st.rerun()
                    else:
                        r_del_reason = st.text_input("Alasan Hapus Resep", key=f"reason_rec_{r['id']}")
                        if st.button("AJUKAN HAPUS RESEP", key=f"btn_del_rec_{r['id']}", use_container_width=True):
                            if r_del_reason:
                                payload = {"id": r['id'], "name": r['name']}
                                c = get_connection()
                                c.execute("INSERT INTO pending_approvals (timestamp, user_requester, action_type, description, data_payload, reason) VALUES (?,?,?,?,?,?)",
                                         (pd.Timestamp.now(), st.session_state.user, "HAPUS_RESEP", f"Menghapus Resep: {r['name']}", json.dumps(payload), r_del_reason))
                                c.commit(); c.close(); st.info("Pengajuan hapus resep dikirim ke Owner."); st.rerun()
                            else: st.warning("Isi alasan hapus.")
        else: 
            st.markdown("""
            <div style="text-align: center; padding: 60px 20px; background: #F8FAFC; border-radius: 16px; border: 2px dashed #E2E8F0;">
                <div style="font-size: 3rem; margin-bottom: 20px;">👨‍🍳</div>
                <h3 style="color: #64748B; margin-bottom: 10px;">Belum Ada Resep</h3>
                <p style="color: #94A3B8; font-size: 0.9rem; margin-bottom: 25px;">Pastikan stok bahan baku sudah terdaftar di Gudang sebelum membuat resep.</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button("📦 CEK STOK GUDANG", use_container_width=True):
                st.session_state.page = 'Inventaris'
                st.rerun()

    # --- TAB 2: ADD-ONS ---
    with tab_addons:
        st.subheader("✨ Registrasi Add-ons")
        with st.form("addon_form"):
            st.markdown("**Tambah Add-on / Toping Baru**")
            c_f1, c_f2, c_f3, c_f4 = st.columns([3, 2, 1, 1])
            a_name = c_f1.text_input("Nama Add-on")
            a_inv = c_f2.selectbox("Pilih Material Gudang", ["-- Pilih Bahan --"] + inv_list['name'].tolist())
            a_qty = c_f3.number_input("Jumlah", min_value=0.0)
            # from utils import UNITS_MASTER (already at top)
            a_unit = c_f4.selectbox("Satuan", UNITS_MASTER)
            
            sel_rows = inv_list[inv_list['name'] == a_inv]
            if not sel_rows.empty:
                sel_item = sel_rows.iloc[0]
                u_label = sel_item['unit_pakai']
                st.info(f"💡 Pengurangan stok otomatis menggunakan satuan gudang: **{u_label}**")
                
                est_cost = sel_item['price_per_unit_pakai'] * a_qty
                est_sell = est_cost * (1 + global_margin/100)
                st.markdown(f"**Estimasi Modal:** {format_rp(est_cost)} | **Saran Jual (+Margin):** {format_rp(est_sell)}")
                manual_price = st.number_input("Harga Jual Final (Top-up ke Harga Roti)", min_value=0.0, value=float(est_sell))
                
                if st.form_submit_button("SIMPAN ADD-ON"):
                    if a_name:
                        c = get_connection(); c.execute("INSERT INTO product_addons (name, price, inventory_id, qty_deduct) VALUES (?,?,?,?)", (a_name, manual_price, int(sel_item['id']), a_qty)); c.commit(); c.close(); st.success(f"Add-on {a_name} tersimpan!"); st.rerun()
            else:
                st.warning("Pilih bahan baku untuk melihat estimasi harga.")
                st.form_submit_button("SIMPAN ADD-ON (TUNGGU PILIHAN)", disabled=True)
        
        st.write("---")
        st.markdown("#### 📋 Daftar Add-ons & Toping Aktif")
        c = get_connection()
        addons_df = pd.read_sql_query("""
            SELECT a.id, a.name as "Nama Add-on", i.name as "Bahan Dasar", 
                   a.qty_deduct as "Qty", i.unit_pakai as "Satuan", a.price as "Harga Jual"
            FROM product_addons a
            JOIN inventory_master i ON a.inventory_id = i.id
        """, c)
        c.close()
        
        if not addons_df.empty:
            addons_df['Harga Jual'] = addons_df['Harga Jual'].apply(format_rp)
            st.markdown(render_luxury_table(addons_df), unsafe_allow_html=True)
            
            if st.session_state.role == 'OWNER':
                sel_addon_del = st.selectbox("Pilih Add-on untuk Dihapus Langsung", ["None"] + addons_df['Nama Add-on'].tolist())
                if sel_addon_del != "None":
                    if st.button("🗑️ HAPUS ADD-ON SEKARANG"):
                        aid = int(addons_df[addons_df['Nama Add-on'] == sel_addon_del].iloc[0]['id'])
                        c = get_connection(); c.execute("DELETE FROM product_addons WHERE id = ?", (aid,)); c.commit(); c.close()
                        st.success(f"Add-on {sel_addon_del} dihapus!"); st.rerun()
            else:
                sel_addon_del = st.selectbox("Pilih Add-on untuk Diajukan Hapus", ["None"] + addons_df['Nama Add-on'].tolist())
                if sel_addon_del != "None":
                    a_del_reason = st.text_input("Alasan Hapus Add-on")
                    if st.button("AJUKAN HAPUS ADD-ON"):
                        if a_del_reason:
                            aid = int(addons_df[addons_df['Nama Add-on'] == sel_addon_del].iloc[0]['id'])
                            payload = {"id": aid, "name": sel_addon_del}
                            c = get_connection()
                            c.execute("INSERT INTO pending_approvals (timestamp, user_requester, action_type, description, data_payload, reason) VALUES (?,?,?,?,?,?)",
                                     (pd.Timestamp.now(), st.session_state.user, "HAPUS_ADDON", f"Menghapus Add-on: {sel_addon_del}", json.dumps(payload), a_del_reason))
                            c.commit(); c.close(); st.info("Pengajuan dikirim."); st.rerun()
                        else: st.warning("Isi alasan.")

    # --- TAB 3: SCALING ---
    with tab_scaling:
        st.subheader("⚖️ Kalkulator Produksi")
        conn = get_connection(); recs_list = pd.read_sql_query("SELECT id, name, yield_qty, yield_unit FROM recipe_master", conn); conn.close()
        if not recs_list.empty:
            sel_r = st.selectbox("Pilih Produk:", recs_list['name'].tolist()); target_qty = st.number_input(f"Target Hasil", min_value=0.1, value=10.0)
            if st.button("HITUNG KEBUTUHAN BAHAN", use_container_width=True):
                r_data = recs_list[recs_list['name'] == sel_r].iloc[0]; mult = target_qty / r_data['yield_qty']
                conn = get_connection(); ings = pd.read_sql_query("SELECT i.name as 'Bahan', (ri.qty_pakai * ?) as 'Butuh', i.unit_pakai as 'Satuan', i.stock as 'Stok' FROM recipe_ingredients ri JOIN inventory_master i ON ri.inventory_id = i.id WHERE ri.recipe_id = ?", conn, params=(mult, int(r_data['id']))); conn.close()
                st.markdown(f"### 📋 Daftar Belanja: {sel_r}"); ings['Status'] = ings.apply(lambda x: "⚠️ KURANG" if x['Stok'] < x['Butuh'] else "✅ CUKUP", axis=1); st.markdown(render_luxury_table(ings), unsafe_allow_html=True)
        else: st.info("Belum ada resep.")
        st.markdown("---")
        # --- QUICK BARCODE UPDATE FOR PRODUCTS ---
        with st.expander("🏷️ Global Barcode Manager (Update Barcode Roti)"):
            st.info("Gunakan ini untuk mengisi semua barcode produk jualan agar bisa di-scan di Kasir.")
            conn = get_connection()
            prod_data = pd.read_sql_query("SELECT id, name, barcode FROM recipe_master", conn)
            conn.close()
            
            with st.form("bulk_barcode_prod"):
                edited_codes = []
                for idx, row in prod_data.iterrows():
                    c1, c2 = st.columns([2, 2])
                    c1.write(f"**{row['name']}**")
                    new_bc = c2.text_input(f"Barcode untuk {row['name']}", value=row['barcode'] if row['barcode'] else "", key=f"bc_prod_{row['id']}", label_visibility="collapsed")
                    edited_codes.append((new_bc, row['id']))
                
                if st.form_submit_button("SIMPAN SEMUA BARCODE PRODUK"):
                    c = get_connection()
                    for bc, rid in edited_codes:
                        c.execute("UPDATE recipe_master SET barcode = ? WHERE id = ?", (bc, rid))
                    c.commit(); c.close(); st.success("Semua Barcode Produk Diperbarui!"); st.rerun()

    
