import streamlit as st
import pandas as pd
from database_engine import get_connection
from utils import format_rp, get_dynamic_selling_price, get_cogs_calculation

def show_customers():
    
    st.markdown("## 🎯 Pusat Promo & Proteksi Laba")
    st.info("Simulasikan dan aktifkan diskon produk Anda di sini.")

    # --- SIMULATOR DISKON ---
    st.markdown("### 📊 Simulator & Aktivasi Diskon")
    
    conn = get_connection()
    conn.execute("ALTER TABLE recipe_master ADD COLUMN IF NOT EXISTS discount_pct INTEGER DEFAULT 0")
    
    products = pd.read_sql_query("SELECT id, name, category, discount_pct FROM recipe_master", conn)
    conn.close()

    if not products.empty:
        col1, col2 = st.columns([1, 1])
        with col1:
            sel_product = st.selectbox("Pilih Produk untuk Promo", products['name'].tolist())
            p_row = products[products['name'] == sel_product].iloc[0]
            pid = int(p_row['id'])
            
            # Default value is current discount
            current_disc = int(p_row['discount_pct'])
            disc_pct = st.slider("Persentase Diskon Baru (%)", 0, 100, current_disc)
            
            if st.button("🚀 AKTIFKAN PROMO SEKARANG", use_container_width=True):
                c = get_connection()
                c.execute("UPDATE recipe_master SET discount_pct = ? WHERE id = ?", (disc_pct, pid))
                c.commit(); c.close()
                st.success(f"PROMO AKTIF! {sel_product} diskon {disc_pct}%")
                st.rerun()
        
        # --- CALCULATION LOGIC ---
        normal_price = get_dynamic_selling_price(pid)
        cogs_data = get_cogs_calculation(pid)
        total_hpp = cogs_data['total_hpp']
        
        disc_amount = normal_price * (disc_pct / 100)
        final_price = normal_price - disc_amount
        net_profit = final_price - total_hpp
        
        with col2:
            st.markdown("#### 💹 Analisis Keuangan Promo")
            if final_price < total_hpp:
                st.error(f"❌ **ALERTA MERAH: RUGI!**")
                st.markdown(f"""
                <div style='background: #dc3545; color: white; padding: 20px; border-radius: 15px; margin-bottom: 10px;'>
                    <b>STATUS: BAHAYA</b><br>
                    Diskon {disc_pct}% menghancurkan profit.<br>
                    Rugi per Pcs: {format_rp(abs(net_profit))}
                </div>
                """, unsafe_allow_html=True)
            elif final_price < (total_hpp * 1.1): # Margin di bawah 10%
                st.warning(f"⚠️ **STATUS: KRITIS (Margin < 10%)**")
                st.info(f"Untung sangat tipis: {format_rp(net_profit)}")
            else:
                st.success(f"✅ **STATUS: AMAN & PROFIT**")
                st.write(f"Harga Jual Akhir: **{format_rp(final_price)}**")
                st.write(f"Untung Bersih: **{format_rp(net_profit)}**")

        # --- FINANCIAL BREAKDOWN TABLE ---
        st.markdown("---")
        st.markdown("#### 📜 Rincian Aliran Dana (Per Transaksi)")
        breakdown_data = [
            ["Harga Normal", format_rp(normal_price)],
            [f"Potongan Diskon ({disc_pct}%)", f"-{format_rp(disc_amount)}"],
            ["HARGA JUAL AKHIR (Inflow Khazanah)", format_rp(final_price)],
            ["Biaya Bahan Baku (HPP)", f"-{format_rp(total_hpp)}"],
            ["KEUNTUNGAN BERSIH (Net Profit)", format_rp(net_profit)]
        ]
        st.table(pd.DataFrame(breakdown_data, columns=["Keterangan", "Nilai"]))
        
        # --- ACTIVE PROMOS LIST ---
        st.write("---")
        st.markdown("### 📢 Daftar Promo Aktif Saat Ini")
        active_promos = products[products['discount_pct'] > 0]
        if not active_promos.empty:
            st.dataframe(active_promos[['name', 'category', 'discount_pct']], use_container_width=True, hide_index=True)
            if st.button("🛑 MATIKAN SEMUA PROMO"):
                c = get_connection(); c.execute("UPDATE recipe_master SET discount_pct = 0"); c.commit(); c.close()
                st.success("Semua promo dihentikan!"); st.rerun()
        else:
            st.info("Tidak ada promo aktif saat ini.")
            
    else:
        st.info("Belum ada produk yang terdaftar di database.")

    
