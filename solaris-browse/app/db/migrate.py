import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os

def run_migration():
    conn = psycopg2.connect(
        dbname="app_db",
        user="postgres",
        password="postgres",
        host="localhost",
        port="5432"
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    
    try:
        with conn.cursor() as cur:
            migrations_path = os.path.join(os.path.dirname(__file__), '..', '..', 'migrations')
            migration_file = os.path.join(migrations_path, '01_create_tables.sql')
            
            with open(migration_file, 'r') as file:
                cur.execute(file.read())
            print("Migration completed successfully")
    except Exception as e:
        print(f"Error during migration: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
