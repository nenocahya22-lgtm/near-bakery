# --- NEAR BAKERY & CO. EXECUTIVE ERP TERMINAL ---
import streamlit as st
import pandas as pd
import sqlite3
import os
import base64
import datetime
from database_engine import get_connection
from utils import format_rp, render_luxury_table
from inventory_module import show_inventory
from purchase_module import show_purchase
from recipe_module import show_recipes
from pos_module import show_pos
from waste_module import show_waste
from approval_module import show_approval
from finance_module import show_finance
from accounting_module import show_accounting
from integration_module import show_integration
from customer_module import show_customers
from vault_module import show_vault
from customer_portal import show_customer_portal
from communication_module import show_communication
from settings_module import show_settings
from health_module import show_health_center, run_system_health_check
from custom_order_module import show_custom_order
from tracking_module import show_tracking
from rd_module import show_rd
from pricing_module import show_pricing_architect

# 1. PAGE CONFIG
st.set_page_config(page_title="Near Bakery & Co.", layout="wide", initial_sidebar_state="expanded")

# 2. SESSION INITIALIZATION
if 'auth' not in st.session_state: st.session_state.auth = False
if 'page' not in st.session_state: st.session_state.page = 'Dashboard'
if 'user' not in st.session_state: st.session_state.user = None
if 'role' not in st.session_state: st.session_state.role = None
if 'permissions' not in st.session_state: st.session_state.permissions = []

# 3. DUAL LINK GATEWAY (Customer Portal)
query_params = st.query_params
if "mode" in query_params and query_params["mode"] == "shop":
    st.session_state.page = 'Storefront'
    st.session_state.auth = True

if st.session_state.page == 'Storefront':
    show_customer_portal()
    st.stop()

