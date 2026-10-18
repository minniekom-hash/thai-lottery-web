import os
import re
import json
import logging
from datetime import datetime
from flask import (
    Flask, render_template, request, jsonify, redirect, 
    url_for, session, flash, abort
)
from config import Config
from database import (
    init_db, get_latest_draw, get_draw_by_date, get_all_draw_dates,
    get_settings, update_setting, verify_admin_login, change_admin_password,
    get_audit_logs, log_audit
)
from glo_service import (
    fetch_latest_from_glo, fetch_draw_by_date_from_glo,
    check_ticket, sync_recent_historical_draws
)
from security import (
    rate_limit, generate_csrf_token, validate_csrf, admin_required,
    apply_security_headers, get_client_ip
)
from scheduler import start_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)

# Make CSRF token & settings available to all templates
@app.context_processor
def inject_global_data():
    return {
        'csrf_token': generate_csrf_token,
        'settings': get_settings(),
        'all_dates': get_all_draw_dates()
    }

# Apply security headers to every response
@app.after_request
def add_security_headers(response):
    return apply_security_headers(response)

# Helper: calculate next lottery draw date
def get_next_draw_info():
    now = datetime.now()
    year = now.year
    month = now.month
    day = now.day
    
    if day < 1:
        target = datetime(year, month, 1, 14, 30)
    elif day < 16:
        target = datetime(year, month, 16, 14, 30)
    else:
        # Next month 1st
        if month == 12:
            target = datetime(year + 1, 1, 1, 14, 30)
        else:
            target = datetime(year, month + 1, 1, 14, 30)
            
    diff = target - now
    days = diff.days
    hours = diff.seconds // 3600
    minutes = (diff.seconds % 3600) // 60
    return {
        'target_date': target.strftime('%Y-%m-%d'),
        'days': days,
        'hours': hours,
        'minutes': minutes
    }

# ==================== PUBLIC ROUTES ====================

@app.route('/')
def index():
    latest_draw = get_latest_draw()
    # If database is empty, automatically fetch latest from GLO right now
    if not latest_draw:
        ok, res = fetch_latest_from_glo()
        if ok:
            latest_draw = get_latest_draw()
            # Also backfill recent draws in background
            try:
                sync_recent_historical_draws(3)
            except Exception as e:
                logger.error(f"Backfill error: {e}")
                
    next_info = get_next_draw_info()
    return render_template('index.html', draw=latest_draw, next_info=next_info)

@app.route('/draw/<date_str>')
def view_draw(date_str):
    # Validate date format YYYY-MM-DD
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        flash('รูปแบบวันที่ไม่ถูกต้อง', 'error')
        return redirect(url_for('index'))
        
    draw = get_draw_by_date(date_str)
    if not draw:
        # Try fetching from GLO by date
        parts = date_str.split('-')
        ok, res = fetch_draw_by_date_from_glo(parts[2], parts[1], parts[0])
        if ok:
            draw = get_draw_by_date(date_str)
        else:
            flash(f'ไม่พบข้อมูลผลการออกรางวัลงวดวันที่ {date_str}', 'warning')
            return redirect(url_for('index'))
            
    next_info = get_next_draw_info()
    return render_template('index.html', draw=draw, next_info=next_info, selected_date=date_str)

@app.route('/history')
def history():
    dates = get_all_draw_dates()
    # Gather summary of each draw
    draws = []
    for d in dates:
        row = get_draw_by_date(d['draw_date'])
        if row:
            draws.append(row)
    return render_template('history.html', draws=draws)

@app.route('/check-multiple')
def check_multiple():
    latest_draw = get_latest_draw()
    all_dates = get_all_draw_dates()
    return render_template('check.html', latest_draw=latest_draw, all_dates=all_dates)

@app.route('/api/check', methods=['POST'])
@rate_limit(limit=Config.RATE_LIMIT_CHECK_PER_MINUTE, window_seconds=60)
def api_check():
    """
    Public checking API
    Accepts: {"date": "2026-10-16", "numbers": ["011781", "123456"]}
    """
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({'status': False, 'message': 'Invalid JSON body'}), 400
        
    date_str = data.get('date', '').strip()
    numbers = data.get('numbers', [])
    
    if not numbers or not isinstance(numbers, list):
        return jsonify({'status': False, 'message': 'กรุณาระบุหมายเลขสลากที่ต้องการตรวจ'}), 400
        
    # Limit max 50 numbers per request to prevent resource exhaustion
    if len(numbers) > 50:
        return jsonify({'status': False, 'message': 'สามารถตรวจได้สูงสุดครั้งละ 50 หมายเลข'}), 400
        
    # Get draw data
    if date_str:
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            return jsonify({'status': False, 'message': 'รูปแบบวันที่ไม่ถูกต้อง (YYYY-MM-DD)'}), 400
        draw = get_draw_by_date(date_str)
        if not draw:
            parts = date_str.split('-')
            ok, _ = fetch_draw_by_date_from_glo(parts[2], parts[1], parts[0])
            if ok:
                draw = get_draw_by_date(date_str)
    else:
        draw = get_latest_draw()
        
    if not draw:
        return jsonify({'status': False, 'message': 'ไม่พบข้อมูลผลรางวัลสำหรับงวดที่เลือก'}), 404
        
    results = []
    total_winning_amount = 0
    winner_count = 0
    
    for num in numbers:
        cleaned_num = str(num).strip()
        result = check_ticket(cleaned_num, draw)
        if result['is_winner']:
            winner_count += 1
            total_winning_amount += result['total_reward']
        results.append(result)
        
    return jsonify({
        'status': True,
        'draw_date': draw['draw_date'],
        'draw_date_thai': draw['draw_date_thai'],
        'first_prize': draw['first_prize'],
        'total_checked': len(numbers),
        'total_winning_tickets': winner_count,
        'total_reward_sum': total_winning_amount,
        'results': results
    })

