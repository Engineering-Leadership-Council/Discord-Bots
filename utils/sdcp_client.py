import asyncio
import aiohttp
import json
import logging
import uuid
import time
import socket

logger = logging.getLogger("SDCPClient")

class SDCPClient:
    def __init__(self, host, port=3030):
        self.host = host
        self.port = port
        self.mainboard_id = None
        self.ws_url = f"ws://{host}:{port}/websocket"
        self.status = {}
        self.attributes = {}
        
    async def discover_mainboard_id(self):
        """
        Sends a specific UDP unicast packet to the host to get the MainboardID.
        """
        try:
            # Run blocking socket IO in a thread executor to avoid blocking the event loop
            loop = asyncio.get_running_loop()
            
            def _udp_query():
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(2.0)
                try:
                    message = b"M99999"
                    target = (self.host, 3000)
                    sock.sendto(message, target)
                    data, _ = sock.recvfrom(4096)
                    return data
                except Exception as e:
                    # logger.debug(f"UDP discovery failed: {e}")
                    return None
                finally:
                    sock.close()

            data = await loop.run_in_executor(None, _udp_query)
            
            if data:
                text = data.decode('utf-8', errors='ignore')
                if text.strip().startswith('{'):
                    j = json.loads(text)
                    # Check multiple locations for MainboardID
                    self.mainboard_id = j.get('Data', {}).get('MainboardID') or j.get('MainboardID')
                    if self.mainboard_id:
                        logger.info(f"Discovered MainboardID: {self.mainboard_id}")
                        return self.mainboard_id

        except Exception as e:
            logger.error(f"Async UDP error: {e}")
            
        return None

    async def fetch_status(self):
        """
        Connects via WebSocket, requests status, waits for response, and closes.
        Returns a dict with 'filename', 'print_duration', 'state', 'progress'.
        """
        if not self.mainboard_id:
            await self.discover_mainboard_id()
            if not self.mainboard_id:
                return {}

        headers = {"User-Agent": "Mozilla/5.0"}
        result = {}

        try:
            # Use a slightly longer timeout for the connection phase
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
                async with session.ws_connect(self.ws_url) as ws:
                    
                    uuid_str = str(uuid.uuid4())
                    ts = int(time.time())
                    topic = f"sdcp/request/{self.mainboard_id}"
                    
                    # Exact format needed by Elegoo SDCP v3.0
                    payload = {
                        "Id": uuid_str,
                        "Data": {
                            "Cmd": 0,
                            "Data": {},
                            "RequestID": uuid_str,
                            "MainboardID": self.mainboard_id,
                            "TimeStamp": ts,
                            "From": 0 
                        },
                        "Topic": topic
                    }
                    
                    await ws.send_json(payload)
                    
                    # Wait for up to 3 seconds for a response
                    start_time = time.time()
                    while time.time() - start_time < 3.0:
                        try:
                            # Add a small timeout to receive() so we don't block forever if server is silent
                            msg = await ws.receive(timeout=1.0)
                            
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                data = json.loads(msg.data)
                                
                                # Check for Status in various places
                                # 1. Status Topic
                                if 'Status' in data and 'PrintInfo' in data['Status']:
                                    status_data = data['Status']
                                    print_info = status_data.get('PrintInfo', {})
                                    
                                    # Parse State
                                    # Status: 0=Idle, 1=Printing (from docs/observations)
                                    status_code = print_info.get('Status', 0)
                                    state = "idle"
                                    if status_code == 1:
                                        state = "printing"
                                    elif status_code == 2: # Paused?
                                        state = "paused"
                                        
                                    result = {
                                        'filename': print_info.get('Filename', ''),
                                        'print_duration': print_info.get('CurrentTicks', 0), # Seconds?
                                        'total_duration': print_info.get('TotalTicks', 0),
                                        'state': state,
                                        'progress': 0,
                                        'meta': status_data
                                    }
                                    
                                    # Calc Progress
                                    if result['total_duration'] > 0:
                                        result['progress'] = result['print_duration'] / result['total_duration']
                                    elif print_info.get('TotalLayer', 0) > 0:
                                        result['progress'] = print_info.get('CurrentLayer', 0) / print_info.get('TotalLayer')
                                        
                                    return result
                                    
                            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                                break
                        except asyncio.TimeoutError:
                            continue # Loop to check total time
                            
        except Exception as e:
            logger.error(f"SDCP WebSocket error: {e}")
            
        return result
