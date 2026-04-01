import psycopg2
import os
from dotenv import load_dotenv

# 加载 .env 环境变量
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:123456@localhost:5432/supply_chain_agent")

def upgrade_db():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()
    
    try:
        cur.execute("ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS email VARCHAR;")
        cur.execute("ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS level VARCHAR DEFAULT 'general';")
        cur.execute("ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'approved';")
        cur.execute("ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id);")
        cur.execute("ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS rating_score DOUBLE PRECISION DEFAULT 0.0;")
        cur.execute("ALTER TABLE inquiry_requests ADD COLUMN IF NOT EXISTS target_price DOUBLE PRECISION;")
        cur.execute("ALTER TABLE inquiry_tasks ADD COLUMN IF NOT EXISTS strategy_config JSON;")
        cur.execute("ALTER TABLE inquiry_tasks ADD COLUMN IF NOT EXISTS deadline TIMESTAMP;")
        cur.execute("ALTER TABLE inquiry_suppliers ADD COLUMN IF NOT EXISTS latest_ai_feedback TEXT;")
        cur.execute("ALTER TABLE contracts ADD COLUMN IF NOT EXISTS total_amount DOUBLE PRECISION;")
        cur.execute("ALTER TABLE contracts ADD COLUMN IF NOT EXISTS buyer_company_name VARCHAR;")
        cur.execute("ALTER TABLE contracts ADD COLUMN IF NOT EXISTS history_versions JSON;")
        cur.execute("ALTER TABLE contracts ADD COLUMN IF NOT EXISTS address VARCHAR;")
        cur.execute("ALTER TABLE contracts ADD COLUMN IF NOT EXISTS legal_representative VARCHAR;")
        cur.execute("ALTER TABLE contracts ADD COLUMN IF NOT EXISTS agent VARCHAR;")
        cur.execute("ALTER TABLE contracts ADD COLUMN IF NOT EXISTS contact_phone VARCHAR;")
        cur.execute("ALTER TABLE contracts ADD COLUMN IF NOT EXISTS bank_name VARCHAR;")
        cur.execute("ALTER TABLE contracts ADD COLUMN IF NOT EXISTS bank_account VARCHAR;")
        cur.execute("ALTER TABLE contracts ADD COLUMN IF NOT EXISTS tax_id VARCHAR;")
        cur.execute("ALTER TABLE contracts ADD COLUMN IF NOT EXISTS fax VARCHAR;")
        cur.execute("ALTER TABLE contracts ADD COLUMN IF NOT EXISTS postal_code VARCHAR;")
        cur.execute("ALTER TABLE contracts ALTER COLUMN pdf_path DROP NOT NULL;")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS contract_templates (
                id SERIAL PRIMARY KEY,
                name VARCHAR NOT NULL UNIQUE,
                file_path VARCHAR NOT NULL,
                default_buyer_name VARCHAR,
                is_active BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );
        """)
        cur.execute("""
            INSERT INTO contracts (
                task_id, inquiry_supplier_id, pdf_path, status, created_at, updated_at,
                address, legal_representative, agent, contact_phone, bank_name, bank_account, tax_id, fax, postal_code
            )
            SELECT
                l.task_id,
                l.id,
                NULLIF(COALESCE(l.contract_pdf_path, l.contract_pdf, ''), ''),
                'generated',
                NOW(),
                NOW(),
                l.address,
                l.legal_rep,
                l.agent,
                l.phone,
                l.bank_name,
                l.bank_account,
                l.tax_id,
                l.fax,
                l.postal_code
            FROM inquiry_suppliers l
            WHERE (
                l.contract_pdf IS NOT NULL OR l.contract_pdf_path IS NOT NULL
                OR l.address IS NOT NULL OR l.legal_rep IS NOT NULL OR l.agent IS NOT NULL
                OR l.phone IS NOT NULL OR l.bank_name IS NOT NULL OR l.bank_account IS NOT NULL
                OR l.tax_id IS NOT NULL OR l.fax IS NOT NULL OR l.postal_code IS NOT NULL
            )
            ON CONFLICT (inquiry_supplier_id) DO NOTHING;
        """)
        cur.execute("ALTER TABLE inquiry_suppliers DROP COLUMN IF EXISTS contract_pdf;")
        cur.execute("ALTER TABLE inquiry_suppliers DROP COLUMN IF EXISTS contract_pdf_path;")
        cur.execute("ALTER TABLE inquiry_suppliers DROP COLUMN IF EXISTS address;")
        cur.execute("ALTER TABLE inquiry_suppliers DROP COLUMN IF EXISTS legal_rep;")
        cur.execute("ALTER TABLE inquiry_suppliers DROP COLUMN IF EXISTS agent;")
        cur.execute("ALTER TABLE inquiry_suppliers DROP COLUMN IF EXISTS phone;")
        cur.execute("ALTER TABLE inquiry_suppliers DROP COLUMN IF EXISTS bank_name;")
        cur.execute("ALTER TABLE inquiry_suppliers DROP COLUMN IF EXISTS bank_account;")
        cur.execute("ALTER TABLE inquiry_suppliers DROP COLUMN IF EXISTS tax_id;")
        cur.execute("ALTER TABLE inquiry_suppliers DROP COLUMN IF EXISTS fax;")
        cur.execute("ALTER TABLE inquiry_suppliers DROP COLUMN IF EXISTS postal_code;")
        cur.execute("ALTER TABLE quotations ADD COLUMN IF NOT EXISTS qty DOUBLE PRECISION;")
        cur.execute("ALTER TABLE quotations ADD COLUMN IF NOT EXISTS delivery_date TIMESTAMP;")
        cur.execute("ALTER TABLE quotations ADD COLUMN IF NOT EXISTS remark TEXT;")
        cur.execute("ALTER TABLE quotations ADD COLUMN IF NOT EXISTS ai_analysis JSON;")
        cur.execute("ALTER TABLE warning_messages ADD COLUMN IF NOT EXISTS is_read BOOLEAN DEFAULT FALSE;")
        print("Database upgraded successfully.")
    except Exception as e:
        print(f"Error upgrading database: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    upgrade_db()
