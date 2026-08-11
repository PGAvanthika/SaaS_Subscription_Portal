# SaaSFlow: Enterprise SaaS Security & Attack Demonstration Platform
## Project Documentation & Security Architecture Report

---

## 1. ABSTRACT

**SaaSFlow** is a simulated enterprise Software-as-a-Service (SaaS) subscription platform engineered specifically to demonstrate common web application vulnerabilities and their corresponding defensive mitigations. Designed for cybersecurity education, academic evaluation, and security awareness, SaaSFlow provides an interactive side-by-side comparison between **Vulnerable Behavior** and **Secure Implementation** across six major web security domains: SQL Injection (SQLi), Password Guessing / Credential Stuffing, Stored Cross-Site Scripting (Stored XSS), Parameter Tampering, Insecure Direct Object References (IDOR / Broken Access Control), and Phishing Simulation.

Built with Python Flask, PostgreSQL (via Supabase / psycopg) with local SQLite fallback capability, and a modern, emoji-free enterprise dark UI, SaaSFlow enables security researchers and evaluators to execute live attacks, analyze raw execution traces, inspect real-time audit logs, and observe defensive security mechanisms in real time.

---

## 2. INTRODUCTION

Modern cloud-native SaaS applications handle sensitive customer subscriptions, financial transactions, and proprietary data. However, software security flaws in web frameworks and data access layers expose applications to severe risk.

SaaSFlow is designed as a dual-mode application featuring an interactive **Platform Security Mode Switch** (`EXPOSED / VULNERABLE` vs `PROTECTED / SECURE`). By toggling between modes, the application dynamically alters its backend execution strategy—demonstrating how insecure code practices (such as raw string formatting, unencoded output rendering, and missing authorization checks) lead to system compromise, while secure practices (such as prepared statement binding, HTML output encoding, server catalog enforcement, and session ownership verification) successfully neutralize threat vectors.

---

## 3. PROBLEM STATEMENT

Many software developers understand security vulnerabilities theoretically but lack empirical, hands-on experience observing how specific coding mistakes translate into live exploits. Furthermore, standard security tutorials often present isolated snippets rather than demonstrating vulnerabilities within a realistic, multi-tenant SaaS business context (such as billing statements, support desks, and subscription checkout workflows).

SaaSFlow addresses this gap by providing a functional, full-stack SaaS environment where security vulnerabilities are contextualized within business workflows and contrasted directly against enterprise-grade defenses.

---

## 4. OBJECTIVES

1. Build a functional, modern SaaS subscription portal with authentication, plan management, billing statements, and support desk ticketing.
2. Implement controlled, reproducible implementations of six critical web security concepts.
3. Architect a session-based dual-mode engine (`VULNERABLE` vs `SECURE`) controlling backend Python logic and database access.
4. Implement a real-time Security Audit Telemetry Logging System recording security events with client IP addresses and timestamps.
5. Provide a polished, emoji-free enterprise dark UI inspired by industry platforms like Cloudflare, Linear, Stripe, and Snyk for academic presentation and demonstration.

---

## 5. SCOPE

- **Target Environment**: Local demonstration server executing against a Supabase cloud PostgreSQL database or local SQLite sandbox.
- **Vulnerability Coverage**:
  1. SQL Injection (Authentication Bypass & Data Extraction)
  2. Password Guessing & Audit Logging
  3. Stored Cross-Site Scripting (Support Desk Payload Storage)
  4. Parameter Tampering (Subscription Checkout Price Manipulation)
  5. URL Manipulation / IDOR (Invoice Statement Access Control)
  6. Phishing Simulation (Domain Spoofing & Origin Warning Banner)
- **Non-Goals**: No external network attacks, malware, real payment processing, or external phishing infrastructure are included. All attack scenarios operate strictly in a controlled sandbox.

---

## 6. TECHNOLOGIES USED

### Backend Architecture
- **Language & Framework**: Python 3.11, Flask 3.0
- **Database Driver**: `psycopg` (PostgreSQL 3.x driver)
- **Cloud Database**: Cloud PostgreSQL hosted on Supabase (`db.daptomthjnprtfxnqevm.supabase.co`)
- **Local Fallback Database**: SQLite 3 (`cybervault.db`)
- **Environment & Cryptography**: `python-dotenv`, `Werkzeug.security` (PBKDF2/Argon2 password hashing)

### Frontend Architecture
- **Markup & Styling**: HTML5, Custom Vanilla CSS (Dark Theme, Inter Typography, CSS Grid/Flexbox)
- **Icons**: Clean inline SVG vector icons (Lucide icon aesthetic, 0% emojis)
- **Client Scripting**: Vanilla JavaScript (ES6 fetch API, dynamic toast notifications, live execution console)

---

## 7. SECURITY ATTACKS IMPLEMENTED

### 7.1 SQL Injection (SQLi)
* **What It Is**: SQL Injection occurs when untrusted user input is directly concatenated into a SQL statement without parameter binding, allowing untrusted input to distort SQL command syntax.
* **How It Works in SaaSFlow**:
  * *Vulnerable Mode*: `raw_query = f"SELECT * FROM users WHERE username = '{username}' AND raw_password = '{password}';"`
  * Inputting payload `admin' --` truncates the password check, authenticating the user as `admin` without knowing the password.
