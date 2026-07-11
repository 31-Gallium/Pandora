import asyncio
import websockets
import json
import threading
import utils
from config import ConfigManager

class IPCServer:
    def __init__(self, on_config_updated=None):
        self.on_config_updated = on_config_updated
        self.clients = set()
        self.loop = None
        self.thread = None

    async def handler(self, websocket):
        self.clients.add(websocket)
        try:
            # Send initial config
            cfg = ConfigManager.load()
            await websocket.send(json.dumps({"type": "config_init", "data": cfg}))
            
            async for message in websocket:
                data = json.loads(message)
                if data.get("type") == "update_config":
                    new_cfg = data.get("data")
                    ConfigManager.save(new_cfg)
                    
                    try:
                        from config import set_startup_registry
                        enable_startup = new_cfg.get("general_settings", {}).get("launch_at_startup", False)
                        set_startup_registry(enable_startup)
                    except Exception as e:
                        print(f"Error setting startup: {e}")
                    
                    if self.on_config_updated:
                        self.on_config_updated(new_cfg)
                        
                elif data.get("type") == "get_config":
                    cfg = ConfigManager.load()
                    await websocket.send(json.dumps({"type": "config_init", "data": cfg}))
                
        finally:
            self.clients.remove(websocket)

    async def _main(self):
        async with websockets.serve(self.handler, "localhost", 8765):
            await asyncio.Future()  # run forever

    def _run_server(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._main())

    def start(self):
        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()

    def broadcast_config(self):
        if self.loop and self.clients:
            cfg = ConfigManager.load()
            msg = json.dumps({"type": "config_init", "data": cfg})
            asyncio.run_coroutine_threadsafe(
                self._broadcast(msg), 
                self.loop
            )

    async def _broadcast(self, msg):
        for client in self.clients:
            try:
                await client.send(msg)
            except:
                pass
