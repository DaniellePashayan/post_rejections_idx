import os
from pushbullet import Pushbullet

def send_error_notification(message):
    PB_API_KEY = os.getenv('PUSHBULLET_API_KEY')
    pb = Pushbullet(PB_API_KEY)
    pb.push_note("REJECTION SCRIPTING ERROR", f"{message}")