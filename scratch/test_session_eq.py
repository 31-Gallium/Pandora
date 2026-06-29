import asyncio

async def test():
    try:
        import winsdk._winrt
        winsdk._winrt.init_apartment(winsdk._winrt.MTA)
    except:
        pass
        
    from winsdk.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as SessionManager
    manager = await SessionManager.request_async()
    sessions1 = manager.get_sessions()
    sessions2 = manager.get_sessions()
    
    if len(sessions1) > 0 and len(sessions2) > 0:
        print(f"Wrapper 1 ID: {id(sessions1[0])}")
        print(f"Wrapper 2 ID: {id(sessions2[0])}")
        print(f"Are they == ? {sessions1[0] == sessions2[0]}")
    else:
        print("No sessions.")

asyncio.run(test())
