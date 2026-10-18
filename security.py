import time
import secrets
from functools import wraps
from flask import request, session, abort, jsonify, redirect, url_for, flash
from config import Config

# IP-based rate limiting dictionary: {ip: [timestamps]}
rate_limits = {}

def get_client_ip():
    """Extracts client IP address safely"""
    if request.headers.getlist("X-Forwarded-For"):
        ip = request.headers.getlist("X-Forwarded-For")[0].split(',')[0].strip()
    else:
        ip = request.remote_addr or '127.0.0.1'
    return ip

def rate_limit(limit=60, window_seconds=60):
    """
    Decorator for limiting requests per client IP to prevent brute-force and DDoS
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            ip = get_client_ip()
            now = time.time()
            
            # Clean old records
            if ip not in rate_limits:
                rate_limits[ip] = []
            rate_limits[ip] = [t for t in rate_limits[ip] if now - t < window_seconds]
            
            if len(rate_limits[ip]) >= limit:
                if request.is_json:
                    return jsonify({
                        'status': False,
                        'message': 'คำขอถี่เกินไป เพื่อความปลอดภัยกรุณารอสักครู่ (Too Many Requests)'
                    }), 429
                return "คำขอถี่เกินไป เพื่อความปลอดภัยกรุณารอสักครู่ (429 Too Many Requests)", 429
                
            rate_limits[ip].append(now)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def generate_csrf_token():
    """Generates a secure CSRF token stored in session"""
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(32)
    return session['_csrf_token']

def validate_csrf():
    """Validates CSRF token from header or form data"""
    token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
    expected = session.get('_csrf_token')
    if not expected or not token or not secrets.compare_digest(token, expected):
        abort(403, description="CSRF Token verification failed (เซสชันหมดอายุหรือไม่ถูกต้อง)")

def admin_required(f):
    """Protects admin endpoints: ensures user is authenticated admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            if request.is_json:
                return jsonify({'status': False, 'message': 'ต้องเข้าสู่ระบบในฐานะผู้ดูแลระบบก่อน'}), 401
            flash('กรุณาเข้าสู่ระบบในฐานะผู้ดูแลระบบเพื่อดำเนินการ', 'warning')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def apply_security_headers(response):
    """Applies strict enterprise security headers to all HTTP responses"""
    # Prevent clickjacking
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    # Prevent MIME sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    # Enable XSS filtering
    response.headers['X-XSS-Protection'] = '1; mode=block'
    # Referrer policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    # Permissions policy
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    # Content Security Policy (allow Tailwind CDN, FontAwesome, Google Fonts, YouTube embeds for live stream)
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com https://cdn.tailwindcss.com; "
        "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
        "img-src 'self' data: https: https://www.glo.or.th https://api.glo.or.th; "
        "frame-src 'self' https://www.youtube.com https://www.youtube-nocookie.com; "
        "connect-src 'self' https://www.glo.or.th;"
    )
    return response
