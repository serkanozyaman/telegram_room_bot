import os
import gspread
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os.path
from datetime import datetime
import pytz

TOKEN = 'BOT_TOKEN'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = r"SERVICE_ACCOUNT_FILE_PATH"
SPREADSHEET_ID = 'SPREADSHEET_ID'
turkey_tz = pytz.timezone('Europe/Istanbul')

def authenticate_google_sheets():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json')
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    gc = build('sheets', 'v4', credentials=creds)
    return gc

def log_to_google_sheets(update, path):
    SPREADSHEET_ID = 'SPREADSHEET_ID'
    gc = authenticate_google_sheets()
    worksheet = gc.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range='Sayfa1!A1:Z1000').execute()
    values = worksheet.get('values', [])
    user = update.message.from_user
    username = user.username if user.username else user.full_name
    command_time = datetime.now(turkey_tz).strftime('%Y-%m-%d %H:%M:%S')
    command = path
    row = [username, command, command_time]
    values.append(row)
    gc.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range='Sayfa1',
        body={'values': values},
        valueInputOption='RAW'
    ).execute()

class User:
    def __init__(self, username, checked_in=False):
        self.username = username
        self.checked_in = checked_in

users = []
room_status  = 0

def oda_acik(update: Update, context: CallbackContext) -> None:
    global room_status
    username = update.message.from_user.username
    if room_status == 0:
        log_to_google_sheets(update, '/oda_acik')
        log_to_google_sheets(update, '/giris')
        new_user = User(username, checked_in=True)  # Yeni bir User nesnesi oluştur
        users.append(new_user)  # Yeni kullanıcıyı users listesine ekle
        update.message.reply_text(f"Koşun Koşun {username} Odayı Açtı !")
        room_status = 1
    else:
        update.message.reply_text("""Oda zaten açık :')""")


def oda_kapali(update: Update, context: CallbackContext) -> None:
    global room_status
    username = update.message.from_user.username
    if room_status == 1:
        log_to_google_sheets(update, '/oda_kapali')
        update.message.reply_text("""Herkes çıktı oda kapandı :') """)
        room_status = 0
        users.clear()  
    else:
        update.message.reply_text("""Oda zaten kapalı :')""")

def giris(update: Update, context: CallbackContext) -> None:
    global room_status
    if room_status == 1:
        username = update.message.from_user.username
        for user in users:
            if user.username == username:
                if user.checked_in:
                    update.message.reply_text('Zaten odadasın!')
                    return
                else:
                    user.checked_in = True
                    log_to_google_sheets(update, '/giris')
                    update.message.reply_text('Odaya hoşgeldin!')
                    return
        new_user = User(username, checked_in=True)
        users.append(new_user)
        log_to_google_sheets(update, '/giris')
        update.message.reply_text('Odaya hoşgeldin!')
    elif room_status == 0:
        update.message.reply_text("""Oda kapalı. Giriş yapamazsın maalesef :')""")

def cikis(update: Update, context: CallbackContext) -> None:
    global room_status
    if room_status == 1:
        username = update.message.from_user.username
        for user in users:
            if user.username == username:
                if user.checked_in:
                    user.checked_in = False
                    log_to_google_sheets(update, '/cikis')
                    update.message.reply_text('Güle güle! Yine bekleriz :)')
                    return
                else:
                    update.message.reply_text('Zaten odada değilsin!')
                    return

    elif room_status == 0:
        update.message.reply_text("""Oda kapalı  nereye çıkıyon :')""")

def list_users_not_checked_out(update: Update, context: CallbackContext) -> None:
    if  room_status == 0:
        update.message.reply_text('Oda kapalı!')
    elif room_status == 1 and users != []:
        users_not_checked_out = [user.username for user in users if user.checked_in]
        user_list_text = "Odada ha bu uşaklar var:\n"
        for username in users_not_checked_out:
            user_list_text += f"{username}\n"
        update.message.reply_text(user_list_text)

        
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("oda_acik", oda_acik))
    dp.add_handler(CommandHandler("oda_kapali", oda_kapali))
    dp.add_handler(CommandHandler("giris", giris))
    dp.add_handler(CommandHandler("cikis", cikis))
    dp.add_handler(CommandHandler("kimvar", list_users_not_checked_out))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
