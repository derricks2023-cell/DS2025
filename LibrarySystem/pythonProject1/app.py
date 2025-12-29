from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
import pymysql
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'library_secret_key_123'  # 闪现消息需要 secret_key

# 数据库连接配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'NewStrongPassword123!', # <-- 确保与你本地一致
    'database': 'library_db',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def get_db():
    return pymysql.connect(**DB_CONFIG)

# --- 1. 仪表盘首页 ---
@app.route('/')
def index():
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT category, SUM(stock) as count FROM books GROUP BY category")
            chart_data = cursor.fetchall()
            cursor.execute("SELECT COUNT(*) as total FROM books")
            total_books = cursor.fetchone()['total'] if cursor.rowcount > 0 else 0
            cursor.execute("SELECT COUNT(*) as total FROM records WHERE status='借出'")
            total_borrows = cursor.fetchone()['total'] if cursor.rowcount > 0 else 0
    finally:
        conn.close()
    return render_template('index.html', chart_data=chart_data, total_books=total_books, total_borrows=total_borrows)

# --- 2. 图书管理 ---
@app.route('/books', methods=['GET', 'POST'])
def manage_books():
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            if request.method == 'POST':
                d = request.form
                cursor.execute("INSERT INTO books (title, author, category, stock, barcode) VALUES (%s,%s,%s,%s,%s)",
                               (d['title'], d['author'], d['category'], d['stock'], d['barcode']))
                conn.commit()
            cursor.execute("SELECT * FROM books")
            books = cursor.fetchall()
    finally:
        conn.close()
    return render_template('books.html', books=books)

@app.route('/edit_book', methods=['POST'])
def edit_book():
    d = request.form
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE books SET title=%s, author=%s, category=%s, stock=%s WHERE id=%s",
                           (d['title'], d['author'], d['category'], d['stock'], d['id']))
            conn.commit()
    finally:
        conn.close()
    return redirect(url_for('manage_books'))

@app.route('/delete_book/<int:id>')
def delete_book(id):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT title FROM books WHERE id=%s", (id,))
            book = cursor.fetchone()
            if book:
                cursor.execute("INSERT INTO logs (op_user, action) VALUES (%s, %s)",
                               ('管理员', f'删除了图书：{book["title"]}'))
            cursor.execute("DELETE FROM books WHERE id=%s", (id,))
            conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"删除失败: {e}")
    finally:
        conn.close()
    # 修正点：重定向到正确的函数名 manage_books
    return redirect(url_for('manage_books'))

# --- 3. 读者管理 ---
@app.route('/users', methods=['GET', 'POST'])
def manage_users():
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            if request.method == 'POST':
                d = request.form
                cursor.execute("INSERT INTO users (username, phone, reg_date) VALUES (%s,%s,CURDATE())",
                               (d['username'], d['phone']))
                conn.commit()
            cursor.execute("SELECT * FROM users")
            users = cursor.fetchall()
    finally:
        conn.close()
    return render_template('users.html', users=users)

@app.route('/edit_user', methods=['POST'])
def edit_user():
    d = request.form
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE users SET username=%s, phone=%s WHERE id=%s",
                           (d['username'], d['phone'], d['id']))
            conn.commit()
    finally:
        conn.close()
    return redirect(url_for('manage_users'))

# --- 4. 借还工作台 (含逾期费计算) ---
@app.route('/borrow')
def borrow_records():
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            # 获取当前逾期费率设置
            cursor.execute("SELECT overdue_rate FROM sys_settings WHERE id=1")
            rate_res = cursor.fetchone()
            daily_rate = float(rate_res['overdue_rate']) if rate_res else 0.5

            # 联表查询
            sql = """
                SELECT r.*, u.username, b.title 
                FROM records r
                JOIN users u ON r.user_id = u.id
                JOIN books b ON r.book_id = b.id
                ORDER BY r.status ASC, r.borrow_date DESC
            """
            cursor.execute(sql)
            records = cursor.fetchall()

            today = datetime.now().date()
            for r in records:
                # 核心：计算逾期和金额
                if r['status'] == '借出' and r['due_date'] and today > r['due_date']:
                    overdue_days = (today - r['due_date']).days
                    r['overdue_days'] = overdue_days
                    r['fine'] = round(overdue_days * daily_rate, 2)
                    r['is_overdue'] = True
                else:
                    r['overdue_days'] = 0
                    r['fine'] = 0.0
                    r['is_overdue'] = False
    finally:
        conn.close()
    return render_template('borrow.html', records=records)

@app.route('/api/borrow', methods=['POST'])
def api_borrow():
    user_id = request.form.get('user_id')
    barcode = request.form.get('barcode')
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
            if not cursor.fetchone(): return "读者不存在", 400

            cursor.execute("SELECT id, stock, title FROM books WHERE barcode = %s", (barcode,))
            book = cursor.fetchone()
            if not book or book['stock'] <= 0: return "书籍不存在或库存不足", 400

            # 插入借阅记录，DATE_ADD 确保了 due_date 不会为 None
            cursor.execute("""
                INSERT INTO records (user_id, book_id, borrow_date, due_date, status) 
                VALUES (%s, %s, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 30 DAY), '借出')
            """, (user_id, book['id']))

            cursor.execute("UPDATE books SET stock = stock - 1 WHERE id = %s", (book['id'],))
            cursor.execute("INSERT INTO logs (op_user, action) VALUES (%s, %s)",
                           ('管理员', f'借出：读者ID {user_id} 借阅了《{book["title"]}》'))
            conn.commit()
    finally:
        conn.close()
    return redirect(url_for('borrow_records'))

@app.route('/return_book/<int:record_id>')
def return_book(record_id):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT book_id FROM records WHERE id = %s", (record_id,))
            res = cursor.fetchone()
            if res:
                cursor.execute("UPDATE records SET status='已还', return_date=CURDATE() WHERE id=%s", (record_id,))
                cursor.execute("UPDATE books SET stock = stock + 1 WHERE id=%s", (res['book_id'],))
                conn.commit()
    finally:
        conn.close()
    return redirect(url_for('borrow_records'))

# --- 5. 系统设置与日志 ---
@app.route('/admin/settings', methods=['GET', 'POST'])
def admin_settings():
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            if request.method == 'POST':
                rate = request.form.get('rate')
                cursor.execute("UPDATE sys_settings SET overdue_rate=%s WHERE id=1", (rate,))
                conn.commit()
            cursor.execute("SELECT * FROM sys_settings WHERE id=1")
            config = cursor.fetchone()
    finally:
        conn.close()
    return render_template('admin_settings.html', config=config)

@app.route('/logs')
def view_logs():
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM logs ORDER BY op_time DESC LIMIT 50")
            logs = cursor.fetchall()
    finally:
        conn.close()
    return render_template('logs.html', logs=logs)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
