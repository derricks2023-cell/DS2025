from flask import Flask, render_template, request, redirect, url_for, jsonify
import pymysql
from datetime import datetime, date

app = Flask(__name__)

# 数据库连接配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'NewStrongPassword123!', # <-- 记得改这里
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
    with conn.cursor() as cursor:
        cursor.execute("SELECT category, SUM(stock) as count FROM books GROUP BY category")
        chart_data = cursor.fetchall()
        cursor.execute("SELECT COUNT(*) as total FROM books")
        total_books = cursor.fetchone()['total']
        cursor.execute("SELECT COUNT(*) as total FROM records WHERE status='借出'")
        total_borrows = cursor.fetchone()['total']
    conn.close()
    return render_template('index.html', chart_data=chart_data, total_books=total_books, total_borrows=total_borrows)

# --- 2. 图书管理 (含编辑) ---
@app.route('/books', methods=['GET', 'POST'])
def manage_books():
    conn = get_db()
    with conn.cursor() as cursor:
        if request.method == 'POST':
            d = request.form
            cursor.execute("INSERT INTO books (title, author, category, stock, barcode) VALUES (%s,%s,%s,%s,%s)",
                           (d['title'], d['author'], d['category'], d['stock'], d['barcode']))
            conn.commit()
        cursor.execute("SELECT * FROM books")
        books = cursor.fetchall()
    conn.close()
    return render_template('books.html', books=books)

@app.route('/edit_book', methods=['POST'])
def edit_book():
    d = request.form
    conn = get_db()
    with conn.cursor() as cursor:
        cursor.execute("UPDATE books SET title=%s, author=%s, category=%s, stock=%s WHERE id=%s",
                       (d['title'], d['author'], d['category'], d['stock'], d['id']))
        conn.commit()
    conn.close()
    return redirect(url_for('manage_books'))

# --- 3. 读者管理 (含编辑) ---
@app.route('/users', methods=['GET', 'POST'])
def manage_users():
    conn = get_db()
    with conn.cursor() as cursor:
        if request.method == 'POST':
            d = request.form
            cursor.execute("INSERT INTO users (username, phone, reg_date) VALUES (%s,%s,CURDATE())",
                           (d['username'], d['phone']))
            conn.commit()
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()
    conn.close()
    return render_template('users.html', users=users)

@app.route('/edit_user', methods=['POST'])
def edit_user():
    d = request.form
    conn = get_db()
    with conn.cursor() as cursor:
        cursor.execute("UPDATE users SET username=%s, phone=%s WHERE id=%s",
                       (d['username'], d['phone'], d['id']))
        conn.commit()
    conn.close()
    return redirect(url_for('manage_users'))

# --- 4. 借还工作台 (解决 overdue_days 报错) ---
@app.route('/borrow')
def borrow_records():
    conn = get_db()
    with conn.cursor() as cursor:
        # 使用 CASE 确保 overdue_days 始终存在且为数字
        sql = """
            SELECT r.*, u.username, b.title, 
            CASE 
                WHEN r.status = '借出' AND CURDATE() > r.due_date THEN DATEDIFF(CURDATE(), r.due_date)
                ELSE 0 
            END as overdue_days
            FROM records r
            JOIN users u ON r.user_id = u.id
            JOIN books b ON r.book_id = b.id
            ORDER BY r.status ASC, r.borrow_date DESC
        """
        cursor.execute(sql)
        records = cursor.fetchall()
    conn.close()
    return render_template('borrow.html', records=records)


# --- 归还书籍处理逻辑 ---
@app.route('/return_book/<int:record_id>')
def return_book(record_id):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            # 1. 先查出这条记录对应的 book_id
            cursor.execute("SELECT book_id FROM records WHERE id = %s", (record_id,))
            record = cursor.fetchone()

            if record:
                book_id = record['book_id']

                # 2. 更新借阅记录状态为“已还”，并记录归还日期
                cursor.execute("""
                    UPDATE records 
                    SET status = '已还', return_date = CURDATE() 
                    WHERE id = %s
                """, (record_id,))

                # 3. 将书籍状态改回“在馆”
                cursor.execute("UPDATE books SET status = '在馆' WHERE id = %s", (book_id,))

                # 4. 写入系统日志
                cursor.execute("""
                    INSERT INTO logs (op_user, action, op_time) 
                    VALUES (%s, %s, NOW())
                """, ('系统管理员', f'归还确认：记录ID {record_id}，书籍ID {book_id}'))

                conn.commit()
    except Exception as e:
        print(f"归还操作失败: {e}")
        conn.rollback()
    finally:
        conn.close()

    # 操作完成后，重定向回借还工作台
    return redirect(url_for('borrow_records'))


# --- 借书处理逻辑 ---
@app.route('/api/borrow', methods=['POST'])
def api_borrow():
    # 获取表单提交的数据
    user_id = request.form.get('user_id')
    barcode = request.form.get('barcode')

    conn = get_db()
    try:
        with conn.cursor() as cursor:
            # 1. 验证读者是否存在
            cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            if not user:
                return "错误：读者ID不存在", 400

            # 2. 验证书籍是否存在且有库存
            cursor.execute("SELECT id, stock, title FROM books WHERE barcode = %s", (barcode,))
            book = cursor.fetchone()
            if not book or book['stock'] <= 0:
                return "错误：书籍不存在或库存不足", 400

            # 3. 创建借阅记录 (默认借期30天)
            # 自动计算应还日期：今天 + 30天
            cursor.execute("""
                INSERT INTO records (user_id, book_id, borrow_date, due_date, status) 
                VALUES (%s, %s, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 30 DAY), '借出')
            """, (user_id, book['id']))

            # 4. 扣减书籍库存
            cursor.execute("UPDATE books SET stock = stock - 1 WHERE id = %s", (book['id'],))

            # 5. 记录系统日志
            cursor.execute("""
                INSERT INTO logs (op_user, action, op_time) 
                VALUES (%s, %s, NOW())
            """, ('管理员', f'借出登记：读者ID {user_id} 借阅了《{book["title"]}》'))

            conn.commit()
    except Exception as e:
        print(f"借书失败: {e}")
        conn.rollback()
        return "数据库操作失败", 500
    finally:
        conn.close()

    # 借书成功后跳回工作台
    return redirect(url_for('borrow_records'))

# --- 5. 系统参数设置 (解决 404) ---
@app.route('/admin/settings', methods=['GET', 'POST'])
def admin_settings():
    conn = get_db()
    with conn.cursor() as cursor:
        if request.method == 'POST':
            rate = request.form.get('rate')
            cursor.execute("UPDATE sys_settings SET overdue_rate=%s WHERE id=1", (rate,))
            conn.commit()
        cursor.execute("SELECT * FROM sys_settings WHERE id=1")
        config = cursor.fetchone()
    conn.close()
    return render_template('admin_settings.html', config=config)

# --- 6. 系统操作日志 (解决 404) ---
@app.route('/logs')
def view_logs():
    conn = get_db()
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM logs ORDER BY op_time DESC LIMIT 50")
        logs = cursor.fetchall()
    conn.close()
    return render_template('logs.html', logs=logs)

if __name__ == '__main__':
    app.run(debug=True, port=5000)