# 4. TERMINAL AUTHENTICATION (Login Page)
if not st.session_state.auth:
    st.markdown("""
    <style>
    /* EXECUTIVE LOGIN THEME */
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(rgba(0,0,0,0.85), rgba(0,0,0,0.85)), 
                    url('https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=1920') !important;
        background-size: cover !important;
        background-position: center !important;
    }
    .stMain { background: transparent !important; padding: 0 !important; }
    [data-testid="stHeader"], [data-testid="stSidebar"] { display: none !important; }
    [data-testid="stSidebarCollapsedControl"] { display: none !important; }

    /* CARD SELECTOR */
    [data-testid="column"] [data-testid="stVerticalBlock"] {
        background: white !important;
        padding: 50px !important;
        border-radius: 4px !important;
        box-shadow: 0 40px 80px rgba(0,0,0,0.6) !important;
        min-width: 400px !important;
        width: 400px !important;
        margin: 0 auto !important;
    }
    .brand-title {
        font-family: 'Outfit', sans-serif; font-weight: 800; font-size: 1.8rem;
        color: #0F172A; text-align: center; white-space: nowrap; margin-bottom: 5px;
    }
    .brand-subtitle {
        font-size: 0.8rem; color: #64748B; font-weight: 600; text-transform: uppercase;
        letter-spacing: 2px; text-align: center; white-space: nowrap; margin-bottom: 30px; display: block;
    }
    .stTextInput label { color: #0F172A !important; font-weight: 700 !important; font-size: 0.85rem !important; }
    .stTextInput input { border: 1px solid #E2E8F0 !important; border-radius: 4px !important; height: 48px !important; }
    .stButton > button {
        background: #0F172A !important; color: white !important; border-radius: 4px !important;
        height: 50px !important; font-weight: 700 !important; width: 100% !important; border: none !important; margin-top: 20px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height: 18vh;'></div>", unsafe_allow_html=True)
    _, col_center, _ = st.columns([1, 1, 1])
    with col_center:
        st.markdown('<h1 class="brand-title">NEAR BAKERY & CO.</h1>', unsafe_allow_html=True)
        st.markdown('<span class="brand-subtitle">Internal ERP System</span>', unsafe_allow_html=True)
        u = st.text_input("Username", placeholder="ID User", key="erp_u")
        p = st.text_input("Password", type="password", placeholder="Password", key="erp_p")
        if st.button("LOGIN", use_container_width=True):
            conn = get_connection(); user = conn.execute("SELECT username, role, permissions FROM users WHERE username=? AND password=?", (u, p)).fetchone(); conn.close()
            if user: 
                st.session_state.auth = True; st.session_state.user = user[0]; st.session_state.role = user[1]
                import json
                try: st.session_state.permissions = json.loads(user[2]) if user[2] else []
                except: st.session_state.permissions = []
                st.rerun()
            else: st.error("Login Gagal: Periksa ID/Password.")
        st.markdown("<p style='text-align:center; margin-top:30px; font-size:0.65rem; color:#94A3B8; letter-spacing:1px;'>SECURE ACCESS ONLY</p>", unsafe_allow_html=True)
    st.stop()

# 5. DASHBOARD UI STYLING (Post-Login)
def apply_executive_ui():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');
    [data-testid="stAppViewContainer"] { background: #F8FAFC !important; }
    .stMain { padding: 1.5rem 2rem !important; }
    [data-testid="stSidebar"] { background-color: #0F172A !important; border-right: 1px solid rgba(255,255,255,0.05) !important; }
    
    /* NAV BUTTONS */
    section[data-testid="stSidebar"] .stButton > button {
        background-color: transparent !important;
        color: #94A3B8 !important;
        border: none !important;
        text-align: left !important;
        font-weight: 600 !important;
        padding: 14px 20px !important;
        width: 100% !important;
        display: flex !important;
        justify-content: flex-start !important;
        transition: all 0.2s ease !important;
        border-radius: 4px !important;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background-color: rgba(212, 175, 55, 0.1) !important;
        background-color: rgba(255,255,255,0.05) !important;
        color: #FFFFFF !important;
    }
    
    /* METRIC CARDS */
    .metric-card {
    /* MASTER INLINE DESIGN SYSTEM - NEAR BAKERY & CO. */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Inter:wght@400;700&display=swap');
    
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Inter', sans-serif;
        background-color: #F8FAFC !important;
    }

    /* TYPOGRAPHY */
    h1, h2, h3, .brand-title { font-family: 'Outfit', sans-serif !important; color: #0F172A !important; }
    
    /* SIDEBAR CUSTOMIZATION */
    [data-testid="stSidebar"] { background-color: #0F172A !important; }
    [data-testid="stSidebar"] .stButton button {
        background-color: transparent !important;
        color: #94A3B8 !important;
        border: none !important;
        text-align: left !important;
        justify-content: flex-start !important;
        font-weight: 600 !important;
        padding-left: 15px !important;
    }
    [data-testid="stSidebar"] .stButton button:hover { color: #FFFFFF !important; background-color: rgba(255,255,255,0.05) !important; }

    /* GLOBAL COMPONENTS */
    .stButton>button { 
        border-radius: 8px !important; 
        font-weight: 700 !important; 
        transition: all 0.2s !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
    }
    
    /* INPUT FIELDS */
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
        border-radius: 8px !important;
        border: 1px solid #E2E8F0 !important;
        background: white !important;
    }

    /* LUXURY METRICS */
    [data-testid="stMetric"] {
        background: white !important;
        padding: 20px !important;
        border-radius: 16px !important;
        border: 1px solid #F1F5F9 !important;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05) !important;
    }

    /* TABS STYLING */
    .stTabs [data-baseweb="tab-list"] { gap: 10px !important; background-color: transparent !important; }
    .stTabs [data-baseweb="tab"] {
        background-color: #F1F5F9 !important;
        border-radius: 8px 8px 0 0 !important;
        padding: 10px 20px !important;
        font-weight: 700 !important;
        color: #64748B !important;
    }
    .stTabs [aria-selected="true"] { background-color: #0F172A !important; color: white !important; }

    /* FOOTER HIDE */
    footer { visibility: hidden; }
    [data-testid="stHeader"] { background: rgba(255,255,255,0.8) !important; backdrop-filter: blur(10px) !important; }
    </style>
    """, unsafe_allow_html=True)

apply_executive_ui()

