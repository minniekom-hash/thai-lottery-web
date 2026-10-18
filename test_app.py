import unittest
import json
from app import app
from database import init_db, get_latest_draw, verify_admin_login, get_settings
from glo_service import fetch_latest_from_glo, check_ticket

class TestLotteryApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        # Ensure we have at least one draw
        ok, res = fetch_latest_from_glo()
        print("Initial GLO fetch ok:", ok)

    def setUp(self):
        self.client = app.test_client()

    def test_database_and_latest_draw(self):
        draw = get_latest_draw()
        self.assertIsNotNone(draw, "Latest draw should exist in DB")
        self.assertTrue(len(draw['first_prize']) == 6, "First prize should be 6 digits")
        print(f"Latest draw date: {draw['draw_date']}, First prize: {draw['first_prize']}")

    def test_ticket_checking_logic(self):
        draw = get_latest_draw()
        
        # Test 1st prize
        res1 = check_ticket(draw['first_prize'], draw)
        self.assertTrue(res1['is_winner'])
        self.assertGreaterEqual(res1['total_reward'], 6000000)
        print("Ticket check 1st prize:", res1['prizes'][0]['name'], res1['total_reward'])
        
        # Test 2-digit back prize
        last2 = draw['last2']
        dummy_num = f"9999{last2}"
        res2 = check_ticket(dummy_num, draw)
        self.assertTrue(res2['is_winner'])
        names = [p['name'] for p in res2['prizes']]
        self.assertIn('รางวัลเลขท้าย 2 ตัว', names)
        print("Ticket check last2 prize:", names, res2['total_reward'])
        
        # Test non-winning dummy ticket (or very unlikely to win)
        res_none = check_ticket("000000", draw)
        print("Ticket check 000000 won?", res_none['is_winner'], res_none['total_reward'])

    def test_api_check_endpoint(self):
        draw = get_latest_draw()
        response = self.client.post('/api/check', 
            data=json.dumps({
                'date': draw['draw_date'],
                'numbers': [draw['first_prize'], '999999']
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['status'])
        self.assertEqual(data['total_checked'], 2)
        print("API Check response status:", data['status'], "Winning count:", data['total_winning_tickets'])

    def test_home_page_renders(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('ผลสลากกินแบ่งรัฐบาลไทย'.encode('utf-8'), response.data)
        # Check security headers
        self.assertEqual(response.headers.get('X-Frame-Options'), 'SAMEORIGIN')
        self.assertEqual(response.headers.get('X-Content-Type-Options'), 'nosniff')

    def test_admin_auth(self):
        # Correct password
        ok, msg = verify_admin_login('admin', 'Admin@Lottery#2026', '127.0.0.1')
        self.assertTrue(ok)
        
        # Wrong password
        ok_wrong, msg_wrong = verify_admin_login('admin', 'WrongPass123', '127.0.0.1')
        self.assertFalse(ok_wrong)
        print("Admin login verification test passed.")

if __name__ == '__main__':
    unittest.main()
