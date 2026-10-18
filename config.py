import os
import secrets

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    
    # On Render (or similar), use /tmp for writable SQLite storage
    # Locally, use the project directory
    if os.environ.get('RENDER'):
        DATABASE_PATH = '/tmp/lottery.db'
    else:
        DATABASE_PATH = os.path.join(BASE_DIR, 'lottery.db')
    
    # GLO API Endpoints
    GLO_LATEST_URL = "https://www.glo.or.th/api/lottery/getLatestLottery"
    GLO_BY_DATE_URL = "https://www.glo.or.th/api/checking/getLotteryResult"
    GLO_CHECK_URL = "https://www.glo.or.th/api/checking/getcheckLotteryResult"
    
    # Security Settings
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 86400  # 1 day
    TEMPLATES_AUTO_RELOAD = True
    
    # Rate Limiting (in-memory)
    RATE_LIMIT_CHECK_PER_MINUTE = 60
    RATE_LIMIT_LOGIN_PER_MINUTE = 5
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 15
    
    # Site Info
    DEFAULT_SITE_TITLE = "นิยมตรวจหวยไทย"
    DEFAULT_ANNOUNCEMENT = "ตรวจผลสลากกินแบ่งรัฐบาลได้แม่นยำ 100% อัปเดตตรงจากสำนักงานสลากกินแบ่งรัฐบาล (GLO) ทุกงวดวันที่ 1 และ 16 ของเดือน"
