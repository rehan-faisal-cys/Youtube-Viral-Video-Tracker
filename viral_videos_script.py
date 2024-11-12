from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from google.oauth2 import service_account
import schedule
import time
import json
import smtplib
import ssl
from email.message import EmailMessage
import requests
from bs4 import BeautifulSoup
import re
import datetime
import json
import os




def get_latest_videos(url):
    
    cookies = {
        'GPS': '1',
        'YSC': 'BlEjSpS7BHQ',
        'VISITOR_INFO1_LIVE': 'vIqUhmNhAEw',
        'VISITOR_PRIVACY_METADATA': 'CgJQSxIEGgAgVg%3D%3D',
        'SOCS': 'CAISNQgDEitib3FfaWRlbnRpdHlmcm9udGVuZHVpc2VydmVyXzIwMjMwODI5LjA3X3AxGgJlbiADGgYIgJnPpwY',
        'PREF': 'f6=40000000&tz=Asia.Karachi',
    }

    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'accept-language': 'en-US,en;q=0.8',
        'cache-control': 'max-age=0',
        'priority': 'u=0, i',
        'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="126", "Brave";v="126"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-model': '""',
        'sec-ch-ua-platform': '"Windows"',
        'sec-ch-ua-platform-version': '"15.0.0"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'none',
        'sec-fetch-user': '?1',
        'sec-gpc': '1',
        'service-worker-navigation-preload': 'true',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    response = requests.get(url, cookies=cookies, headers=headers)
    data = response.text
    soup = BeautifulSoup(data, 'lxml')

    channel_name = soup.find('meta', itemprop='name')['content']
    print(f"Channel Name: {channel_name}")
    json_data = None
    # Find all <script> tags with the specified nonce attribute
    script_tags = soup.find_all('script')

    # Loop through script tags to find the one containing the specific text
    for script in script_tags:
        script_text = script.get_text()
        if 'var ytInitialData = {"responseContext"' in script_text:
            # Extract the JSON data from the script content
            json_data_str = re.search(r'var ytInitialData = ({.*?});', script_text, re.DOTALL).group(1)
            
            # Parse the JSON data
            json_data = json.loads(json_data_str)
            break
    else:
        print("No script tag found containing the specified text.")
    videos = json_data['contents']['twoColumnBrowseResultsRenderer']['tabs'][1]['tabRenderer']['content']['richGridRenderer']['contents']
    latest_videos = []
    for video in videos:
        #if continuationItemRenderer is in the video, it means it's not a video
        if not 'continuationItemRenderer' in video:
            video_title = video['richItemRenderer']['content']['videoRenderer']['title']['runs'][0]['text']
            video_id = video['richItemRenderer']['content']['videoRenderer']['videoId']
            publishedTime = video['richItemRenderer']['content']['videoRenderer'].get('publishedTimeText', {}).get('simpleText' , "")
            viewsCounts_dic = video['richItemRenderer']['content']['videoRenderer'].get('viewCountText', {})
            views = 0
            if 'simpleText' in viewsCounts_dic:
                viewsCount = viewsCounts_dic['simpleText']
                viewsCount = viewsCount.split(' ')[0].replace(',', '')
                if viewsCount.isdigit():
                    views = int(viewsCount)
            if 'runs' in viewsCounts_dic:
                viewsCount = viewsCounts_dic['runs'][0]['text'].replace(',', '')
                if viewsCount.isdigit():
                    views = int(viewsCount)
            if 'second' in publishedTime or'seconds' in publishedTime or'minute' in publishedTime or 'minutes' in publishedTime:
                if 'minutes' in publishedTime:
                    minutes = int(publishedTime.split(' ')[0])
                    if minutes <= 30 and views > 10000:
                        latest_videos.append({
                            'id': video_id,
                            'channel': channel_name,
                            'title': video_title,
                            'publishedTime': publishedTime,
                            'views': views
                        })
    return latest_videos