# 6. SIDEBAR NAVIGATION
with st.sidebar:
    st.markdown(f"""
    <div style="padding: 20px 0; display: flex; align-items: center; gap: 15px; margin-bottom: 20px; border-bottom: 1px solid rgba(255,255,255,0.1);">
        <div style="font-family: 'Inter', sans-serif; font-size: 1.2rem; font-weight: 800; color: #FFFFFF; letter-spacing: 1px;">NEAR BAKERY <span style="font-weight: 400; color: #94A3B8;">ERP</span></div>
    </div>
    """, unsafe_allow_html=True)
    
    menu = {
        "🏠 Dashboard": "Dashboard",
        "--- OPERASIONAL ---": "SEP1",
        "🖥️ Kasir Terminal": "POS",
        "📦 Inventaris Pusat": "Inventory",
        "🍞 Resep & Produksi": "Recipe",
        "🛒 Logistik & Supplier": "Logistics",
        "🥨 Order Kustom": "CustomOrder",
        "📍 Tracking Status": "Tracking",
        "--- ANALISIS & SDM ---": "SEP2",
        "🧪 R&D Lab": "RD",
        "🗑️ Manajemen Limbah": "Waste",
        "📣 CRM & Promo": "CRM",
        "💬 Team Chat": "Chat",
        "✅ Approval Center": "Approval"
    }
    
    if st.session_state.role in ['Owner', 'OWNER']:
        menu["--- EKSEKUTIF ---"] = "SEP3"
        menu["💎 The Vault"] = "Vault"
        menu["📈 Strategi Finansial"] = "Finansial"
        menu["💰 Smart Pricing"] = "Pricing"
        menu["📊 Audit & Analisis"] = "Analisis"
        menu["🔗 Integrasi Sistem"] = "Integrasi"
        menu["🛡️ Guardian & Health"] = "Health"
        menu["⚙️ Pengaturan"] = "Settings"

    for label, page in menu.items():
        if label.startswith("---"):
            st.markdown(f"<div style='color: #64748B; font-size: 0.65rem; font-weight: 800; margin: 15px 0 5px 10px; letter-spacing: 1.5px;'>{label}</div>", unsafe_allow_html=True)
            continue
            
        if st.session_state.role not in ['Owner', 'OWNER'] and page not in st.session_state.permissions and page != "Dashboard":
            continue
            
        is_active = st.session_state.page == page
        btn_type = "secondary" # Streamlit 1.32+ support
        
        if st.button(label, use_container_width=True, key=f"nav_{page}"): 
            st.session_state.page = page
            st.rerun()
    
    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    if st.button("■ LOGOUT", use_container_width=True): 
        st.session_state.auth = False; st.session_state.user = None; st.rerun()

