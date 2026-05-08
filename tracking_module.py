import streamlit as st
import pandas as pd
from database_engine import get_connection
from utils import render_luxury_table, format_rp

def show_tracking():
    
    st.markdown("## 🔍 Quantum Tracking Center")
    st.info("Lacak riwayat hidup dan alur logika setiap item di Near Bakery.")
    
    # 1. SEARCH INPUT
    search_query = st.text_input("Ketik ID Unik atau Nama Barang", placeholder="Contoh: NB-A7X9 atau Tepung Terigu")
    
    if search_query:
        conn = get_connection()
        # Find item first
        item = conn.execute("SELECT id, name, category FROM inventory_master WHERE id LIKE ? OR name LIKE ?", 
                            (f"%{search_query}%", f"%{search_query}%")).fetchone()
        
        if not item:
            # Check finished goods (recipes)
            item = conn.execute("SELECT id, name, category FROM recipe_master WHERE id LIKE ? OR name LIKE ?", 
                                (f"%{search_query}%", f"%{search_query}%")).fetchone()
            is_raw = False
        else:
            is_raw = True
            
        if item:
            item_id, item_name, item_cat = item
            st.markdown(f"### 📦 Pelacakan: {item_name} ({item_id})")
            st.write(f"Kategori: {item_cat}")
            
            # --- THE TIMELINE/JOURNEY ---
            st.subheader("📜 Riwayat Alur Logika")
            journey = []
            
            if is_raw:
                # 1. Purchase/Inbound
                po_data = pd.read_sql_query("SELECT timestamp, 'PENGADAAN' as aksi, 'Masuk via PO' as info FROM purchase_order_log WHERE item_name = ?", conn, params=(item_name,))
                # 2. Waste
                waste_data = pd.read_sql_query("SELECT timestamp, 'WASTE/LOSS' as aksi, reason as info FROM waste_log WHERE inventory_id = ?", conn, params=(item_id,))
                # 3. Usage in Recipes
                usage_data = pd.read_sql_query("""
                    SELECT ri.qty_pakai, rm.name as recipe_name, 'DIPAKAI PRODUKSI' as aksi 
                    FROM recipe_ingredients ri 
                    JOIN recipe_master rm ON ri.recipe_id = rm.id 
                    WHERE ri.inventory_id = ?
                """, conn, params=(item_id,))
                
                # Combine and format
                if not po_data.empty: journey.append(po_data)
                if not waste_data.empty: journey.append(waste_data)
            else:
                # For finished goods (recipes)
                # 1. Sales
                sales_data = pd.read_sql_query("SELECT timestamp, 'PENJUALAN' as aksi, 'Terjual di POS' as info FROM sales_log", conn) # This needs deep mapping in real app
                if not sales_data.empty: journey.append(sales_data)

            # Displaying the combined journey
            st.markdown(render_luxury_table(pd.concat(journey) if journey else pd.DataFrame(columns=['timestamp','aksi','info'])), unsafe_allow_html=True)
        else:
            st.warning("Barang tidak ditemukan. Pastikan ID atau Nama benar.")
        conn.close()
    else:
        st.write("Silakan masukkan kata kunci untuk memulai pelacakan.")
    
    

def generate_unique_id(prefix="NB"):
    import random, string
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{prefix}-{suffix}"