def check_all_files(files):
    #CHECK IF ALL FILES EXIST IF NOT CREATE THE FILES
    for file in files:
        if not os.path.exists(file):
            print(f"{file} => missing")
            return False
    return True


def generate_html_body(videos, spreadsheet_id):
    html_body = '''
    <html>
    <head>
        <style>
            table {
                font-family: Arial, sans-serif;
                border-collapse: collapse;
                width: 100%;
            }
            th, td {
                border: 1px solid #ddd;
                padding: 8px;
            }
            th {
                background-color: #f2f2f2;
                text-align: left;
            }
            tr:nth-child(even) {
                background-color: #f9f9f9;
            }
        </style>
    </head>
    <body>
        <p>Below are the latest videos from Channels:</p>
        <table>
            <tr>
                <th>Title</th>
                <th>Channel</th>
                <th>URL</th>
                <th>Views</th>
            </tr>
    '''

    for video in videos:
        html_body += f'''
        <tr>
            <td>{video["title"]}</td>
            <td>{video["channel"]}</td>
            <td><a href="https://www.youtube.com/watch?v={video["id"]}">Watch</a></td>
            <td>{video["views"]} views</td>
        </tr>
        '''

    html_body += f'''
        </table>
        <p>You can view the full data here:</p>
        <p><a href="https://docs.google.com/spreadsheets/d/{spreadsheet_id}">Google Sheet Link</a></p>
    </body>
    </html>
    '''

    return html_body

def send_email(email_sender, email_password, email_receivers, subject, body):
    # Set the subject and body of the email
    em = EmailMessage()
    em['From'] = email_sender
    em['To'] = ', '.join(email_receivers)  # Join receivers with comma and space
    em['Subject'] = subject
    em.add_alternative(body, subtype='html')

    # Add SSL (layer of security)
    context = ssl.create_default_context()

    # Log in and send the email
    with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
        smtp.login(email_sender, email_password)
        smtp.sendmail(email_sender, email_receivers, em.as_string())

    print(f'Email sent successfully to {", ".join(email_receivers)}')

def get_data(service, spreadsheet_id, range_name):
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
    values = result.get('values', [])
    for row in values:
        print(row)
    return values
    
def get_existing_data(service, spreadsheet_id, range_name):
    # Retrieve existing data from the sheet
    result = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
    existing_values = result.get('values', [])
    #get third row value
    existing_ids = [row[2].split('=')[-1] for row in existing_values[1:]]
    return existing_ids


def change_access(cred_file, spreadsheet_id, access_type='reader'):
    try:
        SCOPES = ['https://www.googleapis.com/auth/drive']
        drive_creds = service_account.Credentials.from_service_account_file(cred_file, scopes=SCOPES)
        service = build('drive', 'v3', credentials=drive_creds)
        permission = {'type': 'anyone', 'role': f'{access_type}'}
        response = service.permissions().create(fileId=spreadsheet_id, body=permission, fields='id').execute()
        return f"Permission ID: {response.get('id')}"
    except Exception as e:
        return f"An error occurred: {e}"