# ==================== ADMIN ROUTES ====================

@app.route('/admin/login', methods=['GET', 'POST'])
@rate_limit(limit=Config.RATE_LIMIT_LOGIN_PER_MINUTE, window_seconds=60)
def admin_login():
    if session.get('is_admin'):
        return redirect(url_for('admin_dashboard'))
        
    if request.method == 'POST':
        validate_csrf()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        client_ip = get_client_ip()
        
        ok, msg = verify_admin_login(username, password, client_ip)
        if ok:
            session['is_admin'] = True
            session['admin_user'] = username
            flash(msg, 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash(msg, 'error')
            
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    user = session.get('admin_user', 'Unknown')
    log_audit("ADMIN_LOGOUT", get_client_ip(), f"Admin {user} logged out")
    session.clear()
    flash('ออกจากระบบสำเร็จแล้ว', 'info')
    return redirect(url_for('admin_login'))

@app.route('/admin')
@admin_required
def admin_dashboard():
    latest_draw = get_latest_draw()
    audit_logs = get_audit_logs(limit=25)
    all_draws = get_all_draw_dates()
    return render_template(
        'admin_dashboard.html',
        latest_draw=latest_draw,
        logs=audit_logs,
        draws_count=len(all_draws)
    )

@app.route('/admin/sync-glo', methods=['POST'])
@admin_required
def admin_sync_glo():
    validate_csrf()
    client_ip = get_client_ip()
    ok, result = fetch_latest_from_glo()
    if ok:
        log_audit("ADMIN_MANUAL_SYNC_SUCCESS", client_ip, f"Synced latest GLO draw: {result.get('date')}")
        flash(f"อัปเดตผลรางวัลจากสำนักงานสลากกินแบ่ง (GLO) สำเร็จ! (งวดวันที่ {result.get('date')})", 'success')
    else:
        log_audit("ADMIN_MANUAL_SYNC_FAIL", client_ip, str(result))
        flash(f"เกิดข้อผิดพลาดในการดึงข้อมูล: {result}", 'error')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/sync-history', methods=['POST'])
@admin_required
def admin_sync_history():
    validate_csrf()
    client_ip = get_client_ip()
    try:
        count = sync_recent_historical_draws(limit_months=6)
        log_audit("ADMIN_SYNC_HISTORY", client_ip, f"Backfilled {count} draws")
        flash(f"ดึงข้อมูลย้อนหลังจาก GLO สำเร็จเรียบร้อยแล้ว เพิ่มงวดใหม่ {count} งวด!", 'success')
    except Exception as e:
        log_audit("ADMIN_SYNC_HISTORY_FAIL", client_ip, str(e))
        flash(f"เกิดข้อผิดพลาดในการดึงผลงวดย้อนหลัง: {e}", 'error')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/settings', methods=['POST'])
@admin_required
def admin_update_settings():
    validate_csrf()
    client_ip = get_client_ip()
    
    title = request.form.get('site_title', '').strip()
    announcement = request.form.get('announcement_text', '').strip()
    announcement_active = '1' if request.form.get('announcement_active') else '0'
    auto_sync_enabled = '1' if request.form.get('auto_sync_enabled') else '0'
    
    if title:
        update_setting('site_title', title)
    update_setting('announcement_text', announcement)
    update_setting('announcement_active', announcement_active)
    update_setting('auto_sync_enabled', auto_sync_enabled)
    
    log_audit("ADMIN_UPDATE_SETTINGS", client_ip, "Updated website title and announcement settings")
    flash('บันทึกการตั้งค่าเว็บไซต์สำเร็จเรียบร้อยแล้ว', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/change-password', methods=['POST'])
@admin_required
def admin_change_password():
    validate_csrf()
    client_ip = get_client_ip()
    
    current_pass = request.form.get('current_password', '')
    new_pass = request.form.get('new_password', '')
    confirm_pass = request.form.get('confirm_password', '')
    
    if new_pass != confirm_pass:
        flash('รหัสผ่านใหม่และการยืนยันรหัสผ่านไม่ตรงกัน', 'error')
        return redirect(url_for('admin_dashboard'))
        
    username = session.get('admin_user', 'admin')
    ok, msg = change_admin_password(username, current_pass, new_pass, client_ip)
    if ok:
        flash(msg, 'success')
    else:
        flash(msg, 'error')
    return redirect(url_for('admin_dashboard'))

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('base.html', not_found=True), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return "เกิดข้อผิดพลาดภายในระบบ กรุณาลองใหม่อีกครั้งในภายหลัง", 500

# Initialize Database and Scheduler on startup
try:
    init_db()
except Exception as e:
    logger.error(f"Database init error: {e}")

# Only start scheduler in main process (avoid duplicate with gunicorn workers)
import os
if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not os.environ.get('GUNICORN_ARBITER'):
    try:
        start_scheduler()
    except Exception as e:
        logger.error(f"Scheduler init error: {e}")

if __name__ == '__main__':
    # Start local server on port 5000
    app.run(host='0.0.0.0', port=5000, debug=False)
