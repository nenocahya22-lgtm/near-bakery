import streamlit as st
import pandas as pd
from database_engine import get_connection
from utils import format_rp
import json
from datetime import datetime

st.set_page_config(page_title="Near Bakery | Freshly Baked for You", layout="centered")

# --- ROYAL CUSTOMER UI ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;0,900;1,700&family=Inter:wght@300;500;700&display=swap');

.stApp { background-color: #FCFAF7; }

.hero-section {
    text-align: center;
    padding: 60px 0;
    background: #1E1B18;
    color: #D4AF37;
    border-radius: 0 0 50px 50px;
    margin-bottom: 40px;
    box-shadow: 0 15px 30px rgba(0,0,0,0.1);
}
.hero-title { font-family: 'Playfair Display', serif; font-size: 3.5rem; font-weight: 900; margin: 0; }
.hero-tagline { letter-spacing: 5px; font-size: 0.9rem; text-transform: uppercase; opacity: 0.8; }

.product-card {
    background: white;
    border-radius: 20px;
    padding: 0;
    margin-bottom: 25px;
    box-shadow: 0 10px 20px rgba(0,0,0,0.03);
    border: 1px solid #F0EDE9;
    overflow: hidden;
    transition: 0.3s;
}
.product-card:hover { transform: translateY(-5px); box-shadow: 0 15px 30px rgba(212, 175, 55, 0.1); }

.product-info { padding: 20px; }
.product-name { font-family: 'Playfair Display', serif; font-size: 1.5rem; font-weight: 700; color: #1E1B18; }
.product-price { color: #D4AF37; font-weight: 700; font-size: 1.2rem; }

.cart-float {
    position: fixed;
    bottom: 20px;
    right: 20px;
    background: #D4AF37;
    color: white;
    padding: 15px 30px;
    border-radius: 50px;
    box-shadow: 0 10px 20px rgba(212, 175, 55, 0.4);
    z-index: 1000;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.markdown("""
<div class='hero-section'>
    <div class='hero-tagline'>Est. 2026</div>
    <h1 class='hero-title'>NEAR BAKERY</h1>
    <div class='hero-tagline'>The Morning Flour</div>
</div>
""", unsafe_allow_html=True)

if 'customer_cart' not in st.session_state: st.session_state.customer_cart = []

# --- MENU DATA ---
conn = get_connection()
# Get only recipes with prices set
products = pd.read_sql_query("SELECT id, name, category, barcode FROM recipe_master", conn)

st.markdown("<h2 style='text-align: center; font-family: \"Playfair Display\", serif;'>Our Signature Collection</h2>", unsafe_allow_html=True)
st.write("---")

from utils import get_dynamic_selling_price

if not products.empty:
    for _, p in products.iterrows():
        price = get_dynamic_selling_price(p['id'])
        with st.container():
            col1, col2 = st.columns([1, 2])
            # Placeholder image (In real app, use product images)
            col1.markdown(f"""
            <div style='background: #F0EDE9; height: 150px; border-radius: 15px; display: flex; align-items: center; justify-content: center; color: #8E8A85;'>
                [ Photo {p['name']} ]
            </div>
            """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"<div class='product-name'>{p['name']}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='product-price'>{format_rp(price)}</div>", unsafe_allow_html=True)
                if st.button(f"Add to Basket", key=f"btn_{p['id']}"):
                    st.session_state.customer_cart.append({'id': p['id'], 'name': p['name'], 'price': price})
                    st.toast(f"{p['name']} added to basket!")
            st.write("---")
else:
    st.info("Menu sedang disiapkan...")

# --- CART / CHECKOUT ---
if st.session_state.customer_cart:
    with st.sidebar:
        st.markdown("### 🛒 Your Basket")
        total = 0
        for idx, item in enumerate(st.session_state.customer_cart):
            st.write(f"**{item['name']}** - {format_rp(item['price'])}")
            if st.button("Remove", key=f"rem_{idx}"):
                st.session_state.customer_cart.pop(idx)
                st.rerun()
            total += item['price']
        
        st.write("---")
        st.markdown(f"### Total: {format_rp(total)}")
        
        with st.form("checkout"):
            name = st.text_input("Nama Anda")
            phone = st.text_input("WhatsApp (628...)")
            addr = st.text_area("Alamat Pengiriman")
            if st.form_submit_button("PLACE ORDER NOW"):
                if name and phone:
                    # Save to database
                    c = get_connection()
                    items_json = json.dumps(st.session_state.customer_cart)
                    c.execute("""
                        INSERT INTO web_orders (timestamp, customer_name, customer_phone, items_json, total_revenue, status)
                        VALUES (?,?,?,?,?,?)
                    """, (datetime.now(), name, phone, items_json, total, 'PENDING'))
                    c.commit(); c.close()
                    st.success("Order received! Our team will contact you via WhatsApp.")
                    st.session_state.customer_cart = []
                    st.balloons()
                else:
                    st.error("Lengkapi data pemesanan.")

# --- FOOTER ---
st.markdown("""
<div style='text-align: center; color: #8E8A85; padding: 40px 0; font-size: 0.8rem;'>
    &copy; 2026 Near Bakery & Co. All rights reserved.
</div>
""", unsafe_allow_html=True)
