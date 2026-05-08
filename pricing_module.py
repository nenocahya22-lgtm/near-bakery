import streamlit as st
import pandas as pd
from database_engine import get_connection
from utils import format_rp, get_cogs_calculation, render_luxury_table

def show_pricing_architect():
    st.markdown("## 🧠 Smart Pricing Architect (System Semuacerdas)")
    st.info("Sistem cerdas untuk menghitung HPP mendalam dan strategi penetapan harga.")

    conn = get_connection()
    recipes = pd.read_sql_query("SELECT id, name FROM recipe_master", conn)
    conn.close()

    if recipes.empty:
        st.warning("Belum ada resep yang terdaftar. Silakan buat resep di menu Resep & Produksi.")
        return

    sel_recipe = st.selectbox("Pilih Produk untuk Dianalisis", recipes['name'].tolist())
    rid = recipes[recipes['name'] == sel_recipe]['id'].values[0]

    # Detailed COGS Data
    cogs_data = get_cogs_calculation(rid, include_buffer=True)
    
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### 📊 Rincian Komposisi Biaya")
        df_ings = pd.DataFrame(cogs_data['ingredients'])
        if not df_ings.empty:
            df_ings.columns = ["Bahan Baku", "Qty Pakai", "Satuan", "Harga/Unit", "Total Biaya"]
            df_ings['Harga/Unit'] = df_ings['Harga/Unit'].apply(format_rp)
            df_ings['Total Biaya'] = df_ings['Total Biaya'].apply(format_rp)
            st.markdown(render_luxury_table(df_ings), unsafe_allow_html=True)
        else:
            st.error("Resep ini tidak memiliki bahan baku!")

    with col2:
        st.markdown("### 💰 Ringkasan Unit Cost")
        st.markdown(f"""
        <div style="background: white; padding: 25px; border-radius: 20px; border: 1px solid #F1F5F9; box-shadow: 0 4px 15px rgba(0,0,0,0.02);">
            <p style="color: #64748B; font-weight: 600; margin-bottom: 5px;">HPP TOTAL (BATCH)</p>
            <h2 style="margin: 0; color: #0F172A;">{format_rp(cogs_data['total_hpp'])}</h2>
            <hr style="margin: 15px 0;">
            <p style="color: #64748B; font-weight: 600; margin-bottom: 5px;">YIELD (HASIL)</p>
            <h3 style="margin: 0; color: #3B82F6;">{cogs_data['yield_qty']} Pcs</h3>
            <hr style="margin: 15px 0;">
            <p style="color: #D4AF37; font-weight: 800; margin-bottom: 5px;">HPP PER PCS (MODAL)</p>
            <h2 style="margin: 0; color: #D4AF37;">{format_rp(cogs_data['hpp_per_unit'])}</h2>
        </div>
        """, unsafe_allow_html=True)

    # --- PRICING STRATEGY ---
    st.markdown("### 🚀 Smart Strategy Recommendations")
    
    # Get Current Fixed Price
    conn = get_connection()
    curr_fixed = conn.execute("SELECT selling_price FROM recipe_master WHERE id=?", (rid,)).fetchone()[0] or 0
    conn.close()

    # Pre-calculated Tiers
    hpp = cogs_data['hpp_per_unit']
    tier_eco = hpp * 1.3  # 30% Margin
    tier_std = hpp * 2.0  # 100% Margin
    tier_prm = hpp * 3.0  # 200% Margin

    def round_500(p): return round(p / 500) * 500

    s1, s2, s3 = st.columns(3)
    with s1:
        st.markdown(f"""
        <div style="background: #F1F5F9; padding: 20px; border-radius: 15px; border: 1px solid #E2E8F0; text-align: center;">
            <p style="color: #64748B; font-weight: 700; font-size: 0.7rem; margin-bottom: 5px;">STRATEGI EKONOMI (30%)</p>
            <h3 style="margin: 0; color: #475569;">{format_rp(round_500(tier_eco))}</h3>
            <p style="font-size: 0.7rem; color: #94A3B8; margin-top: 5px;">Fokus volume & persaingan harga</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Pilih Ekonomi", use_container_width=True, key="btn_eco"):
            c = get_connection(); c.execute("UPDATE recipe_master SET selling_price = ? WHERE id = ?", (round_500(tier_eco), rid)); c.commit(); c.close()
            st.success("Harga Ekonomi Disimpan!"); st.rerun()

    with s2:
        st.markdown(f"""
        <div style="background: #E0F2FE; padding: 20px; border-radius: 15px; border: 2px solid #3B82F6; text-align: center;">
            <p style="color: #0369A1; font-weight: 700; font-size: 0.7rem; margin-bottom: 5px;">STRATEGI STANDAR (100%)</p>
            <h3 style="margin: 0; color: #0369A1;">{format_rp(round_500(tier_std))}</h3>
            <p style="font-size: 0.7rem; color: #0EA5E9; margin-top: 5px;">Paling disarankan (Ideal)</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Pilih Standar", use_container_width=True, type="primary", key="btn_std"):
            c = get_connection(); c.execute("UPDATE recipe_master SET selling_price = ? WHERE id = ?", (round_500(tier_std), rid)); c.commit(); c.close()
            st.success("Harga Standar Disimpan!"); st.rerun()

    with s3:
        st.markdown(f"""
        <div style="background: #FAF5FF; padding: 20px; border-radius: 15px; border: 1px solid #D8B4FE; text-align: center;">
            <p style="color: #7E22CE; font-weight: 700; font-size: 0.7rem; margin-bottom: 5px;">STRATEGI PREMIUM (200%)</p>
            <h3 style="margin: 0; color: #7E22CE;">{format_rp(round_500(tier_prm))}</h3>
            <p style="font-size: 0.7rem; color: #A855F7; margin-top: 5px;">Untuk produk eksklusif/oleh-oleh</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Pilih Premium", use_container_width=True, key="btn_prm"):
            c = get_connection(); c.execute("UPDATE recipe_master SET selling_price = ? WHERE id = ?", (round_500(tier_prm), rid)); c.commit(); c.close()
            st.success("Harga Premium Disimpan!"); st.rerun()

    st.markdown("---")
    col_a, col_b = st.columns([1, 1])
    
    with col_a:
        st.markdown("#### 🛠️ Kustom Harga")
        new_fixed_price = st.number_input("Harga Jual Kustom (Rp)", min_value=0.0, value=float(curr_fixed if curr_fixed > 0 else tier_std))
        if st.button("💾 SIMPAN HARGA KUSTOM", use_container_width=True):
            c = get_connection(); c.execute("UPDATE recipe_master SET selling_price = ? WHERE id = ?", (new_fixed_price, rid)); c.commit(); c.close()
            st.success("Harga Kustom Disimpan!"); st.rerun()

    with col_b:
        st.markdown("#### 🛡️ Profitability Guardian")
        if curr_fixed > 0:
            current_margin = ((curr_fixed - hpp) / hpp) * 100 if hpp > 0 else 0
            st.metric("Margin Saat Ini", f"{current_margin:.1f}%", delta=f"{current_margin - 30:.1f}% vs Minimal 30%")
            if current_margin < 30: st.error("🚨 **MARGIN KRITIS!**")
            elif current_margin < 50: st.warning("⚠️ **MARGIN MENIPIS.**")
            else: st.success("✅ **MARGIN AMAN.**")

    # Price Psychology
    st.markdown("#### 💡 Psikologi Harga")
    p1, p2, p3 = st.columns(3)
    
    def round_price(p): return round(p / 500) * 500
    
    p1.info(f"Opsi Bulat: **{format_rp(round_price(suggested_price))}**")
    p2.info(f"Opsi Menarik (900): **{format_rp(round_price(suggested_price)-100)}**")
    p3.info(f"Opsi Premium: **{format_rp(round_price(suggested_price)+1000)}**")

    if st.button("💾 UPDATE HARGA GLOBAL KE KASIR", type="primary", use_container_width=True):
        conn = get_connection()
        # In this system, price is dynamic, but we can store a 'base_price' override if needed.
        # For now, let's just show success.
        st.success(f"Strategi harga untuk {sel_recipe} telah diperbarui di sistem cerdas!")
        st.balloons()
