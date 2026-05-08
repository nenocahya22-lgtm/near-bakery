import streamlit as st
import pandas as pd
from database_engine import get_connection
from utils import format_rp, get_dynamic_selling_price, render_luxury_table
import json
from datetime import datetime

def show_customer_portal():
    # CUSTOM CSS FOR PUBLIC STOREFRONT
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=Inter:wght@300;400;600&display=swap');
    
    .stApp { background: #FDFCFB !important; }
    
    .store-header {
        text-align: center;
        padding: 60px 20px;
        background: #1E1B18;
        color: #D4AF37;
        margin-bottom: 40px;
        border-bottom: 4px solid #D4AF37;
    }
    
    .product-card {
        background: white;
        border-radius: 20px;
        padding: 25px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.05);
        border: 1px solid rgba(212, 175, 55, 0.1);
        text-align: center;
        transition: 0.3s;
        margin-bottom: 20px;
    }
    .product-card:hover { transform: translateY(-10px); border: 1px solid #D4AF37; }
    
    .product-name { font-family: 'Playfair Display', serif; font-size: 1.5rem; font-weight: 900; color: #1E1B18; }
    .product-price { font-size: 1.2rem; color: #D4AF37; font-weight: 700; margin: 10px 0; }
    
    .checkout-bar {
        position: fixed;
        bottom: 20px;
        right: 20px;
        z-index: 1000;
    }
    </style>
    """, unsafe_allow_html=True)

    if 'web_cart' not in st.session_state: st.session_state.web_cart = []

    # --- HEADER ---
    st.markdown("""
    <div class='store-header'>
        <div style='font-size: 0.8rem; letter-spacing: 10px; margin-bottom: 10px;'>EST. 2026</div>
        <div style='font-family: "Playfair Display", serif; font-size: 3.5rem; font-weight: 900;'>NEAR BAKERY</div>
        <div style='font-size: 0.9rem; letter-spacing: 5px; opacity: 0.8;'>THE MORNING FLOUR</div>
    </div>
    """, unsafe_allow_html=True)

    c_main, c_cart = st.columns([2, 1])

    with c_main:
        st.markdown("### 🧁 Jelajahi Menu Kami")
        conn = get_connection()
        prods = pd.read_sql_query("SELECT id, name, category FROM recipe_master", conn)
        addons = pd.read_sql_query("SELECT name, price FROM product_addons", conn)
        conn.close()

        if not prods.empty:
            p_cols = st.columns(2)
            for idx, p in prods.iterrows():
                with p_cols[idx % 2]:
                    st.markdown(f"""
                    <div class='product-card'>
                        <div class='product-name'>{p['name']}</div>
                        <div style='font-size: 0.8rem; color: #8E8A85;'>{p['category']}</div>
                    """, unsafe_allow_html=True)
                    
                    price = get_dynamic_selling_price(p['id'])
                    st.markdown(f"<div class='product-price'>{format_rp(price)}</div>", unsafe_allow_html=True)
                    
                    # Add-ons for customer
                    sel_add = st.multiselect(f"Topping Tambahan", addons['name'].tolist(), key=f"web_add_{p['id']}")
                    
                    if st.button(f"🛒 TAMBAH KE KERANJANG", key=f"btn_web_{p['id']}", use_container_width=True):
                        st.session_state.web_cart.append({
                            'id': p['id'], 'name': p['name'], 'price': price, 'addons': sel_add
                        })
                        st.success("Ditambahkan!")
                    
        else:
            st.info("Menu sedang disiapkan. Silakan kembali lagi nanti.")

    with c_cart:
        st.markdown("### 🧾 Keranjang Saya")
        if st.session_state.web_cart:
            total = 0
            for i, item in enumerate(st.session_state.web_cart):
                with st.expander(f"{item['name']} ({format_rp(item['price'])})"):
                    st.write(f"Add-ons: {', '.join(item['addons']) if item['addons'] else '-'}")
                    if st.button("Hapus", key=f"web_del_{i}"):
                        st.session_state.web_cart.pop(i); st.rerun()
                total += item['price']
                # Calculate addons total
                for a_name in item['addons']:
                    a_price = addons[addons['name'] == a_name]['price'].values[0]
                    total += a_price

            st.markdown(f"## Total: {format_rp(total)}")
            
            st.markdown("---")
            st.markdown("#### Detail Pengiriman / Pengambilan")
            with st.form("web_checkout"):
                c_name = st.text_input("Nama Lengkap")
                c_phone = st.text_input("Nomor WhatsApp (628...)")
                c_note = st.text_area("Catatan Khusus (Contoh: Tanpa wijen)")
                
                if st.form_submit_button("🚀 KIRIM PESANAN SEKARANG"):
                    if c_name and c_phone:
                        conn = get_connection()
                        conn.execute("""
                            INSERT INTO web_orders (timestamp, customer_name, customer_phone, items_json, total_revenue, status)
                            VALUES (?,?,?,?,?,?)
                        """, (datetime.now(), c_name, c_phone, json.dumps(st.session_state.web_cart), total, 'PENDING'))
                        conn.commit(); conn.close()
                        st.balloons()
                        st.success(f"Terima kasih {c_name}! Pesanan Anda sedang diproses oleh Near Bakery.")
                        st.session_state.web_cart = []
                    else:
                        st.error("Lengkapi data Anda.")
        else:
            st.markdown("<div style='text-align: center; padding: 40px; opacity: 0.5;'>Keranjang Anda masih kosong.</div>", unsafe_allow_html=True)