# 7. MAIN ROUTER
if st.session_state.page == 'Dashboard':
    st.markdown(f"""
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 35px; background: white; padding: 25px; border-radius: 24px; border: 1px solid #F1F5F9; box-shadow: 0 4px 15px rgba(0,0,0,0.02);">
        <div>
            <h1 style="margin: 0; font-size: 1.8rem; letter-spacing: -0.5px;">Dashboard</h1>
            <p style="color: #64748B; margin-top: 5px; font-weight: 500;">
                Selamat datang kembali, <span style="color: #0F172A; font-weight: 700;">{st.session_state.user}</span> 
                <span style="margin: 0 10px; color: #E2E8F0;">|</span> 
                <span style="background: rgba(212, 175, 55, 0.1); color: #D4AF37; padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: 700;">{st.session_state.role}</span>
            </p>
        </div>
        <div style="text-align: right;">
            <div style="display: flex; align-items: center; gap: 10px; justify-content: flex-end; margin-bottom: 5px;">
                <div style="width: 10px; height: 10px; background: #10B981; border-radius: 50%; box-shadow: 0 0 10px #10B981;"></div>
                <span style="font-weight: 800; font-size: 0.85rem; color: #1E293B; letter-spacing: 1px;">SYSTEM ONLINE</span>
            </div>
            <p style="color: #94A3B8; font-size: 0.75rem; font-weight: 600; margin: 0;">TERMINAL ID: NB-ERP-2024-001</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    conn = get_connection()
    
    # DUE ORDERS ALERT
    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    urgent_orders = pd.read_sql_query("SELECT customer_name, pickup_date, notes FROM custom_orders WHERE pickup_date <= ? AND status = 'PENDING' ORDER BY pickup_date ASC", conn, params=(tomorrow,))
    
    if not urgent_orders.empty:
        st.markdown(f"""
        <div style="background: #FFFBEB; border-left: 5px solid #F59E0B; padding: 20px; border-radius: 12px; margin-bottom: 25px;">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 15px;">
                <span style="font-size: 1.2rem;">&#9888;</span>
                <span style="font-weight: 800; color: #92400E; letter-spacing: 1px; text-transform: uppercase; font-size: 0.85rem;">Critical Due Date Alerts ({len(urgent_orders)} Orders)</span>
            </div>
        """, unsafe_allow_html=True)
        for idx, row in urgent_orders.iterrows():
            st.markdown(f"""
            <div style="margin-bottom: 10px; padding-bottom: 10px; border-bottom: 1px solid rgba(245, 158, 11, 0.2);">
                <div style="display: flex; justify-content: space-between;">
                    <span style="font-weight: 700; color: #1E293B;">{row['customer_name']}</span>
                    <span style="font-weight: 700; color: #B45309; font-size: 0.8rem;">{row['pickup_date']}</span>
                </div>
                <p style="margin: 5px 0 0; color: #64748B; font-size: 0.85rem;"><b>Catatan:</b> {row['notes'] if row['notes'] else '-'}</p>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # METRICS
    today_sales = conn.execute("SELECT SUM(total_revenue) FROM sales_log WHERE date(timestamp) = CURRENT_DATE").fetchone()[0] or 0
    today_orders = conn.execute("SELECT COUNT(*) FROM sales_log WHERE date(timestamp) = CURRENT_DATE").fetchone()[0] or 0
    total_prods = conn.execute("SELECT COUNT(*) FROM recipe_master").fetchone()[0] or 0
    vault_bal = conn.execute("SELECT current_balance FROM business_vault").fetchone()[0] or 0
    new_msgs = conn.execute("SELECT COUNT(*) FROM customer_messages WHERE status = 'UNREAD'").fetchone()[0] or 0
    
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.markdown(f"""
        <div class="metric-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <span style="color: #64748B; font-size: 0.75rem; font-weight: 700; text-transform: uppercase;">Sales Today</span>
                <div style="color: #10B981;">&#128181;</div>
            </div>
            <h3 style="margin:0; font-size: 1.4rem;">{format_rp(today_sales)}</h3>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
        <div class="metric-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <span style="color: #64748B; font-size: 0.75rem; font-weight: 700; text-transform: uppercase;">Live Orders</span>
                <div style="color: #3B82F6;">&#128230;</div>
            </div>
            <h3 style="margin:0; font-size: 1.4rem;">{today_orders}</h3>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
        <div class="metric-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <span style="color: #64748B; font-size: 0.75rem; font-weight: 700; text-transform: uppercase;">Inventory</span>
                <div style="color: #F59E0B;">&#128203;</div>
            </div>
            <h3 style="margin:0; font-size: 1.4rem;">{total_prods}</h3>
        </div>
        """, unsafe_allow_html=True)
    with m4:
        st.markdown(f"""
        <div class="metric-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <span style="color: #64748B; font-size: 0.75rem; font-weight: 700; text-transform: uppercase;">Vault Bal</span>
                <div style="color: #8B5CF6;">&#128142;</div>
            </div>
            <h3 style="margin:0; font-size: 1.4rem;">{format_rp(vault_bal)}</h3>
        </div>
        """, unsafe_allow_html=True)
    with m5:
        st.markdown(f"""
        <div class="metric-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <span style="color: #64748B; font-size: 0.75rem; font-weight: 700; text-transform: uppercase;">Unread Msg</span>
                <div style="color: #EF4444;">&#128233;</div>
            </div>
            <h3 style="margin:0; font-size: 1.4rem;">{new_msgs}</h3>
        </div>
        """, unsafe_allow_html=True)
    
    # --- EXECUTIVE INTELLIGENCE (CHARTS) ---
    st.write("---")
    st.markdown("### &#128200; Executive Intelligence")
    
    # 1. SALES TREND (LAST 30 DAYS)
    sales_data = pd.read_sql_query("""
        SELECT date(timestamp) as date, SUM(total_revenue) as revenue 
        FROM sales_log 
        WHERE timestamp >= CURRENT_DATE - INTERVAL '30 days'
        GROUP BY date 
        ORDER BY date ASC
    """, conn)
    
    # 2. CATEGORY DISTRIBUTION
    cat_data = pd.read_sql_query("""
        SELECT category, COUNT(*) as count FROM recipe_master GROUP BY category
    """, conn)
    
    c_chart1, c_chart2 = st.columns(2)
    with c_chart1:
        st.markdown('<div class="metric-card"><b>Sales Trend (30 Days)</b><br><br></div>', unsafe_allow_html=True)
        if not sales_data.empty:
            st.line_chart(sales_data.set_index('date'))
        else:
            st.info("Data penjualan belum tersedia untuk grafik.")
            
    with c_chart2:
        st.markdown('<div class="metric-card"><b>Product Distribution</b><br><br></div>', unsafe_allow_html=True)
        if not cat_data.empty:
            st.bar_chart(cat_data.set_index('category'))
        else:
            st.info("Data kategori belum tersedia.")
    
    conn.close()

elif st.session_state.page == 'Inventory': show_inventory()
elif st.session_state.page == 'POS': show_pos()
elif st.session_state.page == 'Recipe': show_recipes()
elif st.session_state.page == 'Waste': show_waste()
elif st.session_state.page == 'Approval': show_approval()
elif st.session_state.page == 'Finansial': show_finance()
elif st.session_state.page == 'Integrasi': show_integration()
elif st.session_state.page == 'Health': show_health_center()
elif st.session_state.page == 'Vault': show_vault()
elif st.session_state.page == 'CustomOrder': show_custom_order()
elif st.session_state.page == 'Tracking': show_tracking()
elif st.session_state.page == 'RD': show_rd()
elif st.session_state.page == 'Pricing': show_pricing_architect()
elif st.session_state.page == 'Settings': show_settings()
elif st.session_state.page == 'Analisis': show_accounting()
elif st.session_state.page == 'Logistics': show_purchase()
elif st.session_state.page == 'CRM': show_customers()
elif st.session_state.page == 'Chat': show_communication()
