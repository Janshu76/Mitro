# Synthetic-only schema reference. The runtime SQLAlchemy models are authoritative for this fixture.
CREATE TABLE customers (id INTEGER PRIMARY KEY, full_name TEXT, phone TEXT, email TEXT, pan_last4 TEXT, consent_status TEXT);
CREATE TABLE loan_applications (id INTEGER PRIMARY KEY, customer_id INTEGER, requested_amount REAL, purpose TEXT, status TEXT, risk_score INTEGER, decision_reason TEXT);
CREATE TABLE loan_accounts (id INTEGER PRIMARY KEY, application_id INTEGER, customer_id INTEGER, principal REAL, outstanding REAL, status TEXT);
CREATE TABLE repayments (id INTEGER PRIMARY KEY, loan_id INTEGER, amount REAL, reference TEXT, received_at TIMESTAMP);
CREATE TABLE partner_events (id INTEGER PRIMARY KEY, partner_name TEXT, loan_id INTEGER, event_type TEXT, payload_summary TEXT);
