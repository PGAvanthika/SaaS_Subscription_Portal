import os
import sqlite3
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

def is_postgres():
    url = os.getenv("DATABASE_URL", "").strip()
    return bool(url and (url.startswith("postgresql://") or url.startswith("postgres://")))

def get_db_connection():
    """
    Returns a PostgreSQL psycopg connection if DATABASE_URL is defined,
    otherwise falls back to a local SQLite database connection.
    Both return dictionary-like row results.
    """
    load_dotenv(override=True)
    db_url = os.getenv("DATABASE_URL", "").strip()

    if is_postgres():
        try:
            # Append sslmode=require if not present for Supabase PostgreSQL
            connect_url = db_url
            if "sslmode=" not in connect_url:
                connect_url += ("&sslmode=require" if "?" in connect_url else "?sslmode=require")

            conn = psycopg.connect(connect_url, row_factory=dict_row)
            return conn, "postgres"
        except Exception as e:
            print(f"[DB Warning] Could not connect to Supabase PostgreSQL: {e}. Falling back to SQLite.")
    
    # SQLite fallback
    db_path = os.path.join(os.path.dirname(__file__), "cybervault.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn, "sqlite"

def execute_raw_sql_vulnerable(query):
    """
    Executes a raw SQL string query directly without parameter binding.
    USED SPECIFICALLY FOR DEMONSTRATING VULNERABLE BEHAVIOR (e.g. SQL Injection).
    """
    conn, db_type = get_db_connection()
    try:
        if db_type == "postgres":
            with conn.cursor() as cur:
                cur.execute(query)
                conn.commit()
                try:
                    results = cur.fetchall()
                    return results
                except Exception:
                    return []
        else:
            cur = conn.cursor()
            cur.executescript(query) if ";" in query and not query.strip().startswith("SELECT") else cur.execute(query)
            conn.commit()
            results = [dict(row) for row in cur.fetchall()] if cur.description else []
            return results
    finally:
        conn.close()

def execute_param_sql_secure(query, params=()):
    """
    Executes a SQL query using parameterized placeholders.
    USED SPECIFICALLY FOR DEMONSTRATING SECURE BEHAVIOR.
    """
    conn, db_type = get_db_connection()
    try:
        if db_type == "postgres":
            with conn.cursor() as cur:
                cur.execute(query, params)
                conn.commit()
                try:
                    results = cur.fetchall()
                    return results
                except Exception:
                    return []
        else:
            # Convert %s or %()s placeholders for SQLite if needed
            sqlite_query = query.replace("%s", "?")
            cur = conn.cursor()
            cur.execute(sqlite_query, params)
            conn.commit()
            results = [dict(row) for row in cur.fetchall()] if cur.description else []
            return results
    finally:
        conn.close()

def init_db():
    """Creates initial database schema if not exists."""
    conn, db_type = get_db_connection()
    try:
        cur = conn.cursor()
        
        if db_type == "postgres":
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    raw_password VARCHAR(255) NOT NULL,
                    role VARCHAR(20) DEFAULT 'user',
                    failed_attempts INT DEFAULT 0,
                    locked_until TIMESTAMP NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS subscriptions (
                    id SERIAL PRIMARY KEY,
                    user_id INT REFERENCES users(id) ON DELETE CASCADE,
                    plan_name VARCHAR(50) NOT NULL,
                    price NUMERIC(10, 2) NOT NULL,
                    status VARCHAR(20) DEFAULT 'active',
                    renews_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS invoices (
                    id SERIAL PRIMARY KEY,
                    user_id INT REFERENCES users(id) ON DELETE CASCADE,
                    amount NUMERIC(10, 2) NOT NULL,
                    status VARCHAR(20) DEFAULT 'paid',
                    invoice_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    description VARCHAR(255) NOT NULL
                );

                CREATE TABLE IF NOT EXISTS support_tickets (
                    id SERIAL PRIMARY KEY,
                    user_id INT REFERENCES users(id) ON DELETE CASCADE,
                    subject VARCHAR(255) NOT NULL,
                    message TEXT NOT NULL,
                    status VARCHAR(20) DEFAULT 'open',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS security_logs (
                    id SERIAL PRIMARY KEY,
                    event_type VARCHAR(50) NOT NULL,
                    description TEXT NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    ip_address VARCHAR(50) DEFAULT '127.0.0.1',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
        else:
            cur.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    raw_password TEXT NOT NULL,
                    role TEXT DEFAULT 'user',
                    failed_attempts INTEGER DEFAULT 0,
                    locked_until TIMESTAMP NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    plan_name TEXT NOT NULL,
                    price REAL NOT NULL,
                    status TEXT DEFAULT 'active',
                    renews_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS invoices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    amount REAL NOT NULL,
                    status TEXT DEFAULT 'paid',
                    invoice_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    description TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS support_tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    subject TEXT NOT NULL,
                    message TEXT NOT NULL,
                    status TEXT DEFAULT 'open',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS security_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    status TEXT NOT NULL,
                    ip_address TEXT DEFAULT '127.0.0.1',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
        conn.commit()
        print(f"[DB Info] Initialized schema successfully using {db_type.upper()}.")
    finally:
        conn.close()

def seed_db():
    """Seeds sample data for testing and demonstrations if empty."""
    conn, db_type = get_db_connection()
    try:
        cur = conn.cursor()
        if db_type == "postgres":
            cur.execute("SELECT COUNT(*) as count FROM users;")
            row = cur.fetchone()
            user_count = row['count'] if isinstance(row, dict) else row[0]
        else:
            cur.execute("SELECT COUNT(*) as count FROM users;")
            user_count = cur.fetchone()[0]

        if user_count == 0:
            print("[DB Seed] Seeding initial CyberVault demo users and records...")
            users = [
                ('admin', 'admin@cybervault.local', generate_password_hash('AdminPass123!'), 'AdminPass123!', 'admin'),
                ('alice', 'alice@cybervault.local', generate_password_hash('AliceSecret123!'), 'AliceSecret123!', 'user'),
                ('bob', 'bob@cybervault.local', generate_password_hash('BobPassword456!'), 'BobPassword456!', 'user'),
                ('attacker', 'attacker@darknet.io', generate_password_hash('Hacker123!'), 'Hacker123!', 'user')
            ]
            
            for u in users:
                if db_type == "postgres":
                    cur.execute(
                        "INSERT INTO users (username, email, password_hash, raw_password, role) VALUES (%s, %s, %s, %s, %s);",
                        u
                    )
                else:
                    cur.execute(
                        "INSERT INTO users (username, email, password_hash, raw_password, role) VALUES (?, ?, ?, ?, ?);",
                        u
                    )

            # Subscriptions
            subscriptions = [
                (1, 'CyberVault Enterprise', 499.00, 'active'),
                (2, 'CyberVault Pro Plan', 99.00, 'active'),
                (3, 'CyberVault Free Starter', 0.00, 'active'),
                (4, 'CyberVault Pro Plan', 99.00, 'active')
            ]
            for s in subscriptions:
                if db_type == "postgres":
                    cur.execute(
                        "INSERT INTO subscriptions (user_id, plan_name, price, status) VALUES (%s, %s, %s, %s);",
                        s
                    )
                else:
                    cur.execute(
                        "INSERT INTO subscriptions (user_id, plan_name, price, status) VALUES (?, ?, ?, ?);",
                        s
                    )

            # Invoices
            invoices = [
                (1, 499.00, 'paid', 'Enterprise Annual License #INV-1001'),
                (2, 99.00, 'paid', 'Pro Monthly Subscription #INV-1002'),
                (3, 0.00, 'paid', 'Free Plan Initialization #INV-1003'),
                (4, 99.00, 'unpaid', 'Pro Plan Monthly Renewal #INV-1004')
            ]
            for inv in invoices:
                if db_type == "postgres":
                    cur.execute(
                        "INSERT INTO invoices (user_id, amount, status, description) VALUES (%s, %s, %s, %s);",
                        inv
                    )
                else:
                    cur.execute(
                        "INSERT INTO invoices (user_id, amount, status, description) VALUES (?, ?, ?, ?);",
                        inv
                    )

            # Support tickets (including initial sample ticket)
            tickets = [
                (2, 'Upgrade Request', 'Hello Support, I would like to inquire about API access for Pro users.', 'open'),
                (3, 'Password Reset Help', 'I am unable to reset my password using the standard portal link.', 'closed')
            ]
            for t in tickets:
                if db_type == "postgres":
                    cur.execute(
                        "INSERT INTO support_tickets (user_id, subject, message, status) VALUES (%s, %s, %s, %s);",
                        t
                    )
                else:
                    cur.execute(
                        "INSERT INTO support_tickets (user_id, subject, message, status) VALUES (?, ?, ?, ?);",
                        t
                    )

            # Security Logs
            logs = [
                ('SYSTEM_INIT', 'CyberVault Security Portal initialized', 'SUCCESS'),
                ('AUTH_LOGIN', 'User admin logged in successfully from 127.0.0.1', 'SUCCESS')
            ]
            for l in logs:
                if db_type == "postgres":
                    cur.execute(
                        "INSERT INTO security_logs (event_type, description, status) VALUES (%s, %s, %s);",
                        l
                    )
                else:
                    cur.execute(
                        "INSERT INTO security_logs (event_type, description, status) VALUES (?, ?, ?);",
                        l
                    )

            conn.commit()
            print("[DB Seed] Seed completed successfully.")
    finally:
        conn.close()

def add_security_log(event_type, description, status="INFO", ip="127.0.0.1"):
    """Helper to log security events into security_logs table."""
    query = "INSERT INTO security_logs (event_type, description, status, ip_address) VALUES (%s, %s, %s, %s);"
    try:
        execute_param_sql_secure(query, (event_type, description, status, ip))
    except Exception as e:
        print(f"[Log Error] Failed to insert security log: {e}")
