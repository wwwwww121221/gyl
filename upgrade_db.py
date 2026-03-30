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
