import schedule
import time
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from viral_videos_script import *


url_file = './files/channels_url.txt'
cred_file = './files/industrial-glow-430302-b9-2614cd5ccb2b.json'

files = [url_file , cred_file , './files/notifications_flag.json' ,'./files/sheet_id.json']
if check_all_files(files):
    email_sender = 'viralvideoapp7@gmail.com'
    email_password = 'ouctkcvrucyhruxr'
    email_receiver = ['viralvideoapp7@gmail.com','ajmuro19@gmail.com','captainalders1@gmail.com','Jonmuro10x@icloud.com']
    schedule.every().day.at("00:01").do(lambda: create_sheet(cred_file))
    schedule.every(5).minutes.do(lambda: main(url_file,email_sender, email_password, email_receiver,cred_file))
    while True:
        schedule.run_pending()
else:
    print('Files are missing')