* **How It Is Rectified**:
  * *Secure Mode*: Uses parameterized prepared statements: `SELECT * FROM users WHERE username = %s OR email = %s;` passed with tuple parameters `(username, username)`. Database drivers treat input strings strictly as literal data, preventing syntax manipulation.

---

### 7.2 Password Guessing & Audit Trail
* **What It Is**: Password Guessing (brute force / credential stuffing) involves automated trial of password dictionaries against login endpoints.
* **How It Works in SaaSFlow**:
  * *Vulnerable Mode*: Login handler evaluates attempts without tracking attempt counters or rate limits, permitting repeated unauthorized login retries.
* **How It Is Rectified**:
  * *Secure Mode*: Uses `check_password_hash` to evaluate salted password hashes and dispatches `AUTH_LOGIN_FAIL` telemetry logs containing source IP addresses into `security_logs` for audit tracking.

---

### 7.3 Stored Cross-Site Scripting (Stored XSS)
* **What It Is**: Stored XSS occurs when an application receives malicious HTML/JavaScript input, stores it permanently in a database, and subsequently renders it unescaped into victim browser sessions.
* **How It Works in SaaSFlow**:
  * *Vulnerable Mode*: Support ticket messages are rendered in Jinja2 using `{{ ticket.message | safe }}`.
  * Injected payload `<img src=x onerror="alert('XSS!')">` is saved in `support_tickets` table and executes whenever any user views the ticket page.
* **How It Is Rectified**:
  * *Secure Mode*: Employs standard auto-escaping (`{{ ticket.message }}`). Metacharacters `< > " ' &` are converted into HTML entity representations (`&lt; &gt;`), causing the browser to render text without script execution.

---

### 7.4 Parameter Tampering
* **What It Is**: Parameter Tampering occurs when an application trusts client-submitted form inputs or query parameters (such as price, quantity, or role) for authorization or billing decisions without server-side validation.
* **How It Works in SaaSFlow**:
  * The subscription UI presents a standard professional billing page submitting `plan_name` and `<input type="hidden" name="price" value="99.00">`.
  * Testers alter the hidden form `price` field value to `$0.00` using Browser Developer Tools (Inspect Element / Network tab) before clicking **Subscribe**.
  * *Vulnerable Mode*: Backend evaluates `price = float(request.form.get('price'))`, directly creating a `$0.00` subscription invoice for the $99 Pro Plan.
* **How It Is Rectified**:
  * *Secure Mode*: The backend ignores the client-submitted `price` parameter and retrieves the authoritative pricing directly from the server-side catalog (`PLANS_CATALOG[plan_name]`), enforcing the official `$99.00` price regardless of client parameter tampering.

---

### 7.5 URL Manipulation / IDOR (Insecure Direct Object References)
* **What It Is**: IDOR occurs when an application retrieves database objects using user-supplied primary keys (e.g. `/invoice/<id>`) without validating whether the authenticated session user owns the requested resource.
* **How It Works in SaaSFlow**:
  * *Vulnerable Mode*: Endpoint `/invoice/<id>` queries `SELECT * FROM invoices WHERE id = %s`. User `bob` (ID 3) can access Admin's statement by navigating to `/invoice/1`.
* **How It Is Rectified**:
  * *Secure Mode*: Endpoint enforces session ownership check in the database query: `SELECT * FROM invoices WHERE id = %s AND user_id = %s;`. Unauthorized requests trigger an Access Denied message and HTTP redirect.

---

### 7.6 Phishing Simulation
* **What It Is**: Phishing involves spoofing legitimate SaaS application interfaces on lookalike domains to trick users into submitting credentials.
* **How It Works in SaaSFlow**:
  * *Vulnerable Mode*: Renders a simulated login portal on lookalike domain `saasflow-security.local` without domain integrity warnings.
* **How It Is Rectified**:
  * *Secure Mode*: Renders an explicit **Security Alert Banner** (`UNTRUSTED DOMAIN ORIGIN DETECTED`) warning users about unverified domain origins before credentials can be entered.

---

## 8. SYSTEM DATABASE SCHEMA

The PostgreSQL database contains 5 core relational tables:

```sql
CREATE TABLE users (
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

CREATE TABLE subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    plan_name VARCHAR(50) NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    renews_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE invoices (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    amount NUMERIC(10, 2) NOT NULL,
    status VARCHAR(20) DEFAULT 'paid',
    invoice_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description VARCHAR(255) NOT NULL
);

CREATE TABLE support_tickets (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    subject VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'open',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE security_logs (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    status VARCHAR(20) NOT NULL,
    ip_address VARCHAR(50) DEFAULT '127.0.0.1',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 9. CONCLUSION & FUTURE WORK

SaaSFlow successfully fulfills all requirements for a simulated SaaS cybersecurity demonstration platform. By combining a real-world multi-tenant business model with side-by-side vulnerable vs. secure implementation patterns, SaaSFlow serves as a complete academic capstone project suitable for technical evaluations, portfolio showcases, and security awareness training.

Future enhancements include integrating WebAuthn FIDO2 passwordless authentication, implementing automated rate-limiting middleware (such as Redis token buckets), and expanding threat detection coverage to include Cross-Site Request Forgery (CSRF) and Server-Side Request Forgery (SSRF).