def create_sheet(cred_file ):
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    SERVICE_ACCOUNT_FILE = cred_file
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('sheets', 'v4', credentials=creds)
    title = f'Viral_Videos_Data_{datetime.datetime.now().strftime("%Y-%m-%d")}'
    with open('./files/sheet_id.json', 'r', encoding='utf-8') as file:
        j_data = json.load(file)
        if title in j_data:
            print("Sheet already exists")
            return j_data[title]
    spreadsheet = {'properties': {'title': title}}
    spreadsheet = service.spreadsheets().create(body=spreadsheet, fields='spreadsheetId').execute()
    spreadsheet_id = spreadsheet.get('spreadsheetId')
    sheet_values = [['Video Name', 'Channel Name', 'Video URL', 'Views Count']]
    # for video in latest_videos:
    #     sheet_values.append([video['title'], video['channel'], f'https://www.youtube.com/watch?v={video["id"]}', video['views']])
    request = service.spreadsheets().values().update(spreadsheetId=spreadsheet_id, range='Sheet1', valueInputOption='RAW', body={'values': sheet_values})
    response = request.execute()
    change_access(cred_file, spreadsheet_id, 'reader')
    print(f"Data saved to Google Sheet with ID: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
    with open('./files/sheet_id.json', 'w' ,encoding='utf-8') as file:
        j_data[title] = spreadsheet_id
        json.dump(j_data, file, indent=4)
    return spreadsheet_id

def delete_sheet(cred_file, spreadsheet_id):
    try:
        SCOPES = ['https://www.googleapis.com/auth/drive']
        drive_creds = service_account.Credentials.from_service_account_file(cred_file, scopes=SCOPES)
        service = build('drive', 'v3', credentials=drive_creds)
        service.files().delete(fileId=spreadsheet_id).execute()
        return "File deleted successfully"
    except Exception as e:
        return f"An error occurred: {e}"

def update_sheet(service, spreadsheet_id,range_name, latest_videos):
    sheet_values = []
    for video in latest_videos:
        sheet_values.append([video['title'], video['channel'], f'https://www.youtube.com/watch?v={video["id"]}', video['views']])
    request = service.spreadsheets().values().append(spreadsheetId=spreadsheet_id, range=range_name, valueInputOption='RAW', body={'values': sheet_values})
    response = request.execute()
    print(f"Data updated in Google Sheet with ID: {spreadsheet_id}")
    return spreadsheet_id

def read_notification_flag():
    while True:
        try:
            with open('./files/notifications_flag.json', 'r') as file:
                data = json.load(file)
                return data['flag']
        except FileNotFoundError:
            print("notifications_flag.txt not found. Waiting to retry...")
        except Exception as e:
            print(f"Error reading file: {e}. Waiting to retry...")
        time.sleep(5)  # Wait for 5 seconds before retrying


def main(url_file , email_sender, email_password, email_receiver,cred_file):
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    SERVICE_ACCOUNT_FILE = cred_file
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('sheets', 'v4', credentials=creds)
    range_name = 'Sheet1'
    all_latest_videos = []
    with open(url_file, 'r') as file:
        urls = file.read().strip()
        for url in urls.split('\n'):
            if '?' in url:
                url = f"{url.split('?')[0]}/videos"
            elif 'channel' in url:
                url += '/channel/videos'
            else:
                url += '/videos'
            try:
                latest_videos = get_latest_videos(url)
            except Exception as e:
                print(f"An error occured : {e}")
                continue
            all_latest_videos.extend(latest_videos)

    with open('./files/sheet_id.json', 'r', encoding='utf-8') as file:
        data = json.load(file)
        if data:
            title = list(data.keys())[-1]
            spreadsheet_id = data[title]
        else:
            spreadsheet_id = create_sheet(cred_file)
    existing_ids = get_existing_data(service, spreadsheet_id, range_name)
    unique_videos = [video for video in all_latest_videos if video['id'] not in existing_ids]
    
    if unique_videos:
        for video in unique_videos:
            print(f"Title: {video['title']} \n=> Video ID: {video['id']} \n=> Published Time: {video['publishedTime']} \n=> View Count: {video['views']}")
        update_sheet(service, spreadsheet_id,range_name, unique_videos)

        if read_notification_flag():
            body = generate_html_body(unique_videos, spreadsheet_id)
            subject = f'Viral Videos Data - {datetime.datetime.now().strftime("%Y-%m-%d")}'
            send_email(email_sender, email_password, email_receiver, subject, body)
        else:
            print("Notification flag is off. No email sent.")
    else:
        print("No Viral videos found.")
        return "No Viral videos found."
    return "Data updated successfully."
