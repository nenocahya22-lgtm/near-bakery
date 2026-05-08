import streamlit as st
import pandas as pd
from database_engine import get_connection
from utils import format_rp
from datetime import datetime

def show_customer_portal():
    # --- SHOPPING CART STATE ---
    if 'online_cart' not in st.session_state: st.session_state.online_cart = {}

    # --- CUSTOMER UI STYLING (The Shopee-Luxury Hybrid) ---
    st.markdown(f"""
    <style>
    .block-container {{ padding: 0 !important; max-width: 100% !important; }}
    .stApp {{ background: #FFFFFF; }}
    
    /* FLOATING HEADER */
    .floating-header {{
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        padding: 15px 8%;
        display: flex;
        justify-content: space-between;
        align-items: center;
        z-index: 1000;
        box-shadow: 0 2px 15px rgba(0,0,0,0.05);
        border-bottom: 1px solid #F1F5F9;
    }}
    
    .cart-badge {{
        background: #FF6B35;
        color: white;
        border-radius: 50%;
        padding: 2px 8px;
        font-size: 0.7rem;
        position: absolute;
        top: -10px;
        right: -10px;
        font-weight: bold;
    }}

    /* HERO SECTION */
    .hero-section {{
        background-color: #3D2B1F;
        padding: 160px 8% 100px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        color: white;
        background-image: linear-gradient(rgba(0,0,0,0.3), rgba(0,0,0,0.3)), url('https://images.unsplash.com/photo-1509440159596-0249088772ff?auto=format&fit=crop&w=1920&q=80');
        background-size: cover;
        background-position: center;
    }}
    
    .product-card {{
        background: #FFFFFF;
        border-radius: 15px;
        padding: 15px;
        border: 1px solid #F1F5F9;
        margin-bottom: 40px;
        transition: 0.3s;
    }}
    .product-card:hover {{ box-shadow: 0 20px 40px rgba(0,0,0,0.08); transform: translateY(-5px); }}
    
    .product-img {{
        width: 100%;
        height: 250px;
        object-fit: cover;
        border-radius: 10px;
        margin-bottom: 15px;
    }}
    </style>
    """, unsafe_allow_html=True)

    # --- CALCULATE TOTALS ---
    cart_count = sum(item['qty'] for item in st.session_state.online_cart.values())
    cart_total = sum(item['price'] * item['qty'] for item in st.session_state.online_cart.values())

    # --- RENDER FLOATING HEADER ---
    st.markdown(f"""
    <div class="floating-header">
        <div style="font-family: 'Playfair Display', serif; font-weight: 900; font-size: 1.5rem; color: #3D2B1F;">NEAR BAKERY</div>
        <div style="position: relative; display: flex; align-items: center; gap: 20px;">
            <div style="text-align: right;">
                <div style="font-size: 0.7rem; color: #64748B;">Total Belanja</div>
                <div style="font-weight: 700; color: #FF6B35;">{format_rp(cart_total)}</div>
            </div>
            <div style="position: relative; font-size: 1.5rem; cursor: pointer;">
                ðŸ›’ <span class="cart-badge">{cart_count}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- HERO SECTION ---
    st.markdown(f"""
    <div class="hero-section">
        <div class="hero-text">
            <p style="letter-spacing: 5px; color: #FF6B35; font-weight: 700;">PREMIUM SELECTION</p>
            <h1 style="font-family: 'Playfair Display', serif; font-size: 4.5rem; margin: 0;">Near Bakery</h1>
            <div style="font-size: 1.1rem; margin: 20px 0 40px; opacity: 0.9; max-width: 500px;">
                Cita rasa mewah dalam setiap gigitan. Dibuat dengan cinta untuk menemani momen spesial Anda.
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- PRODUCT CATALOG ---
    st.markdown("<div style='padding: 60px 8%;'>", unsafe_allow_html=True)
    
    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.markdown("<h2 style='font-family: \"Playfair Display\", serif;'>ðŸ¥ Katalog Pagi Ini</h2>", unsafe_allow_html=True)
        conn = get_connection()
        products = pd.read_sql_query("SELECT id, name, category, discount_pct, image_path FROM recipe_master", conn)
        conn.close()

        if products.empty:
            st.markdown(f"""
            <div style="text-align: center; padding: 100px 8%; background: #F8FAFC; border-radius: 30px; margin-top: 50px;">
                <h2 style="font-family: 'Playfair Display', serif; color: #3D2B1F;">Curating Our Masterpieces</h2>
                <p style="color: #64748B; max-width: 500px; margin: 20px auto;">
                    Tim artisan kami sedang mempersiapkan koleksi roti terbaik untuk Anda. 
                    Nantikan keajaiban rasa yang akan segera hadir di etalase Near Bakery.
                </p>
                <div style="font-size: 3rem;">ðŸ¥âœ¨</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            p_cols = st.columns(2)
            for idx, p in products.iterrows():
                with p_cols[idx % 2]:
                    from utils import get_dynamic_selling_price
                    base_price = get_dynamic_selling_price(p['id'])
                    disc_pct = p.get('discount_pct', 0)
                    final_price = base_price * (1 - disc_pct/100) if disc_pct > 0 else base_price
                    img_url = p.get('image_path') or "https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=400"
                    
                    st.markdown(f"""
                    <div class="product-card">
                        <img src="{img_url}" class="product-img">
                        <div style="font-weight: 700; font-size: 1.1rem;">{p['name']}</div>
                        <div style="color: #FF6B35; font-weight: 700; margin: 5px 0 15px;">{format_rp(final_price)}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"ðŸ›’ TAMBAH KE KERANJANG", key=f"add_{p['id']}", width="stretch"):
                        pid = str(p['id'])
                        if pid in st.session_state.online_cart:
                            st.session_state.online_cart[pid]['qty'] += 1
                        else:
                            st.session_state.online_cart[pid] = {'name': p['name'], 'price': final_price, 'qty': 1}
                        st.rerun()

    with c2:
        st.markdown("<div style='background: #F8FAFC; padding: 25px; border-radius: 20px; position: sticky; top: 100px;'>", unsafe_allow_html=True)
        st.markdown("### ðŸ›ï¸ Keranjang Saya")
        if not st.session_state.online_cart:
            st.write("Keranjang masih kosong.")
        else:
            for pid, item in st.session_state.online_cart.items():
                st.markdown(f"""
                <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                    <div><b>{item['name']}</b><br><small>{item['qty']}x {format_rp(item['price'])}</small></div>
                    <div style="font-weight: 700;">{format_rp(item['price'] * item['qty'])}</div>
                </div>
                """, unsafe_allow_html=True)
                # Tombol Kurang/Tambah
                k1, k2 = st.columns(2)
                if k1.button("âž–", key=f"min_{pid}"):
                    st.session_state.online_cart[pid]['qty'] -= 1
                    if st.session_state.online_cart[pid]['qty'] <= 0: del st.session_state.online_cart[pid]
                    st.rerun()
                if k2.button("âž•", key=f"plus_{pid}"):
                    st.session_state.online_cart[pid]['qty'] += 1
                    st.rerun()
            
            st.write("---")
            st.markdown(f"#### Total: <span style='color: #FF6B35;'>{format_rp(cart_total)}</span>", unsafe_allow_html=True)
            if st.button("ðŸš€ CHECKOUT SEKARANG", width="stretch", type="primary"):
                # Simpan ke pending_approvals
                import json
                conn = get_connection()
                payload = json.dumps(list(st.session_state.online_cart.values()))
                conn.execute("INSERT INTO pending_approvals (timestamp, user_requester, action_type, description, data_payload) VALUES (?,?,?,?,?)",
                             (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "ONLINE_CUSTOMER", "ONLINE_ORDER", 
                              f"Pesanan Online: {cart_count} item - Total {format_rp(cart_total)}", payload))
                conn.commit(); conn.close()
                st.session_state.online_cart = {}
                st.success("Pesanan Berhasil Dikirim! Mohon tunggu konfirmasi toko.")
                st.rerun()
        

    
