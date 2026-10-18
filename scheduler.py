import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from glo_service import fetch_latest_from_glo, sync_recent_historical_draws
from database import log_audit, get_settings

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()

def scheduled_glo_sync():
    """Routine sync job called on draw dates or regular intervals"""
    try:
        settings = get_settings()
        if settings.get('auto_sync_enabled') == '0':
            logger.info("Auto sync is currently disabled by Admin.")
            return

        logger.info("[SCHEDULER] Fetching latest lottery results from GLO...")
        ok, result = fetch_latest_from_glo()
        if ok:
            draw_date = result.get('date', 'Unknown')
            logger.info(f"[SCHEDULER] Successfully synced GLO draw for date: {draw_date}")
            log_audit("AUTO_SYNC_SUCCESS", "SYSTEM", f"Synced latest draw: {draw_date}")
        else:
            logger.warning(f"[SCHEDULER] Auto sync failed or not available yet: {result}")
            log_audit("AUTO_SYNC_NOTICE", "SYSTEM", f"Notice: {result}")
    except Exception as e:
        logger.error(f"[SCHEDULER] Error during auto sync: {e}")
        log_audit("AUTO_SYNC_ERROR", "SYSTEM", str(e))

def start_scheduler():
    """Configures and starts the background lottery update jobs"""
    if scheduler.running:
        return
        
    # 1. Sync on draw days (1st and 16th of every month) during drawing hours: 14:30, 15:00, 15:30, 16:00, 16:30, 17:00
    scheduler.add_job(
        scheduled_glo_sync,
        CronTrigger(day='1,16', hour='14,15,16,17', minute='0,30'),
        id='draw_day_sync',
        replace_existing=True,
        name="Draw Day Live Sync"
    )
    
    # 2. Daily check at 06:00 and 18:00
    scheduler.add_job(
        scheduled_glo_sync,
        CronTrigger(hour='6,18', minute='0'),
        id='daily_heartbeat_sync',
        replace_existing=True,
        name="Daily Heartbeat Sync"
    )
    
    scheduler.start()
    logger.info("[SCHEDULER] Lottery Background Scheduler started successfully.")
