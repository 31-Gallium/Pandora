import asyncio
import websockets
import sys

async def main():
    try:
        async with websockets.connect('ws://localhost:8765') as ws:
            print("Successfully connected to Pandora WS server!")
            # Read first message (init_config)
            msg = await ws.recv()
            print("Received init_config:")
            print(msg[:200] + "...")
            sys.exit(0)
    except Exception as e:
        print(f"Failed to connect: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
