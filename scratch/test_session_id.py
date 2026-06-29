import asyncio

async def test():
    try:
        import winsdk._winrt
        winsdk._winrt.init_apartment(winsdk._winrt.MTA)
    except:
        pass
        
    from winsdk.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as SessionManager
    manager = await SessionManager.request_async()
    sessions = manager.get_sessions()
    
    for s in sessions:
        print(f"App ID: {s.source_app_user_model_id}")
        print(f"Dir: {dir(s)}")
        break

asyncio.run(test())
