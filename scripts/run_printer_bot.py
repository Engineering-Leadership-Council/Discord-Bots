import asyncio
import os
import sys
import discord
from dotenv import load_dotenv

# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bots.printer_bot import PrinterBot

# Load env
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

async def run_printer_bot():
    print("🤖 Starting 3D Print Observer ONLY...")
    
    intents = discord.Intents.default()
    # messages content needed if we ever listen for commands, but for now it's mostly outbound.
    intents.message_content = True 

    token = os.getenv('PRINTER_OBSERVER_TOKEN')
    if not token:
        print("❌ Error: PRINTER_OBSERVER_TOKEN not found in .env")
        return

    bot = PrinterBot(intents=intents)

    try:
        await bot.start(token)
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(run_printer_bot())
    except KeyboardInterrupt:
        print("\n🛑 Stopping 3D Print Observer...")
