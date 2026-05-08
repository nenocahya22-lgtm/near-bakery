import streamlit as st
import pandas as pd
from datetime import datetime
from database_engine import get_connection
from utils import format_rp, get_dynamic_selling_price

def show_pos():
    # --- POS STYLING ---
    st.markdown("""
    <style>
    .pos-product-card {
        background: white;
        padding: 15px;
        border-radius: 15px;
        border: 1px solid #E2E8F0;
        margin-bottom: 15px;
        text-align: center;
        transition: all 0.3s;
    }
    .pos-product-card:hover { transform: translateY(-5px); box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); }
    .cat-tag { background: #DBEAFE; color: #1E40AF; font-size: 0.6rem; padding: 2px 8px; border-radius: 10px; font-weight: bold; }
    .cart-item-card {
        background: white;
        border: 1px solid #F1F5F9;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    </style>
    """, unsafe_allow_html=True)

    if 'cart' not in st.session_state: st.session_state.cart = {}
    
    col_cart, col_menu = st.columns([1.3, 2])
    
    # --- LEFT SIDE: CART & INVOICE ---
    with col_cart:
        st.markdown("""
        <div style="background: white; border-radius: 16px 16px 0 0; padding: 20px; border: 1px solid #E2E8F0; border-bottom: none; min-height: 50vh;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h3 style="margin:0; color: #1E293B;">🧾 Daftar Pesanan</h3>
                <span style="background: #ECFDF5; color: #10B981; padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 700;">LIVE TERMINAL</span>
            </div>
        """, unsafe_allow_html=True)
        
        subtotal = 0
        if not st.session_state.cart:
            st.markdown("""
            <div style="text-align: center; padding: 40px 10px; color: #94A3B8;">
                <div style="font-size: 2.5rem; margin-bottom: 10px;">🧺</div>
                Belum ada pesanan aktif
            </div>
            """, unsafe_allow_html=True)
        else:
            conn = get_connection(); addons_db = pd.read_sql_query("SELECT name, price FROM product_addons", conn); conn.close()
            for pid, item in list(st.session_state.cart.items()):
                # Calculate Price with Add-ons
                base_p = item['price']
                sel_addons = item.get('selected_addons', [])
                addon_p = 0
                if not addons_db.empty:
                    addon_p = addons_db[addons_db['name'].isin(sel_addons)]['price'].sum()
                
                effective_p = base_p + addon_p
                item_sub = effective_p * item['qty']
                subtotal += item_sub
                
                st.markdown(f"""
                <div class="cart-item-card">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <div style="font-weight: 700; color: #1E293B;">{item['name']}</div>
                            <div style="font-size: 0.8rem; color: #64748B;">{format_rp(base_p)} / unit</div>
                        </div>
                        <div style="font-weight: 800; color: #3B82F6;">{format_rp(item_sub)}</div>
                    </div>
                """, unsafe_allow_html=True)
                
                # Note & Add-ons
                c_addons, c_notes = st.columns([1, 1.2])
                with c_addons:
                    if not addons_db.empty:
                        new_addons = st.multiselect(f"✨ Add-ons", options=addons_db['name'].tolist(), default=sel_addons, key=f"add_{pid}", label_visibility="collapsed")
                        if new_addons != sel_addons:
                            st.session_state.cart[pid]['selected_addons'] = new_addons
                            st.rerun()
                with c_notes:
                    item_note = st.text_input(f"📝 Notes", value=item.get('note', ""), key=f"note_{pid}", placeholder="Keterangan...", label_visibility="collapsed")
                    st.session_state.cart[pid]['note'] = item_note

                # Quantity Controls
                cq1, cq2, cq3 = st.columns([1, 1, 1])
                if cq1.button("➖", key=f"min_{pid}", use_container_width=True):
                    if st.session_state.cart[pid]['qty'] > 1: st.session_state.cart[pid]['qty'] -= 1
                    else: del st.session_state.cart[pid]
                    st.rerun()
                cq2.markdown(f"<center><div style='padding-top:10px; font-weight:800;'>{item['qty']}</div></center>", unsafe_allow_html=True)
                if cq3.button("➕", key=f"plus_{pid}", use_container_width=True):
                    st.session_state.cart[pid]['qty'] += 1
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

        # --- ACTION BUTTONS (FOOTER) ---
        st.markdown("""<div style="background: #F8FAFC; border: 1px solid #E2E8F0; padding: 15px; display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px;">""", unsafe_allow_html=True)
        ca1, ca2, ca3 = st.columns(3)
        if ca1.button("📠 Cetak", use_container_width=True):
            if 'last_bill' in st.session_state: st.session_state.print_requested = True
            else: st.toast("Belum ada data")
        ca2.button("🏷️ Diskon", use_container_width=True)
        ca3.button("🚚 Kirim", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # --- TOTAL BAR ---
        tax = subtotal * 0.11; grand_total = subtotal + tax
        st.markdown(f"""
        <div style="background: #10B981; color: white; padding: 20px; border-radius: 0 0 16px 16px; display: flex; justify-content: space-between; align-items: center;">
            <span style="font-weight: 600; font-size: 1rem;">TOTAL AKHIR</span>
            <span style="font-weight: 800; font-size: 1.6rem;">{format_rp(grand_total)}</span>
        </div>
        """, unsafe_allow_html=True)
        
        if subtotal > 0:
            st.write("")
            pay_method = st.radio("Metode Pembayaran", ["TUNAI", "QRIS", "DEBIT"], horizontal=True)
            if st.button("🚀 PROSES PEMBAYARAN (F9)", use_container_width=True, type="primary"):
                conn = get_connection()
                conn.execute("INSERT INTO sales_log (total_revenue, profit, timestamp, payment_method) VALUES (?,?,?,?)", 
                             (grand_total, grand_total*0.3, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), pay_method))
                conn.execute("UPDATE business_vault SET current_balance = current_balance + ?", (grand_total,))
                conn.commit(); conn.close()
                st.session_state.last_bill = st.session_state.cart.copy()
                st.session_state.last_total = grand_total
                st.session_state.cart = {}
                st.success("Transaksi Berhasil!")
                st.rerun()

    # --- RIGHT SIDE: MENU SELECTION ---
    with col_menu:
        st.markdown("### 🥨 Menu Near Bakery")
        t1, t2 = st.columns([3, 2])
        search = t1.text_input("🔍 Cari Produk...", placeholder="Ketik nama produk...")
        barcode = t2.text_input("📋 Scan Barcode", placeholder="Arahkan scanner...")

        if barcode:
            conn = get_connection(); b_prod = conn.execute("SELECT id, name, discount_pct FROM recipe_master WHERE barcode = ?", (barcode,)).fetchone(); conn.close()
            if b_prod:
                pid = b_prod[0]
                if pid in st.session_state.cart: st.session_state.cart[pid]['qty'] += 1
                else: 
                    fixed_p = b_prod[3] or 0
                    p_price = fixed_p if fixed_p > 0 else get_dynamic_selling_price(pid)
                    p_price = p_price * (1 - (b_prod[2] or 0)/100)
                    st.session_state.cart[pid] = {'name': b_prod[1], 'price': p_price, 'qty': 1, 'selected_addons': [], 'note': ""}
                st.toast(f"✅ {b_prod[1]} ditambahkan!")

        conn = get_connection(); products = pd.read_sql_query("SELECT id, name, category, discount_pct FROM recipe_master", conn); conn.close()
        if not products.empty:
            filtered = products[products['name'].str.contains(search, case=False)]
            p_cols = st.columns(3)
            for idx, p in filtered.reset_index().iterrows():
                with p_cols[idx % 3]:
                    fixed_p = p.get('selling_price', 0)
                    base_p = fixed_p if fixed_p > 0 else get_dynamic_selling_price(p['id'])
                    d_pct = p.get('discount_pct', 0)
                    final_p = base_p * (1 - d_pct/100) if d_pct > 0 else base_p
                    st.markdown(f'<div class="pos-product-card"><span class="cat-tag">{p["category"]}</span><div style="font-weight: bold; margin-top:10px;">{p["name"]}</div><div style="font-weight: 800; color: #1E3A8A; margin-top:5px;">{format_rp(final_p)}</div></div>', unsafe_allow_html=True)
                    if st.button("TAMBAH", key=f"add_{p['id']}", use_container_width=True):
                        pid = p['id']
                        if pid in st.session_state.cart: st.session_state.cart[pid]['qty'] += 1
                        else: st.session_state.cart[pid] = {'name': p['name'], 'price': final_p, 'qty': 1, 'selected_addons': [], 'note': ""}
                        st.rerun()
        else:
            st.markdown("""
            <div style="background: #F8FAFC; border: 1px dashed #E2E8F0; border-radius: 16px; padding: 40px; text-align: center;">
                <div style="font-size: 3rem; margin-bottom: 20px;">🥨</div>
                <h3 style="color: #1E293B; margin-bottom: 10px;">Etalase Siap Digunakan</h3>
                <p style="color: #64748B; margin-bottom: 30px;">Tambahkan produk di menu <b>Resep</b> untuk mulai berjualan.</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button("🚀 BUAT PRODUK PERTAMA SEKARANG", use_container_width=True, type="primary"):
                st.session_state.page = 'Resep'
                st.rerun()

    # --- PRINT LOGIC ---
    if st.session_state.get('print_requested', False):
        st.session_state.print_requested = False
        bill_items = "".join([f"<tr><td>{v['qty']}x {v['name']}</td><td align='right'>{format_rp((v['price'] + sum([addons_db[addons_db['name']==a]['price'].values[0] for a in v.get('selected_addons', [])]))*v['qty'])}</td></tr>" for k,v in st.session_state.last_bill.items()])
        receipt = f"""
        <div style="width: 58mm; padding: 5px; background: white; color: black; font-family: 'Courier New', monospace; font-size: 12px;">
            <center><b>NEAR BAKERY</b><br>--- STRUK PEMBAYARAN ---</center><br>
            <table width="100%">{bill_items}</table>
            --------------------------<br>
            <b>TOTAL: <span style='float:right'>{format_rp(st.session_state.last_total)}</span></b><br>
            <center><br>Terima Kasih!</center>
        </div>
        <script>window.print();</script>
        """
        st.components.v1.html(receipt, height=500)
