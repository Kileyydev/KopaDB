# The Pesapal Junior Dev Challenge 2026  
## KopaDB — A Lightweight Relational Database Engine with a Demo Web App


## Introduction

This project is my submission for The Pesapal Junior Developer Challenge 2026.

The goal of the challenge is to design and implement a simple relational database management system (RDBMS) with support for table definitions, CRUD operations, indexing, constraints, basic joins, and an SQL-like interactive interface, and to demonstrate its usage through a trivial web application.

To address this, I built **KopaDB**, which is a lightweight, file-backed relational database engine implemented in Python, together with a Flask-based demo web application that uses the database to manage merchants, customers, loans, and transactions.

This project focuses on **clear thinking, correctness, and practical system design**, rather than production-grade completeness.

---

## Core Features of the RDBMS

### Database Engine
- Table creation with schema definitions
- Supported data types:
  - `INT`
  - `FLOAT`
  - `TEXT`
  - `TIMESTAMP`
- Primary key enforcement
- Unique key constraints
- In-memory storage with **JSON persistence** to disk
- Automatic data reload on startup

### CRUD Operations
- `INSERT` — add new records with constraint validation
- `SELECT` — retrieve records with optional filtering
- `UPDATE` — modify existing records
- `DELETE` — remove records safely

### Indexing
- Single-column indexing
- Indexes accelerate equality-based lookups
- Indexes are automatically rebuilt when the database reloads
- Indexes are kept consistent during insert, update, and delete operations

### Joins
- Basic JOIN support between tables
- Implemented using a simple nested-loop strategy for clarity

---

## SQL-Like Interface (REPL)

The database exposes an **interactive REPL (Read-Eval-Print Loop)** that accepts SQL-like commands such as:

- `CREATE TABLE`
- `INSERT INTO`
- `SELECT * FROM`
- `UPDATE`
- `DELETE`
- `CREATE INDEX`
- `JOIN`

This interface allows direct interaction with the database engine and demonstrates how SQL-style commands are parsed and executed internally.

---

## Demo Web Application

To demonstrate real-world usage of the database, I built a Flask web application that uses KopaDB as its data layer.

### Key Functionalities
- Merchant registration and login
- Customer registration
- Loan application and tracking
- Transaction and balance management
- Risk and fraud flagging logic (rule-based)

### Automation & Business Logic
- When a merchant registers, they are automatically credited with **$1,000,000** in starting funds
- Timestamps such as `created_at` and `updated_at` are automatically handled
- Session-based authentication is used to manage logged-in users

> Note: Sessions are used for simplicity and demonstration purposes. More advanced authentication mechanisms are considered out of scope for this challenge but are discussed below as future improvements.

---

## Security Considerations

- Passwords are currently hashed using **SHA-256**
- Input validation is enforced at the database and application layers
- Constraint violations (primary key, unique key) are strictly enforced

These measures are intentionally lightweight to keep the focus on core system design.

---

## Planned Improvements & Future Work

The following enhancements are intentionally left for future iterations:

### Security
- Replace SHA-256 password hashing with **bcrypt** for stronger password security
- Add OTP-based email verification
- Introduce rate limiting and CSRF protection

### Database Engine
- Column projection (e.g. `SELECT id, email FROM users`)
- Support for multiple WHERE conditions (`AND` / `OR`)
- Comparison operators (`>`, `<`, `>=`, `<=`)
- Optimized join strategies (e.g. hash joins)
- Transaction support (`BEGIN`, `COMMIT`, `ROLLBACK`)

### Application Layer
- Role-based access control
- Improved session handling or token-based authentication
- More detailed audit logging

---

## Design Philosophy

This project prioritizes:
- Simplicity and clarity over over-engineering
- Readable, modular code
- Explicit handling of constraints and edge cases
- Demonstrating understanding of how databases work internally

While not production-ready, KopaDB is designed to be educational, extendable, and practical.

---
