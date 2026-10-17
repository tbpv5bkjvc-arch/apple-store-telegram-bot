import sqlite3

DB_FILE = "store.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON;")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        telegram_id INTEGER PRIMARY KEY,
        first_name TEXT,
        phone TEXT,
        interaction_count INTEGER DEFAULT 0
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        price_kzt INTEGER,
        stock INTEGER DEFAULT 10
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS cart_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER,
        product_id INTEGER,
        quantity INTEGER DEFAULT 1,
        FOREIGN KEY (telegram_id) REFERENCES users(telegram_id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER,
        total_amount INTEGER,
        status TEXT DEFAULT 'pending_payment',
        receipt_file_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
    );
    """)
    items = [
        ("iPhone 16 Pro", 649990, 5),
        ("iPhone 16", 499990, 8),
        ("MacBook Air 13 M3", 599990, 4),
        ("MacBook Pro 14 M3", 999990, 3),
        ("iPad Air 11 M2", 379990, 6),
        ("Apple Watch Series 10", 249990, 10),
        ("AirPods Pro 2 USB-C", 129990, 15)
    ]
    cur.executemany("INSERT OR IGNORE INTO products (name, price_kzt, stock) VALUES (?, ?, ?);", items)
    conn.commit()
    conn.close()

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def register_user(telegram_id: int, first_name: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT interaction_count FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cur.fetchone()
    if row:
        cur.execute("UPDATE users SET first_name = ?, interaction_count = interaction_count + 1 WHERE telegram_id = ?", (first_name, telegram_id))
    else:
        cur.execute("INSERT INTO users (telegram_id, first_name, interaction_count) VALUES (?, ?, 1)", (telegram_id, first_name))
    conn.commit()
    conn.close()

def save_user_phone(telegram_id: int, phone: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET phone = ? WHERE telegram_id = ?", (phone, telegram_id))
    conn.commit()
    conn.close()

def get_user_stats(telegram_id: int) -> dict:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    user = cur.fetchone()
    cur.execute("SELECT SUM(quantity) as items FROM cart_items WHERE telegram_id = ?", (telegram_id,))
    cart = cur.fetchone()
    total_items = cart["items"] if cart and cart["items"] else 0
    conn.close()
    return {
        "name": user["first_name"] if user else "Клиент",
        "phone": user["phone"] if user and user["phone"] else "Не указан",
        "interactions": user["interaction_count"] if user else 0,
        "cart_items": total_items
    }

def get_active_products():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products ORDER BY price_kzt ASC")
    res = cur.fetchall()
    conn.close()
    return res

def add_product_to_cart(telegram_id: int, product_name: str) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, stock FROM products WHERE LOWER(name) = LOWER(?)", (product_name,))
    product = cur.fetchone()
    if not product or product["stock"] <= 0:
        conn.close()
        return False

    cur.execute("SELECT id, quantity FROM cart_items WHERE telegram_id = ? AND product_id = ?", (telegram_id, product["id"]))
    item = cur.fetchone()
    if item:
        cur.execute("UPDATE cart_items SET quantity = quantity + 1 WHERE id = ?", (item["id"],))
    else:
        cur.execute("INSERT INTO cart_items (telegram_id, product_id, quantity) VALUES (?, ?, 1)", (telegram_id, product["id"]))
    conn.commit()
    conn.close()
    return True

def get_user_cart(telegram_id: int):
    conn = get_connection()
    cur = conn.cursor()
    sql = """
    SELECT p.name, p.price_kzt, ci.quantity, (p.price_kzt * ci.quantity) as subtotal
    FROM cart_items ci
    JOIN products p ON ci.product_id = p.id
    WHERE ci.telegram_id = ?
    """
    cur.execute(sql, (telegram_id,))
    res = cur.fetchall()
    conn.close()
    return res

def create_order_from_cart(telegram_id: int) -> int | None:
    conn = get_connection()
    cur = conn.cursor()
    cart = get_user_cart(telegram_id)
    if not cart:
        conn.close()
        return None

    total = sum(item["subtotal"] for item in cart)
    cur.execute("INSERT INTO orders (telegram_id, total_amount, status) VALUES (?, ?, 'pending_payment')", (telegram_id, total))
    order_id = cur.lastrowid
    cur.execute("DELETE FROM cart_items WHERE telegram_id = ?", (telegram_id,))
    conn.commit()
    conn.close()
    return order_id

def attach_receipt_to_latest_order(telegram_id: int, file_path: str) -> int | None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id FROM orders 
        WHERE telegram_id = ? AND status = 'pending_payment'
        ORDER BY created_at DESC LIMIT 1
    """, (telegram_id,))
    order = cur.fetchone()
    if not order:
        conn.close()
        return None

    cur.execute("UPDATE orders SET receipt_file_path = ?, status = 'payment_review' WHERE id = ?", (file_path, order["id"]))
    conn.commit()
    conn.close()
    return order["id"]

init_db()
