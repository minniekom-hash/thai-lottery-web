import requests
import json
import logging
from datetime import datetime
from config import Config
from database import save_lottery_draw, get_latest_draw, get_draw_by_date, log_audit

logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Content-Type': 'application/json',
    'Accept': 'application/json, text/plain, */*'
}

def fetch_latest_from_glo():
    """Fetches the latest lottery result directly from the official GLO API"""
    try:
        response = requests.post(Config.GLO_LATEST_URL, json={}, headers=HEADERS, timeout=12)
        if response.status_code == 200:
            res_data = response.json()
            if res_data.get('status') and 'response' in res_data:
                lottery_data = res_data['response']
                save_lottery_draw(lottery_data)
                return True, lottery_data
            else:
                return False, f"GLO API returned status false: {res_data.get('statusMessage')}"
        return False, f"GLO API HTTP Error {response.status_code}"
    except Exception as e:
        logger.error(f"Error fetching latest from GLO: {e}")
        return False, str(e)

def fetch_draw_by_date_from_glo(day, month, year):
    """
    Fetches lottery result by specific date (day: '01'/'16', month: '01'-'12', year: '2026')
    """
    try:
        payload = {
            "date": str(day).zfill(2),
            "month": str(month).zfill(2),
            "year": str(year)
        }
        response = requests.post(Config.GLO_BY_DATE_URL, json=payload, headers=HEADERS, timeout=12)
        if response.status_code == 200:
            res_data = response.json()
            result_obj = res_data.get('response', {}).get('result')
            if result_obj and result_obj.get('data'):
                # Ensure date field is present
                if not result_obj.get('date'):
                    result_obj['date'] = f"{year}-{str(month).zfill(2)}-{str(day).zfill(2)}"
                save_lottery_draw(result_obj)
                return True, result_obj
            else:
                return False, "ไม่พบข้อมูลผลการออกรางวัลของงวดนี้"
        return False, f"GLO API HTTP {response.status_code}"
    except Exception as e:
        logger.error(f"Error fetching date {year}-{month}-{day} from GLO: {e}")
        return False, str(e)

def check_ticket(number_str, draw_dict):
    """
    Accurately checks a 6-digit ticket against all prize categories in the draw.
    Returns: {
        'number': '123456',
        'is_winner': True/False,
        'prizes': [
            {'name': 'รางวัลที่ 1', 'prize_per_ticket': 6000000, 'description': 'เลขตรงทั้ง 6 ตัว'}
        ],
        'total_reward': 6000000
    }
    """
    num = str(number_str).strip()
    if len(num) != 6 or not num.isdigit():
        return {
            'number': num,
            'is_winner': False,
            'prizes': [],
            'total_reward': 0,
            'error': 'หมายเลขสลากต้องเป็นตัวเลข 6 หลักเท่านั้น'
        }
        
    prizes_won = []
    total_reward = 0
    
    # 1. รางวัลที่ 1 (6,000,000 บาท)
    first_prize = draw_dict.get('first_prize', '')
    if num == first_prize:
        reward = int(draw_dict.get('first_price', 6000000))
        prizes_won.append({
            'name': 'รางวัลที่ 1',
            'reward': reward,
            'detail': f'เลขตรงกับรางวัลที่ 1 ({first_prize})'
        })
        total_reward += reward
        
    # 2. รางวัลข้างเคียงรางวัลที่ 1 (100,000 บาท)
    near1_list = draw_dict.get('near1', [])
    if num in near1_list:
        prizes_won.append({
            'name': 'รางวัลข้างเคียงรางวัลที่ 1',
            'reward': 100000,
            'detail': f'เลขตรงกับรางวัลข้างเคียงรางวัลที่ 1'
        })
        total_reward += 100000
        
    # 3. รางวัลที่ 2 (200,000 บาท)
    second_list = draw_dict.get('second', [])
    if num in second_list:
        prizes_won.append({
            'name': 'รางวัลที่ 2',
            'reward': 200000,
            'detail': 'เลขตรงกับรางวัลที่ 2'
        })
        total_reward += 200000

    # 4. รางวัลที่ 3 (80,000 บาท)
    third_list = draw_dict.get('third', [])
    if num in third_list:
        prizes_won.append({
            'name': 'รางวัลที่ 3',
            'reward': 80000,
            'detail': 'เลขตรงกับรางวัลที่ 3'
        })
        total_reward += 80000

    # 5. รางวัลที่ 4 (40,000 บาท)
    fourth_list = draw_dict.get('fourth', [])
    if num in fourth_list:
        prizes_won.append({
            'name': 'รางวัลที่ 4',
            'reward': 40000,
            'detail': 'เลขตรงกับรางวัลที่ 4'
        })
        total_reward += 40000

    # 6. รางวัลที่ 5 (20,000 บาท)
    fifth_list = draw_dict.get('fifth', [])
    if num in fifth_list:
        prizes_won.append({
            'name': 'รางวัลที่ 5',
            'reward': 20000,
            'detail': 'เลขตรงกับรางวัลที่ 5'
        })
        total_reward += 20000

    # 7. รางวัลเลขหน้า 3 ตัว (4,000 บาท ต่อรางวัล)
    front3 = num[:3]
    last3f_list = draw_dict.get('last3f', [])
    matches_3f = last3f_list.count(front3)
    if matches_3f > 0:
        reward = 4000 * matches_3f
        prizes_won.append({
            'name': 'รางวัลเลขหน้า 3 ตัว',
            'reward': reward,
            'detail': f'เลข 3 ตัวหน้า ({front3}) ตรงกับรางวัลเลขหน้า 3 ตัว'
        })
        total_reward += reward

    # 8. รางวัลเลขท้าย 3 ตัว (4,000 บาท ต่อรางวัล)
    back3 = num[3:]
    last3b_list = draw_dict.get('last3b', [])
    matches_3b = last3b_list.count(back3)
    if matches_3b > 0:
        reward = 4000 * matches_3b
        prizes_won.append({
            'name': 'รางวัลเลขท้าย 3 ตัว',
            'reward': reward,
            'detail': f'เลข 3 ตัวท้าย ({back3}) ตรงกับรางวัลเลขท้าย 3 ตัว'
        })
        total_reward += reward

    # 9. รางวัลเลขท้าย 2 ตัว (2,000 บาท)
    back2 = num[4:]
    last2 = draw_dict.get('last2', '')
    if back2 == last2:
        prizes_won.append({
            'name': 'รางวัลเลขท้าย 2 ตัว',
            'reward': 2000,
            'detail': f'เลข 2 ตัวท้าย ({back2}) ตรงกับรางวัลเลขท้าย 2 ตัว'
        })
        total_reward += 2000

    return {
        'number': num,
        'is_winner': len(prizes_won) > 0,
        'prizes': prizes_won,
        'total_reward': total_reward
    }

def sync_recent_historical_draws(limit_months=6):
    """
    Backfills recent lottery draws into the database
    """
    now = datetime.now()
    curr_year = now.year
    curr_month = now.month
    
    count_success = 0
    # Walk backwards month by month
    for i in range(limit_months):
        m = curr_month - i
        y = curr_year
        while m <= 0:
            m += 12
            y -= 1
            
        for day in [16, 1]:
            # If in future, skip
            draw_dt = datetime(y, m, day)
            if draw_dt > now:
                continue
                
            date_key = f"{y}-{str(m).zfill(2)}-{str(day).zfill(2)}"
            existing = get_draw_by_date(date_key)
            if existing:
                continue
                
            ok, _ = fetch_draw_by_date_from_glo(day, m, y)
            if ok:
                count_success += 1
                
    return count_success
