from pycaw.pycaw import AudioUtilities
import pythoncom

def test_matching():
    pythoncom.CoInitialize()
    sessions = AudioUtilities.GetAllSessions()
    app_id = "SpotifyAB.SpotifyMusic_zpdnekdrzrea0!Spotify"
    print(f"Target App ID: {app_id}")
    print("-" * 30)
    for session in sessions:
        if session.Process:
            name = session.Process.name().lower()
            match = name in app_id.lower() or app_id.lower() in name
            print(f"Process: {name:20} | Match: {match}")
            
            # Improved match test
            clean_name = name.replace(".exe", "")
            improved_match = clean_name in app_id.lower() or app_id.lower() in clean_name
            print(f"  (Clean: {clean_name:18} | Improved: {improved_match})")

if __name__ == "__main__":
    test_matching()
