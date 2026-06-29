import asyncio
import json
from PyQt6.QtCore import QThread, pyqtSignal
from websockets.server import serve

class WebSocketServerThread(QThread):
    config_received = pyqtSignal(dict)
    client_connected = pyqtSignal()
    port_bound = pyqtSignal(int)
    create_folder_requested = pyqtSignal()
    
    def __init__(self, cfg, host="localhost", port=0):
        super().__init__()
        self.cfg = cfg
        self.host = host
        self.port = port
        self.loop = None
        self.clients = set()

    async def handler(self, websocket):
        self.clients.add(websocket)
        self.client_connected.emit()
        
        # Send initial config to client upon connection
        try:
            await websocket.send(json.dumps({
                "type": "init_config",
                "data": self.cfg
            }))
        except:
            pass

        try:
            async for message in websocket:
                try:
                    payload = json.loads(message)
                    if payload.get('type') == 'update_config':
                        new_data = payload.get('data')
                        if new_data:
                            print("WS RECV CONFIG:", new_data.get('hub_config', {}).get('layers', []))
                            self.config_received.emit(new_data)
                    elif payload.get('type') == 'create_folder_at_cursor':
                        self.create_folder_requested.emit()
                except Exception as e:
                    print(f"WS Parse Error: {e}")
        finally:
            self.clients.remove(websocket)

    async def _run_server(self):
        async with serve(self.handler, self.host, self.port) as server:
            assigned_port = server.sockets[0].getsockname()[1]
            self.port = assigned_port
            self.port_bound.emit(assigned_port)
            await asyncio.Future()  # run forever

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._run_server())
        except Exception as e:
            print(f"WS Server error: {e}")

    def send_config_to_clients(self, new_cfg):
        self.cfg = new_cfg
        if self.loop and self.clients:
            asyncio.run_coroutine_threadsafe(self._broadcast_config(), self.loop)
            
    async def _broadcast_config(self):
        msg = json.dumps({"type": "update_config", "data": self.cfg})
        for client in list(self.clients):
            try:
                await client.send(msg)
            except:
                pass

    def send_command_to_clients(self, command_dict):
        """Send an arbitrary JSON command to all connected Electron clients."""
        if self.loop and self.clients:
            asyncio.run_coroutine_threadsafe(self._broadcast_command(command_dict), self.loop)

    async def _broadcast_command(self, command_dict):
        msg = json.dumps(command_dict)
        for client in list(self.clients):
            try:
                await client.send(msg)
            except:
                pass
