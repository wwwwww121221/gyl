import psycopg2

DATABASE_URL = "postgresql://postgres:123456@localhost:5432/supply_chain_agent"

def upgrade_db():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()
    
    try:
        cur.execute("ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS email VARCHAR;")
        cur.execute("ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS level VARCHAR DEFAULT 'general';")
        cur.execute("ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'approved';")
        cur.execute("ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id);")
        print("Database upgraded successfully.")
    except Exception as e:
        print(f"Error upgrading database: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    upgrade_db()
