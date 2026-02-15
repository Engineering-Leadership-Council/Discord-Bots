import discord
import asyncio
import aiohttp
import os
import logging
from dotenv import load_dotenv
from io import BytesIO

# --- Configuration ---
STREAM_URL = "http://192.168.1.121:3031/video"
UPDATE_INTERVAL = 3.0 # Seconds between updates (Don't go too low or Discord will rate limit)
Target_Channel_ID = None # Set this manually or via command if needed, or put in .env

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("StreamBot")

load_dotenv()

class StreamBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stream_task = None
        self.message = None
        self.channel_id = int(os.getenv('STREAM_CHANNEL_ID', '0'))

    async def on_ready(self):
        logger.info(f"Logged in as {self.user}")
        
        if self.channel_id == 0:
            logger.warning("STREAM_CHANNEL_ID not found in .env. Please set it or run !start_stream in a channel.")

    async def on_message(self, message):
        if message.author == self.user:
            return

        if message.content.startswith('!start_stream'):
            if self.stream_task and not self.stream_task.done():
                await message.channel.send("Stream is already running.")
                return

            self.channel_id = message.channel.id
            await message.channel.send("Starting stream...")
            self.stream_task = self.loop.create_task(self.stream_loop(message.channel))

        if message.content.startswith('!stop_stream'):
            if self.stream_task:
                self.stream_task.cancel()
                self.stream_task = None
                await message.channel.send("Stream stopped.")

    async def get_frame(self, session):
        """
        Connects to the MJPEG stream and yields individual JPEG frames.
        This is a generator that stays connected.
        """
        buffer = b""
        try:
            async with session.get(STREAM_URL) as response:
                if response.status != 200:
                    logger.error(f"Failed to connect to stream: {response.status}")
                    return

                # MJPEG streams are multipart/x-mixed-replace. 
                # We need to read the buffer and find JPEG start/end markers.
                # Start: \xff\xd8
                # End: \xff\xd9
                
                async for chunk in response.content.iter_chunked(4096):
                    buffer += chunk
                    
                    while True:
                        a = buffer.find(b'\xff\xd8')
                        b = buffer.find(b'\xff\xd9')
                        
                        if a != -1 and b != -1:
                            if a < b:
                                # We found a complete frame
                                jpg = buffer[a:b+2]
                                buffer = buffer[b+2:]
                                yield jpg
                            else:
                                # End marker before start marker? Garbage data or partial previous frame.
                                # Discard up to start marker
                                buffer = buffer[a:]
                        else:
                            # Not enough data for a full frame
                            break
                        
                    # Clear buffer if it gets too big (safety)
                    if len(buffer) > 5 * 1024 * 1024: # 5MB limit
                         logger.warning("Buffer overflow, clearing.")
                         buffer = b""
                             
        except Exception as e:
            logger.error(f"Stream error: {e}")
            await asyncio.sleep(5) # Wait before retry

    async def stream_loop(self, channel):
        self.message = None # Reset message on new loop
        async with aiohttp.ClientSession() as session:
            backoff = 1
            last_update = 0
            while not self.is_closed():
                try:
                    # Connect to stream
                    async for jpg_data in self.get_frame(session):
                        now = asyncio.get_running_loop().time()
                        
                        # Only update if enough time has passed
                        if self.message is None or (now - last_update >= UPDATE_INTERVAL):
                             # Time to update Discord
                            file = discord.File(BytesIO(jpg_data), filename="stream.jpg")
                            
                            try:
                                if self.message:
                                    # Edit existing message
                                    await self.message.edit(attachments=[file])
                                else:
                                    # Send new message
                                    self.message = await channel.send("Live Stream", file=file)
                                
                                last_update = now
                                backoff = 1 # Reset backoff
                                
                            except discord.NotFound:
                                # Message deleted
                                self.message = None
                                last_update = 0 # Force immediate repost
                            except Exception as e:
                                logger.error(f"Discord update error: {e}")
                
                except Exception as e:
                    logger.error(f"Stream Loop Crash: {e}")
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 30)

if __name__ == "__main__":
    token = os.getenv('STREAM_BOT_TOKEN')
    if not token:
        print("Error: STREAM_BOT_TOKEN not found in .env")
        exit(1)
        
    intents = discord.Intents.default()
    intents.message_content = True
    
    bot = StreamBot(intents=intents)
    bot.run(token)
