import unittest
import json
import os
import shutil
from unittest.mock import MagicMock, AsyncMock, patch

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Create a dummy Client class to avoid MagicMock inheritance issues
class DummyClient:
    def __init__(self, *args, **kwargs):
        self.user = MagicMock()
        self.user.id = 123
        self.loop = MagicMock()

    def wait_until_ready(self):
        pass

    def is_closed(self):
        return False

mock_discord = MagicMock()
mock_discord.Client = DummyClient
mock_discord.Embed = MagicMock

# Mock discord before importing bot
with patch.dict('sys.modules', {'discord': mock_discord, 'bot_config': MagicMock()}):
    from bots.event_bot import EventBot

import asyncio

class TestEventDashboard(unittest.TestCase):
    def setUp(self):
        self.test_file = "events.json"
        # Create a dummy events file in OLD format (list)
        with open(self.test_file, 'w') as f:
            json.dump([{'name': 'Old Event', 'time': '2025-01-01 12:00', 'description': 'Legacy'}], f)

    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def test_migration_and_dashboard_update(self):
        # Initialize bot (should trigger migration)
        bot = EventBot()
        
        # Verify migration
        self.assertIsInstance(bot.data, dict)
        self.assertEqual(len(bot.events), 1)
        self.assertEqual(bot.events[0]['name'], 'Old Event')
        self.assertIsNone(bot.data['dashboard'])
        
        # Simulate !setup_dashboard
        bot.data['dashboard'] = {'channel_id': 123, 'message_id': 456}
        bot.get_channel = MagicMock()
        mock_channel = MagicMock()
        mock_message = AsyncMock()
        
        bot.get_channel.return_value = mock_channel
        mock_channel.fetch_message = AsyncMock(return_value=mock_message)
        
        # Run update_dashboard
        loop = asyncio.get_event_loop()
        loop.run_until_complete(bot.update_dashboard())
        
        # Verify message edit was called
        mock_message.edit.assert_called_once()
        print("Dashboard update verified!")

if __name__ == '__main__':
    unittest.main()
