import os
import re
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import streamlit as st

# --- SUPABASE CLOUD CONFIG (Secure) ---
try:
    DB_URL = st.secrets["DB_URL"]
except:
    # Local fallback
    DB_URL = "postgresql://postgres.btcsynyxodkonqdpwowx:%23Nenocahyamulan190604@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres"

# Create Engine
engine = create_engine(DB_URL, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class PostgresCursor:
    def __init__(self, parent):
        self.parent = parent
        self.description = None
        self.rowcount = -1
    
    def execute(self, query, params=None):
        self.parent.execute(query, params)
        self.description = self.parent.description
        self.rowcount = self.parent.rowcount
        return self
        
    def fetchall(self):
        return self.parent.fetchall()
        
    def fetchone(self):
        return self.parent.fetchone()
        
    def close(self):
        pass

class PostgresCompat:
    def __init__(self, conn):
        self.conn = conn
        self._last_id = None
        self._current_result = None
    
    def cursor(self):
        return PostgresCursor(self)

    def execute(self, query, params=None):
        try:
            if isinstance(query, str):
                # Clean up query
                query = query.replace("date('now')", "CURRENT_DATE")
                query = query.replace("datetime('now')", "CURRENT_TIMESTAMP")
                query = re.sub(r"date\((?!')(.*?)\)", r"\1::date", query)
                if "INSERT OR REPLACE INTO" in query:
                    query = query.replace("INSERT OR REPLACE INTO", "INSERT INTO")
                
                # Handle placeholders
                placeholders = re.findall(r'\?', query)
                for i in range(len(placeholders)):
                    query = query.replace('?', f':p{i+1}', 1)
                
                query_obj = text(query)
                if params:
                    if isinstance(params, (tuple, list)):
                        param_dict = {f'p{i+1}': val for i, val in enumerate(params)}
                        self._current_result = self.conn.execute(query_obj, param_dict)
                    else:
                        self._current_result = self.conn.execute(query_obj, params)
                else:
                    self._current_result = self.conn.execute(query_obj)
            else:
                self._current_result = self.conn.execute(query, params) if params else self.conn.execute(query)
        except Exception as e:
            try:
                self.conn.rollback()
            except:
                pass
            raise e
        
        return self

    def fetchall(self):
        return self._current_result.fetchall() if self._current_result else []

    def fetchone(self):
        if self._current_result:
            return self._current_result.fetchone()
        return None

    def scalar(self):
        if self._current_result:
            return self._current_result.scalar()
        return None

    @property
    def description(self):
        if self._current_result:
            return [(name, None, None, None, None, None, None) for name in self._current_result.keys()]
        return []

    @property
    def rowcount(self):
        return self._current_result.rowcount if self._current_result else -1

    @property
    def lastrowid(self):
        return self._last_id

    def commit(self):
        try: self.conn.commit()
        except: pass

    def rollback(self):
        try: self.conn.rollback()
        except: pass

    def close(self):
        try: self.conn.close()
        except: pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            try: self.conn.rollback()
            except: pass
        try: self.conn.close()
        except: pass

def get_connection():
    return PostgresCompat(engine.connect())

def init_db():
    """
    Initialize all tables in Supabase if they don't exist.
    """
    conn = get_connection()
    try:
        # Core Tables
        conn.execute("CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username TEXT UNIQUE, password TEXT, role TEXT, email TEXT, permissions TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS inventory_master (id SERIAL PRIMARY KEY, name TEXT, category TEXT, stock FLOAT, unit_beli TEXT, unit_pakai TEXT, price_per_unit_beli FLOAT, price_per_unit_pakai FLOAT, barcode TEXT UNIQUE, last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        conn.execute("CREATE TABLE IF NOT EXISTS recipe_master (id SERIAL PRIMARY KEY, name TEXT, barcode TEXT UNIQUE, category TEXT, yield_qty FLOAT, yield_unit TEXT, selling_price FLOAT DEFAULT 0, discount_pct FLOAT DEFAULT 0, image_path TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS recipe_ingredients (id SERIAL PRIMARY KEY, recipe_id INTEGER, inventory_id INTEGER, qty_pakai FLOAT)")
        conn.execute("CREATE TABLE IF NOT EXISTS sales_log (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, total_revenue FLOAT, total_hpp FLOAT DEFAULT 0, profit FLOAT DEFAULT 0, payment_method TEXT, customer_id INTEGER)")
        conn.execute("CREATE TABLE IF NOT EXISTS sales_items (id SERIAL PRIMARY KEY, sales_id INTEGER, product_name TEXT, qty INTEGER, price FLOAT)")
        conn.execute("CREATE TABLE IF NOT EXISTS finance_config (config_key TEXT PRIMARY KEY, config_value FLOAT)")
        conn.execute("CREATE TABLE IF NOT EXISTS pending_approvals (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, user_requester TEXT, action_type TEXT, description TEXT, data_payload TEXT, reason TEXT, status TEXT DEFAULT 'PENDING')")
        conn.execute("CREATE TABLE IF NOT EXISTS business_vault (id SERIAL PRIMARY KEY, current_balance FLOAT DEFAULT 0, last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        conn.execute("CREATE TABLE IF NOT EXISTS vault_ledger (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, amount FLOAT, type TEXT, source TEXT, description TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS audit_logs (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, user_actor TEXT, action TEXT, table_name TEXT, old_value TEXT, new_value TEXT, reason TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS customer_messages (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, customer_name TEXT, message TEXT, status TEXT DEFAULT 'UNREAD')")
        conn.execute("CREATE TABLE IF NOT EXISTS internal_messages (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, sender TEXT, message TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS system_settings (config_key TEXT PRIMARY KEY, config_value FLOAT)")
        
        # Operational Tables
        conn.execute("CREATE TABLE IF NOT EXISTS stock_movement_log (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, inventory_id INTEGER, qty FLOAT, type TEXT, reason TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS packaging_bundles (id SERIAL PRIMARY KEY, name TEXT UNIQUE)")
        conn.execute("CREATE TABLE IF NOT EXISTS packaging_bundle_items (id SERIAL PRIMARY KEY, bundle_id INTEGER, inventory_id INTEGER, qty FLOAT)")
        conn.execute("CREATE TABLE IF NOT EXISTS category_packaging_map (category_name TEXT PRIMARY KEY, bundle_id INTEGER)")
        conn.execute("CREATE TABLE IF NOT EXISTS custom_orders (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, customer_name TEXT, phone TEXT, order_details TEXT, pickup_date DATE, total_price FLOAT, down_payment FLOAT, status TEXT DEFAULT 'PENDING')")
        conn.execute("CREATE TABLE IF NOT EXISTS system_health_log (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, issue_type TEXT, severity TEXT, description TEXT, status TEXT DEFAULT 'OPEN')")
        
        # Financial & Waste Tables
        conn.execute("CREATE TABLE IF NOT EXISTS waste_log (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, inventory_id INTEGER, qty_waste FLOAT, loss_value FLOAT, reason TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS asset_waste_log (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, asset_name TEXT, loss_value FLOAT, reason TEXT, image_path TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS budget_usage_log (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, room_name TEXT, amount FLOAT, description TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS budget_allocation (room_name TEXT PRIMARY KEY, target_pct FLOAT)")
        
        # Procurement & R&D
        conn.execute("CREATE TABLE IF NOT EXISTS suppliers (id SERIAL PRIMARY KEY, name TEXT, contact_person TEXT, phone TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS purchase_order_log (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, inventory_id INTEGER, supplier_id INTEGER, qty_order FLOAT, unit_order TEXT, price_total FLOAT, status TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS rd_trials (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, name TEXT, total_cost FLOAT)")
        conn.execute("CREATE TABLE IF NOT EXISTS rd_trial_ingredients (id SERIAL PRIMARY KEY, trial_id INTEGER, inventory_id INTEGER, qty_pakai FLOAT)")
        conn.execute("CREATE TABLE IF NOT EXISTS product_addons (id SERIAL PRIMARY KEY, name TEXT, price FLOAT, inventory_id INTEGER, qty_deduct FLOAT)")
        
        # --- MIGRATIONS (Add missing columns to existing tables) ---
        try:
            # recipe_master migrations
            conn.execute("ALTER TABLE recipe_master ADD COLUMN IF NOT EXISTS selling_price FLOAT DEFAULT 0")
            conn.execute("ALTER TABLE recipe_master ADD COLUMN IF NOT EXISTS discount_pct FLOAT DEFAULT 0")
            conn.execute("ALTER TABLE recipe_master ADD COLUMN IF NOT EXISTS image_path TEXT")
            
            # inventory_master migrations
            conn.execute("ALTER TABLE inventory_master ADD COLUMN IF NOT EXISTS price_per_unit_beli FLOAT DEFAULT 0")
            conn.execute("ALTER TABLE inventory_master ADD COLUMN IF NOT EXISTS last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            
            # sales_log migrations
            conn.execute("ALTER TABLE sales_log ADD COLUMN IF NOT EXISTS total_hpp FLOAT DEFAULT 0")
            conn.execute("ALTER TABLE sales_log ADD COLUMN IF NOT EXISTS profit FLOAT DEFAULT 0")
            conn.execute("ALTER TABLE sales_log ADD COLUMN IF NOT EXISTS payment_method TEXT")
            
            # asset_waste_log migrations
            conn.execute("ALTER TABLE asset_waste_log ADD COLUMN IF NOT EXISTS image_path TEXT")
            
            # business_vault migrations
            conn.execute("ALTER TABLE business_vault ADD COLUMN IF NOT EXISTS last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            
            # recipe_ingredients migrations
            conn.execute("ALTER TABLE recipe_ingredients ADD COLUMN IF NOT EXISTS unit TEXT")
            
            # custom_orders migrations
            conn.execute("ALTER TABLE custom_orders ADD COLUMN IF NOT EXISTS notes TEXT")
        except:
            pass # Ignore if columns already exist or other migration issues

        # --- SEED INITIAL DATA ---
        res = conn.execute("SELECT COUNT(*) FROM users WHERE username='admin'").scalar()
        if res == 0:
            conn.execute("INSERT INTO users (username, password, role) VALUES ('admin', 'admin123', 'OWNER')")
        
        res_fc = conn.execute("SELECT COUNT(*) FROM finance_config").scalar()
        if res_fc == 0:
            conn.execute("INSERT INTO finance_config (config_key, config_value) VALUES ('global_margin_pct', 100)")
            conn.execute("INSERT INTO finance_config (config_key, config_value) VALUES ('cogs_buffer_pct', 5)")

        res_ss = conn.execute("SELECT COUNT(*) FROM system_settings").scalar()
        if res_ss == 0:
            conn.execute("INSERT INTO system_settings (config_key, config_value) VALUES ('comm_grab', 20)")
            conn.execute("INSERT INTO system_settings (config_key, config_value) VALUES ('comm_gofood', 20)")
            conn.execute("INSERT INTO system_settings (config_key, config_value) VALUES ('comm_shopee', 20)")
            conn.execute("INSERT INTO system_settings (config_key, config_value) VALUES ('tax_pct', 10)")

        res_bv = conn.execute("SELECT COUNT(*) FROM business_vault").scalar()
        if res_bv == 0:
            conn.execute("INSERT INTO business_vault (current_balance) VALUES (0)")

        # Update vault balance for sample look
        # conn.execute("UPDATE business_vault SET current_balance = 5000000 WHERE current_balance = 0")

        conn.commit()
    except Exception as e:
        print(f"Error initializing database: {e}")
        try: conn.rollback()
        except: pass
    finally:
        try: conn.close()
        except: pass

# Auto-init on import
if "db_initialized" not in st.session_state:
    init_db()
    st.session_state.db_initialized = True
