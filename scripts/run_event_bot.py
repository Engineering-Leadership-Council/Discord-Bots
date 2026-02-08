import asyncio
import os
import sys
import discord
from dotenv import load_dotenv

# Add parent directory to sys.path to allow imports from bots folder
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bots.event_bot import EventBot

# Load environment variables (from parent dir .env)
# We need to construct the path manually to ensure it loads the correct .env
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

async def run_event_bot():
    print("🤖 Starting Event Messenger Bot ONLY...")

    # Setup Intents (Although Client doesn't strictly need them as much to start, good practice)
    intents = discord.Intents.default()
    intents.members = True # Useful if we want to mention members later, though not critical for this version
    intents.message_content = True # Needed for !commands
    intents.guilds = True

    # Get Token
    event_token = os.getenv('EVENT_BOT_TOKEN')
    
    if not event_token:
        print("❌ Error: EVENT_BOT_TOKEN not found in .env")
        print("Please add 'EVENT_BOT_TOKEN=your_token' to your .env file.")
        return

    # Initialize Bot
    # Pass intents if the bot class expects them (it inherits from Client which takes intents)
    event_bot = EventBot(intents=intents)

    # Start
    try:
        await event_bot.start(event_token.strip())
    except discord.LoginFailure:
        print("❌ Error: Invalid Token. Please checking your .env file.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(run_event_bot())
    except KeyboardInterrupt:
        print("\n🛑 Stopping Event Bot...")
