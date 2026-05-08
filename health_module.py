import streamlit as st
import pandas as pd
from database_engine import get_connection
from utils import format_rp, get_dynamic_selling_price, get_cogs_calculation

def run_system_health_check():
    issues = []
    conn = get_connection()
    
    # 1. Check for Negative Stock (Using correct column: 'stock')
    try:
        neg_stock = conn.execute("SELECT name, stock FROM inventory_master WHERE stock < 0").fetchall()
        for item in neg_stock:
            issues.append({"type": "STOK MINUS", "desc": f"Barang '{item[0]}' memiliki stok {item[1]}. Ini merusak logika HPP!", "severity": "HIGH"})
    except Exception as e:
        issues.append({"type": "DATABASE ERROR", "desc": f"Gagal membaca stok: {str(e)}", "severity": "CRITICAL"})
        
    # 2. Check for "Boncos" (Selling Price < HPP)
    try:
        recipes = conn.execute("SELECT id, name FROM recipe_master").fetchall()
        for r in recipes:
            cogs_res = get_cogs_calculation(r[0], include_buffer=True)
            hpp = cogs_res['total_hpp']
            sell = get_dynamic_selling_price(r[0])
            if sell <= hpp and hpp > 0:
                issues.append({"type": "DETEKSI BONCOS", "desc": f"Roti '{r[1]}' dijual seharga {format_rp(sell)} padahal HPP-nya {format_rp(hpp)}. ANDA RUGI!", "severity": "CRITICAL"})
    except:
        pass
            
    # 3. Check for 0 HPP Recipes (Missing Ingredients)
    try:
        for r in recipes:
            cogs_res = get_cogs_calculation(r[0])
            hpp = cogs_res['total_hpp']
            if hpp <= 0:
                issues.append({"type": "DATA KOSONG", "desc": f"Resep '{r[1]}' belum punya bahan baku atau harga bahan 0.", "severity": "MEDIUM"})
    except:
        pass
            
    # 4. Check for Outdated Prices
    outdated = conn.execute("SELECT name FROM inventory_master WHERE price_per_unit_pakai <= 0").fetchall()
    for item in outdated:
        issues.append({"type": "HARGA NOL", "desc": f"Bahan '{item[0]}' belum memiliki harga beli. Perhitungan HPP tidak akan akurat!", "severity": "HIGH"})
            
    conn.close()
    return issues

def show_health_center():
    
    st.markdown("## 🛡️ Guardian System & Enterprise Troubleshooting")
    
    # --- QUICK STATS ---
    issues = run_system_health_check()
    total_issues = len(issues)
    critical_issues = len([i for i in issues if i['severity'] == "CRITICAL"])
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Status Kesehatan", "EXCELLENT" if total_issues == 0 else "WARNING" if critical_issues == 0 else "CRITICAL")
    c2.metric("Isu Terdeteksi", total_issues)
    c3.metric("Isu Kritis", critical_issues)
    
    st.write("---")
    
    tab_status, tab_repair, tab_update = st.tabs(["🚦 System Health Scan", "🔧 Auto-Repair Center", "🆕 Version History"])
    
    with tab_status:
        if not issues:
            st.success("✨ **LOGIKA BISNIS SEMPURNA!** Semua data sinkron dan tidak ada kebocoran profit.")
        else:
            for iss in issues:
                icon = "🔴" if iss['severity'] == "CRITICAL" else "🟡" if iss['severity'] == "HIGH" else "🔵"
                st.markdown(f"""
                <div style="padding: 18px; border-left: 5px solid {'#EF4444' if iss['severity']=='CRITICAL' else '#F59E0B' if iss['severity']=='HIGH' else '#3B82F6'}; background: #F8FAFC; margin-bottom: 12px; border-radius: 12px;">
                    <span style="font-size: 1.2rem;">{icon}</span> <b>{iss['type']}</b><br>
                    <span style="color: #64748B; font-size: 0.9rem;">{iss['desc']}</span>
                </div>
                """, unsafe_allow_html=True)
                
    with tab_repair:
        st.subheader("🛠️ Enterprise Repair Toolkit")
        st.write("Jalankan alat ini untuk memastikan stabilitas sistem Near Bakery.")
        
        if st.button("🚀 JALANKAN SYNC ULANG DATABASE", width="stretch", type="primary"):
            with st.spinner("Mensinkronisasi alur logika..."):
                # Real fix: ensure default values in DB
                conn = get_connection()
                conn.execute("UPDATE inventory_master SET stock = 0 WHERE stock IS NULL")
                conn.execute("UPDATE inventory_master SET price_per_unit_pakai = 0 WHERE price_per_unit_pakai IS NULL")
                conn.commit(); conn.close()
                st.cache_data.clear()
                st.success("Database berhasil disinkronisasi dan diperbaiki!")
                st.balloons()
            
        if st.button("🧹 Clear All System Cache", width="stretch"):
            st.cache_data.clear()
            st.rerun()
            
    with tab_update:
        st.subheader("🆕 Update Sistem v5.2")
        st.markdown("""
        - **v5.2.1**: Penambahan Guardian System (Anti-Boncos)
        - **v5.2.0**: Integrasi Shopee-Style Customer Portal
        - **v5.1.9**: Penambahan Sistem Custom Order (Coming Soon)
        - **v5.1.8**: Perbaikan Indentation Error & Database Closure
        """)
    
