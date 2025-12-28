-- 1. 创建并使用数据库
DROP DATABASE IF EXISTS library_db;
CREATE DATABASE library_db DEFAULT CHARACTER SET utf8mb4;
USE library_db;

-- 2. 系统参数配置表 (控制全馆借阅规则)
CREATE TABLE sys_settings (
    id INT PRIMARY KEY DEFAULT 1,
    overdue_rate DECIMAL(10, 2) DEFAULT 0.50, -- 每天罚款金额
    max_borrow_days INT DEFAULT 30,           -- 默认借阅期限
    max_books INT DEFAULT 5                   -- 单人最大借阅数
);
-- 初始化一条配置数据
INSERT INTO sys_settings (id, overdue_rate, max_borrow_days, max_books) VALUES (1, 0.50, 30, 5);

-- 3. 书籍信息表 (编目与典藏)
CREATE TABLE books (
    id INT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(100) NOT NULL,
    author VARCHAR(100),
    category VARCHAR(50),
    stock INT DEFAULT 1,
    price DECIMAL(10, 2),
    barcode VARCHAR(50) UNIQUE,               -- 图书唯一条码
    location VARCHAR(50) DEFAULT '流通部二楼',  -- 馆藏地点
    status VARCHAR(20) DEFAULT '在馆'          -- 状态：在馆/借出/丢失/损毁/维修
);

-- 4. 读者会员表
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL,
    phone VARCHAR(20),
    reg_date DATE
);

-- 5. 借阅记录表 (流通管理核心)
CREATE TABLE records (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT,
    book_id INT,
    borrow_date DATE,
    due_date DATE,                            -- 应还日期
    return_date DATE,                         -- 实际归还日期
    status VARCHAR(20) DEFAULT '借出',         -- 状态：借出/已还
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
);

-- 6. 罚款处理表
CREATE TABLE fines (
    id INT PRIMARY KEY AUTO_INCREMENT,
    record_id INT,
    amount DECIMAL(10, 2),
    is_paid BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (record_id) REFERENCES records(id)
);

-- 7. 系统操作日志表
CREATE TABLE logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    op_user VARCHAR(50),
    action VARCHAR(255),
    op_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8. 插入演示数据 (方便你直接演示)
INSERT INTO books (title, author, category, stock, price, barcode, location) VALUES 
('三体：全集', '刘慈欣', '科幻', 10, 198.0, '69001', '科幻阅览室A1'),
('Python核心编程', 'Wesley', '计算机', 5, 89.0, '69002', '技术中心B2'),
('活着', '余华', '文学', 8, 35.0, '69003', '文学书库C1');

INSERT INTO users (username, phone, reg_date) VALUES 
('张三', '13800138000', CURDATE()),
('李四', '13911223344', CURDATE());

-- 模拟一条借阅记录（为了演示逾期，设一个过去的日期）
INSERT INTO records (user_id, book_id, borrow_date, due_date, status) VALUES 
(1, 1, '2025-11-01', '2025-12-01', '借出');

INSERT INTO logs (op_user, action) VALUES ('系统', '初始化数据库成功');