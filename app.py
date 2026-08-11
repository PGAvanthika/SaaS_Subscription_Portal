import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from db import init_db, seed_db, execute_param_sql_secure, execute_raw_sql_vulnerable, add_security_log

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "cybervault-secret-key-2026")

# Initialize database schema and initial seed data on application start
with app.app_context():
    try:
        init_db()
        seed_db()
    except Exception as e:
        print(f"[App Init Warning] DB initialization error: {e}")

@app.before_request
def ensure_security_mode():
    """Ensure a default security mode is initialized in the user session."""
    if 'security_mode' not in session:
        session['security_mode'] = 'VULNERABLE'

# ==========================================================================
# AUTHENTICATION ROUTES
# ==========================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        mode = session.get('security_mode', 'VULNERABLE')

        if mode == 'VULNERABLE':
            # Demonstrating SQL Injection / Unsafe Raw Concatenation
            raw_query = f"SELECT * FROM users WHERE username = '{username}' AND raw_password = '{password}';"
            try:
                users = execute_raw_sql_vulnerable(raw_query)
                if users:
                    user = users[0]
                    session['user_id'] = user['id']
                    session['username'] = user['username']
                    session['role'] = user['role']
                    add_security_log("AUTH_LOGIN_VULN", f"User '{username}' logged in via vulnerable query", "WARNING")
                    flash(f"Welcome back, {user['username']}!", "success")
                    return redirect(url_for('dashboard'))
                else:
                    add_security_log("AUTH_LOGIN_FAIL", f"Failed login attempt for '{username}'", "FAILURE")
                    flash("Invalid credentials.", "danger")
            except Exception as err:
                add_security_log("SQLI_ATTEMPT", f"SQL Injection error triggered: {err}", "VULNERABILITY_EXPLOITED")
                flash(f"Database Query Error (SQLi trigger): {err}", "danger")
        else:
            # SECURE MODE: Parameterized Query & Hashed Password Check
            secure_query = "SELECT * FROM users WHERE username = %s OR email = %s;"
            users = execute_param_sql_secure(secure_query, (username, username))
            if users:
                user = users[0]
                if check_password_hash(user['password_hash'], password) or user['raw_password'] == password:
                    session['user_id'] = user['id']
                    session['username'] = user['username']
                    session['role'] = user['role']
                    add_security_log("AUTH_LOGIN_SECURE", f"User '{username}' authenticated securely", "SUCCESS")
                    flash(f"Secure Login Successful! Welcome, {user['username']}.", "success")
                    return redirect(url_for('dashboard'))

            add_security_log("AUTH_LOGIN_FAIL", f"Failed secure login for '{username}'", "FAILURE")
            flash("Invalid credentials provided.", "danger")

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not email or not password:
            flash("All fields are required.", "danger")
            return redirect(url_for('register'))

        # Check existing user
        existing = execute_param_sql_secure("SELECT id FROM users WHERE username = %s OR email = %s;", (username, email))
        if existing:
            flash("Username or Email already registered.", "danger")
            return redirect(url_for('register'))

        pass_hash = generate_password_hash(password)
        insert_query = "INSERT INTO users (username, email, password_hash, raw_password, role) VALUES (%s, %s, %s, %s, 'user');"
        execute_param_sql_secure(insert_query, (username, email, pass_hash, password))

        # Get inserted user
        new_users = execute_param_sql_secure("SELECT id FROM users WHERE username = %s;", (username,))
        if new_users:
            user_id = new_users[0]['id']
            # Create default free subscription
            execute_param_sql_secure("INSERT INTO subscriptions (user_id, plan_name, price, status) VALUES (%s, 'CyberVault Free Starter', 0.00, 'active');", (user_id,))
            execute_param_sql_secure("INSERT INTO invoices (user_id, amount, status, description) VALUES (%s, 0.00, 'paid', 'Free Plan Welcome Invoice #INV-NEW');", (user_id,))

        add_security_log("USER_REGISTER", f"New user '{username}' registered", "SUCCESS")
        flash("Registration successful! Please login.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('role', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

# ==========================================================================
# SAAS CORE ROUTES
# ==========================================================================

@app.route('/')
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    
    # Subscriptions
    subs = execute_param_sql_secure("SELECT * FROM subscriptions WHERE user_id = %s ORDER BY id DESC LIMIT 1;", (user_id,))
    subscription = subs[0] if subs else None

    # Invoices
    invoices = execute_param_sql_secure("SELECT * FROM invoices WHERE user_id = %s ORDER BY id DESC;", (user_id,))

    # Support Tickets
    tickets = execute_param_sql_secure("SELECT * FROM support_tickets WHERE user_id = %s ORDER BY id DESC;", (user_id,))

    return render_template('dashboard.html', subscription=subscription, invoices=invoices, tickets=tickets)

@app.route('/subscriptions', methods=['GET', 'POST'])
def subscriptions():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    
    if request.method == 'POST':
        plan_name = request.form.get('plan_name')
        client_price = request.form.get('price', 0.0)
        mode = session.get('security_mode', 'VULNERABLE')

        PLANS = {
            'CyberVault Free Starter': 0.00,
            'CyberVault Pro Plan': 99.00,
            'CyberVault Enterprise': 499.00
        }

        if mode == 'VULNERABLE':
            # Parameter Tampering Vulnerability: Trusts price sent from client form!
            final_price = float(client_price)
            add_security_log("PARAM_TAMPER_VULN", f"User {user_id} ordered {plan_name} with client price ${final_price}", "VULNERABLE")
        else:
            # SECURE MODE: Validates price against authoritative server catalog
            final_price = PLANS.get(plan_name, 0.00)
            add_security_log("PARAM_TAMPER_SECURE", f"Server verified price for {plan_name} as ${final_price}", "SECURE")

        # Update or create subscription
        execute_param_sql_secure("INSERT INTO subscriptions (user_id, plan_name, price, status) VALUES (%s, %s, %s, 'active');", (user_id, plan_name, final_price))
        # Create invoice record
        execute_param_sql_secure("INSERT INTO invoices (user_id, amount, status, description) VALUES (%s, %s, 'paid', %s);", (user_id, final_price, f"{plan_name} Subscription Purchase"))

        flash(f"Successfully subscribed to {plan_name} for ${final_price:.2f}!", "success")
        return redirect(url_for('dashboard'))

    # GET request
    subs = execute_param_sql_secure("SELECT * FROM subscriptions WHERE user_id = %s ORDER BY id DESC LIMIT 1;", (user_id,))
    current_sub = subs[0] if subs else None
    return render_template('subscriptions.html', current_sub=current_sub)

@app.route('/invoices')
def invoices():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    invoices_list = execute_param_sql_secure("SELECT * FROM invoices WHERE user_id = %s ORDER BY id DESC;", (user_id,))
    return render_template('invoices.html', invoices=invoices_list)

@app.route('/invoice/<int:invoice_id>')
def view_invoice(invoice_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    mode = session.get('security_mode', 'VULNERABLE')

    if mode == 'VULNERABLE':
        # IDOR / Broken Access Control Vulnerability: No ownership check!
        invoice_rows = execute_param_sql_secure("SELECT * FROM invoices WHERE id = %s;", (invoice_id,))
        if not invoice_rows:
            flash("Invoice not found.", "danger")
            return redirect(url_for('invoices'))
        invoice = invoice_rows[0]
        if invoice['user_id'] != user_id:
            add_security_log("IDOR_EXPLOITED", f"User {user_id} accessed Invoice #{invoice_id} belonging to User {invoice['user_id']}", "EXPLOITED")
            flash(f"⚠️ VULNERABLE DEMO: You accessed Invoice #{invoice_id} belonging to User ID {invoice['user_id']}!", "warning")
    else:
        # SECURE MODE: Strict Authorization / Ownership Verification
        invoice_rows = execute_param_sql_secure("SELECT * FROM invoices WHERE id = %s AND user_id = %s;", (invoice_id, user_id))
        if not invoice_rows:
            add_security_log("IDOR_BLOCKED", f"User {user_id} blocked from unauthorized access to Invoice #{invoice_id}", "BLOCKED")
            flash("Access Denied: You do not have permission to view this invoice statement.", "danger")
            return redirect(url_for('invoices'))
        invoice = invoice_rows[0]

    # Fetch invoice owner details for display
    owner_rows = execute_param_sql_secure("SELECT username, email FROM users WHERE id = %s;", (invoice['user_id'],))
    owner = owner_rows[0] if owner_rows else {'username': 'Unknown', 'email': 'N/A'}

    return render_template('invoice_detail.html', invoice=invoice, owner=owner)

@app.route('/tickets', methods=['GET', 'POST'])
def tickets():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    if request.method == 'POST':
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()

        if subject and message:
            execute_param_sql_secure(
                "INSERT INTO support_tickets (user_id, subject, message, status) VALUES (%s, %s, %s, 'open');",
                (user_id, subject, message)
            )
            add_security_log("SUPPORT_TICKET_CREATED", f"Support ticket created by User {user_id}", "INFO")
            flash("Support ticket submitted successfully!", "success")
            return redirect(url_for('dashboard'))

    tickets_list = execute_param_sql_secure("SELECT * FROM support_tickets ORDER BY id DESC;")
    return render_template('tickets.html', tickets=tickets_list)

# ==========================================================================
# SECURITY LAB & DEMONSTRATION ROUTES
# ==========================================================================

@app.route('/lab')
def security_lab():
    return render_template('lab.html')

@app.route('/security-logs')
def security_logs():
    logs = execute_param_sql_secure("SELECT * FROM security_logs ORDER BY id DESC LIMIT 50;")
    return render_template('logs.html', logs=logs)

@app.route('/phishing-demo')
def phishing_demo():
    return render_template('phishing.html')

@app.route('/api/toggle-mode', methods=['POST'])
def toggle_mode():
    data = request.get_json() or {}
    new_mode = data.get('mode', 'VULNERABLE')
    if new_mode in ['VULNERABLE', 'SECURE']:
        session['security_mode'] = new_mode
        add_security_log("SECURITY_MODE_CHANGE", f"Security Mode toggled to {new_mode}", "CONFIG")
        return jsonify({'success': True, 'mode': new_mode})
    return jsonify({'success': False, 'error': 'Invalid mode'}), 400

@app.route('/api/sqli-demo', methods=['POST'])
def sqli_demo():
    """
    Interactive API for SQL Injection testing.
    Executes raw string query in VULNERABLE mode or parameterized query in SECURE mode.
    """
    data = request.get_json() or {}
    payload = data.get('payload', '').strip()
    mode = session.get('security_mode', 'VULNERABLE')

    if not payload:
        payload = "' OR '1'='1"

    if mode == 'VULNERABLE':
        raw_query = f"SELECT id, username, email, raw_password, role FROM users WHERE username = '{payload}';"
        try:
            results = execute_raw_sql_vulnerable(raw_query)
            add_security_log("SQLI_TEST_VULN", f"SQLi payload executed via raw query: {payload}", "EXPLOITED")
            return jsonify({
                'success': True,
                'mode': 'VULNERABLE',
                'executed_query': raw_query,
                'results': results,
                'result_count': len(results),
                'explanation': "⚠️ VULNERABLE MODE: Input string was directly concatenated into the SQL command structure. Metacharacters like single quotes (') disrupted the query syntax, altering query logic."
            })
        except Exception as e:
            add_security_log("SQLI_TEST_ERROR", f"SQLi raw query syntax error: {e}", "EXPLOITED")
            return jsonify({
                'success': False,
                'mode': 'VULNERABLE',
                'executed_query': raw_query,
                'error': str(e),
                'explanation': "⚠️ VULNERABLE MODE: Injected SQL payload caused a database operational/syntax error."
            }), 400
    else:
        # SECURE MODE: Parameterized prepared statement
        secure_query = "SELECT id, username, email, raw_password, role FROM users WHERE username = %s;"
        try:
            results = execute_param_sql_secure(secure_query, (payload,))
            add_security_log("SQLI_TEST_SECURE", f"SQLi payload safely bound via parameter: {payload}", "BLOCKED")
            return jsonify({
                'success': True,
                'mode': 'SECURE',
                'executed_query': f"SELECT id, username, email, raw_password, role FROM users WHERE username = ? [Bound Param: '{payload}']",
                'results': results,
                'result_count': len(results),
                'explanation': "🛡️ SECURE MODE: The input payload was bound safely as a literal text parameter. SQL metacharacters were neutralized and could not alter query structure."
            })
        except Exception as e:
            return jsonify({'success': False, 'mode': 'SECURE', 'error': str(e)}), 400


if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    print(f"🚀 Starting CyberVault Security Portal on http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)
