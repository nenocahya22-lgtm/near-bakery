import streamlit as st
from database_engine import get_connection

def format_rp(value):
    return f"Rp {value:,.0f}"

def get_cogs_buffer_pct():
    conn = get_connection()
    res = conn.execute("SELECT config_value FROM finance_config WHERE config_key = 'cogs_buffer_pct'").fetchone()
    conn.close()
    return res[0] if res else 0

def convert_qty(qty, from_unit, to_unit):
    if not from_unit or not to_unit: return qty
    u1 = from_unit.lower()
    u2 = to_unit.lower()
    if u1 == u2: return qty
    
    # Weight
    if "kg" in u1 and ("gram" in u2 or "gr" in u2): return qty * 1000
    if ("gram" in u1 or "gr" in u1) and "kg" in u2: return qty / 1000
    
    # Volume
    if ("liter" in u1 or " l" in u1) and ("ml" in u2 or "mililiter" in u2): return qty * 1000
    if ("ml" in u1 or "mililiter" in u1) and ("liter" in u2 or " l" in u2): return qty / 1000
    
    return qty

def get_cogs_calculation(recipe_id, include_buffer=False):
    conn = get_connection()
    # Get Yield Info
    res_y = conn.execute("SELECT yield_qty FROM recipe_master WHERE id=?", (recipe_id,)).fetchone()
    y_qty = res_y[0] if res_y else 1.0
    
    query = """
        SELECT inv.name, ri.qty_pakai, ri.unit as recipe_unit, inv.unit_pakai as inv_unit, inv.price_per_unit_pakai 
        FROM recipe_ingredients ri
        JOIN inventory_master inv ON ri.inventory_id = inv.id
        WHERE ri.recipe_id = ?
    """
    ings = conn.execute(query, (recipe_id,)).fetchall()
    conn.close()
    
    breakdown = []
    total_hpp = 0
    for name, r_qty, r_unit, i_unit, i_price in ings:
        # Convert Recipe Qty to Inventory Unit Qty
        converted_qty = convert_qty(r_qty, r_unit, i_unit)
        cost = converted_qty * i_price
        total_hpp += cost
        breakdown.append({
            "name": name,
            "qty": r_qty,
            "unit": r_unit,
            "unit_price_base": i_price,
            "total_cost": cost
        })
    
    actual_total = total_hpp
    if include_buffer:
        buffer_pct = get_cogs_buffer_pct()
        actual_total = total_hpp * (1 + buffer_pct / 100)
    
    return {
        "total_hpp": actual_total,
        "ingredients": breakdown,
        "hpp_per_unit": actual_total / y_qty if y_qty > 0 else 0,
        "yield_qty": y_qty
    }

def get_dynamic_selling_price(recipe_id):
    conn = get_connection()
    res_y = conn.execute("SELECT yield_qty FROM recipe_master WHERE id=?", (recipe_id,)).fetchone()
    res_m = conn.execute("SELECT config_value FROM finance_config WHERE config_key='global_margin_pct'").fetchone()
    conn.close()
    
    y_qty = res_y[0] if res_y else 1.0
    margin = res_m[0] if res_m else 100.0
    
    cogs_data = get_cogs_calculation(recipe_id, include_buffer=True)
    hpp_unit = cogs_data['hpp_per_unit']
    return hpp_unit * (1 + margin/100)

UNITS_MASTER = ["Kilogram (Kg)", "Gram (gr)", "Liter (L)", "Mililiter (ml)", "Pcs", "Karung", "Karton", "Botol", "Pack", "Butir", "Ikat", "Sdm", "Sdt", "Slice", "Bungkus"]
CATEGORIES_MASTER = ["BAKERY", "DRINK"]

def render_luxury_table(df):
    if df.empty:
        return "<div style='text-align: center; padding: 40px; color: #94A3B8; background: white; border-radius: 12px; border: 1px dashed #E2E8F0;'>No data available in this section.</div>"
    
    headers = [str(col).replace("_", " ").upper() for col in df.columns]
    
    html = f"""
    <div style="overflow-x: auto; border: 1px solid #E2E8F0; border-radius: 8px; background: white; margin: 15px 0;">
        <table style="width: 100%; border-collapse: collapse; font-family: 'Inter', sans-serif;">
            <thead>
                <tr style="background-color: #F8FAFC; border-bottom: 1px solid #E2E8F0;">
    """
    for col in headers:
        html += f"<th style='padding: 12px 15px; text-align: left; color: #64748B; font-weight: 600; font-size: 11px; text-transform: uppercase; letter-spacing: 0.02em;'>{col}</th>"
    
    html += "</tr></thead><tbody>"
    
    for i, row in df.iterrows():
        html += "<tr style='border-bottom: 1px solid #F1F5F9;'>"
        for col_name, val in zip(df.columns, row):
            display_val = val
            cell_style = "padding: 10px 15px; color: #334155; font-size: 13px;"
            
            # Professional Status Indicators
            val_str = str(val).upper()
            if val_str in ['LUNAS', 'PAID', 'COMPLETED', 'SUCCESS', 'ACTIVE', 'DONE']:
                display_val = f"<span style='color: #059669; font-weight: 600;'>● {val}</span>"
            elif val_str in ['PENDING', 'WAITING', 'IN PROGRESS', 'DRAFT']:
                display_val = f"<span style='color: #D97706; font-weight: 600;'>● {val}</span>"
            elif val_str in ['OVERDUE', 'FAILED', 'CRITICAL', 'CANCELLED', 'VOID']:
                display_val = f"<span style='color: #DC2626; font-weight: 600;'>● {val}</span>"
            elif isinstance(val, (int, float)) and val > 1000 and "QTY" not in str(col_name).upper() and "ID" not in str(col_name).upper():
                display_val = format_rp(val)
                cell_style += " color: #0F172A; font-weight: 500;"

            html += f"<td style='{cell_style}'>{display_val}</td>"
        html += "</tr>"
    
    html += "</tbody></table></div>"
    return html
