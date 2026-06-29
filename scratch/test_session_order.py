import asyncio

async def test():
    try:
        import winsdk._winrt
        winsdk._winrt.init_apartment(winsdk._winrt.MTA)
    except:
        pass
        
    from winsdk.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as SessionManager
    manager = await SessionManager.request_async()
    s1 = manager.get_sessions()
    await asyncio.sleep(1)
    s2 = manager.get_sessions()
    
    for i, (a, b) in enumerate(zip(s1, s2)):
        print(f"Session {i}: {a.source_app_user_model_id} == {b.source_app_user_model_id}")

asyncio.run(test())
