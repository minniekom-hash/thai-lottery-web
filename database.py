import sqlite3
import json
import os
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config

THAI_MONTHS = [
    "", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
]

def format_thai_date(date_str):
    """Convert YYYY-MM-DD to Thai Date e.g. 16 ตุลาคม 2569"""
    try:
        parts = date_str.split('-')
        year = int(parts[0]) + 543
        month = THAI_MONTHS[int(parts[1])]
        day = int(parts[2])
        return f"{day} {month} {year}"
    except Exception:
        return date_str

def get_db_connection():
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Lottery Draws table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lottery_draws (
            draw_date TEXT PRIMARY KEY,
            draw_date_thai TEXT,
            youtube_url TEXT,
            pdf_url TEXT,
            status INTEGER DEFAULT 1,
            first_prize TEXT,
            first_price REAL DEFAULT 6000000.0,
            near1_json TEXT,
            second_json TEXT,
            third_json TEXT,
            fourth_json TEXT,
            fifth_json TEXT,
            last2 TEXT,
            last3f_json TEXT,
            last3b_json TEXT,
            raw_data_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 2. Site Settings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS site_settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 3. Admin Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            failed_attempts INTEGER DEFAULT 0,
            locked_until TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    
    # 4. Audit Logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            ip_address TEXT,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Set default settings if not exists
    cursor.execute('SELECT COUNT(*) FROM site_settings WHERE key = ?', ('site_title',))
    if cursor.fetchone()[0] == 0:
        cursor.execute('INSERT INTO site_settings (key, value) VALUES (?, ?)', ('site_title', Config.DEFAULT_SITE_TITLE))
        cursor.execute('INSERT INTO site_settings (key, value) VALUES (?, ?)', ('announcement_text', Config.DEFAULT_ANNOUNCEMENT))
        cursor.execute('INSERT INTO site_settings (key, value) VALUES (?, ?)', ('announcement_active', '1'))
        cursor.execute('INSERT INTO site_settings (key, value) VALUES (?, ?)', ('auto_sync_enabled', '1'))
    
    # Create initial admin user if not exists (username: admin, initial password: adminLottery2026!)
    cursor.execute('SELECT COUNT(*) FROM admin_users')
    if cursor.fetchone()[0] == 0:
        default_pass = 'Admin@Lottery#2026'
        hashed = generate_password_hash(default_pass)
        cursor.execute('INSERT INTO admin_users (username, password_hash) VALUES (?, ?)', ('admin', hashed))
        print(f"[SECURITY] Initial Admin account created: username='admin', password='{default_pass}'")
    
    conn.commit()
    conn.close()

def save_lottery_draw(glo_response_data):
    """
    Parse and save/update GLO response dictionary into lottery_draws
    """
    if not glo_response_data:
        return False
        
    date_str = glo_response_data.get('date')
    if not date_str:
        return False
        
    date_thai = format_thai_date(date_str)
    youtube_url = glo_response_data.get('youtube_url', '')
    pdf_url = glo_response_data.get('pdf_url', '')
    status = glo_response_data.get('status', 1)
    
    prizes = glo_response_data.get('data', {})
    
    # Extract First Prize
    first_data = prizes.get('first', {})
    first_prize = ""
    first_price = 6000000.0
    if first_data.get('number'):
        first_prize = str(first_data['number'][0].get('value', '')).strip()
        first_price = float(first_data.get('price', 6000000.0))
        
    # Helper to extract list of numbers
    def extract_numbers(prize_dict):
        numbers = []
        if prize_dict and 'number' in prize_dict:
            for item in prize_dict['number']:
                val = str(item.get('value', '')).strip()
                if val:
                    numbers.append(val)
        return numbers

    near1 = extract_numbers(prizes.get('near1', {}))
    second = extract_numbers(prizes.get('second', {}))
    third = extract_numbers(prizes.get('third', {}))
    fourth = extract_numbers(prizes.get('fourth', {}))
    fifth = extract_numbers(prizes.get('fifth', {}))
    
    # Last 2 digits
    last2_list = extract_numbers(prizes.get('last2', {}))
    last2 = last2_list[0] if last2_list else ""
    
    # Last 3 front & back
    last3f = extract_numbers(prizes.get('last3f', {}))
    last3b = extract_numbers(prizes.get('last3b', {}))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO lottery_draws (
            draw_date, draw_date_thai, youtube_url, pdf_url, status,
            first_prize, first_price, near1_json, second_json, third_json,
            fourth_json, fifth_json, last2, last3f_json, last3b_json,
            raw_data_json, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(draw_date) DO UPDATE SET
            draw_date_thai = excluded.draw_date_thai,
            youtube_url = excluded.youtube_url,
            pdf_url = excluded.pdf_url,
            status = excluded.status,
            first_prize = excluded.first_prize,
            first_price = excluded.first_price,
            near1_json = excluded.near1_json,
            second_json = excluded.second_json,
            third_json = excluded.third_json,
            fourth_json = excluded.fourth_json,
            fifth_json = excluded.fifth_json,
            last2 = excluded.last2,
            last3f_json = excluded.last3f_json,
            last3b_json = excluded.last3b_json,
            raw_data_json = excluded.raw_data_json,
            updated_at = CURRENT_TIMESTAMP
    ''', (
        date_str, date_thai, youtube_url, pdf_url, status,
        first_prize, first_price,
        json.dumps(near1, ensure_ascii=False),
        json.dumps(second, ensure_ascii=False),
        json.dumps(third, ensure_ascii=False),
        json.dumps(fourth, ensure_ascii=False),
        json.dumps(fifth, ensure_ascii=False),
        last2,
        json.dumps(last3f, ensure_ascii=False),
        json.dumps(last3b, ensure_ascii=False),
        json.dumps(glo_response_data, ensure_ascii=False)
    ))
    
    conn.commit()
    conn.close()
    return True

def get_latest_draw():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM lottery_draws ORDER BY draw_date DESC LIMIT 1')
    row = cursor.fetchone()
    conn.close()
    if row:
        return parse_draw_row(dict(row))
    return None

def get_draw_by_date(date_str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM lottery_draws WHERE draw_date = ?', (date_str,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return parse_draw_row(dict(row))
    return None

def get_all_draw_dates():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT draw_date, draw_date_thai FROM lottery_draws ORDER BY draw_date DESC')
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def parse_draw_row(d):
    """Decodes JSON fields into python lists"""
    for field in ['near1_json', 'second_json', 'third_json', 'fourth_json', 'fifth_json', 'last3f_json', 'last3b_json']:
        key = field.replace('_json', '')
        raw = d.get(field)
        d[key] = json.loads(raw) if raw else []
    return d

def get_settings():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT key, value FROM site_settings')
    rows = cursor.fetchall()
    conn.close()
    return {r['key']: r['value'] for r in rows}

def update_setting(key, value):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO site_settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
    ''', (key, value))
    conn.commit()
    conn.close()

def log_audit(action, ip_address, details=""):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO audit_logs (action, ip_address, details) VALUES (?, ?, ?)', (action, ip_address, details))
    conn.commit()
    conn.close()

def get_audit_logs(limit=50):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT ?', (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def verify_admin_login(username, password, client_ip):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM admin_users WHERE username = ?', (username,))
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        log_audit("FAILED_LOGIN", client_ip, f"Invalid username attempt: {username}")
        return False, "ชื่อผู้ใช้งานหรือรหัสผ่านไม่ถูกต้อง"
        
    user = dict(user)
    
    # Check account lockout
    if user['locked_until']:
        locked_until = datetime.strptime(user['locked_until'], '%Y-%m-%d %H:%M:%S')
        if datetime.now() < locked_until:
            rem = int((locked_until - datetime.now()).total_seconds() / 60) + 1
            conn.close()
            log_audit("BLOCKED_LOGIN_ATTEMPT", client_ip, f"Account locked for {username}")
            return False, f"บัญชีถูกระงับชั่วคราวเนื่องจากใส่รหัสผ่านผิดเกินกำหนด กรุณารออีก {rem} นาที"
            
    # Verify password
    if check_password_hash(user['password_hash'], password):
        # Reset failed attempts and set last login
        cursor.execute('''
            UPDATE admin_users SET failed_attempts = 0, locked_until = NULL, last_login = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (user['id'],))
        conn.commit()
        conn.close()
        log_audit("ADMIN_LOGIN_SUCCESS", client_ip, f"Admin {username} logged in successfully")
        return True, "เข้าสู่ระบบสำเร็จ"
    else:
        # Increment failed attempts
        failed = user['failed_attempts'] + 1
        lock_time = None
        msg = "ชื่อผู้ใช้งานหรือรหัสผ่านไม่ถูกต้อง"
        if failed >= Config.MAX_LOGIN_ATTEMPTS:
            lock_until_dt = datetime.now() + timedelta(minutes=Config.LOCKOUT_DURATION_MINUTES)
            lock_time = lock_until_dt.strftime('%Y-%m-%d %H:%M:%S')
            msg = f"รหัสผ่านผิดเกิน 5 ครั้ง ระบบทำการล็อกบัญชีเป็นเวลา {Config.LOCKOUT_DURATION_MINUTES} นาที"
            
        cursor.execute('''
            UPDATE admin_users SET failed_attempts = ?, locked_until = ? WHERE id = ?
        ''', (failed, lock_time, user['id']))
        conn.commit()
        conn.close()
        log_audit("FAILED_PASSWORD", client_ip, f"Wrong password attempt {failed} for {username}")
        return False, msg

def change_admin_password(username, current_password, new_password, client_ip):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM admin_users WHERE username = ?', (username,))
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        return False, "ไม่พบบัญชีผู้ดูแลระบบ"
        
    user = dict(user)
    if not check_password_hash(user['password_hash'], current_password):
        conn.close()
        log_audit("PASSWORD_CHANGE_FAILED", client_ip, "Current password incorrect")
        return False, "รหัสผ่านปัจจุบันไม่ถูกต้อง"
        
    if len(new_password) < 8:
        conn.close()
        return False, "รหัสผ่านใหม่ต้องมีความยาวอย่างน้อย 8 ตัวอักษร"
        
    new_hash = generate_password_hash(new_password)
    cursor.execute('UPDATE admin_users SET password_hash = ? WHERE id = ?', (new_hash, user['id']))
    conn.commit()
    conn.close()
    log_audit("PASSWORD_CHANGE_SUCCESS", client_ip, f"Admin {username} changed password")
    return True, "เปลี่ยนรหัสผ่านสำเร็จเรียบร้อยแล้ว"
