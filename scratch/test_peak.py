import sys
import os
import time
import asyncio
from PyQt6.QtWidgets import QApplication

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core_services.media_daemon import MediaDaemon

async def main():
    app = QApplication(sys.argv)
    print("Initializing MediaDaemon...")
    daemon = MediaDaemon()
    app.media_daemon = daemon
    
    print("Polling state for 10 seconds. Play some audio/music now!")
    for i in range(50):
        await asyncio.sleep(0.2)
        # Flush Qt event loop
        app.processEvents()
        
        status = daemon.state.status
        title = daemon.state.title
        artist = daemon.state.artist
        peak = daemon.state.audio_peak
        session_count = len(daemon.state.available_sessions)
        
        print(f"[{i*0.2:.1f}s] Session Count: {session_count} | Status: {status} | Title: {title} | Peak: {peak:.4f}")

if __name__ == "__main__":
    asyncio.run(main())
