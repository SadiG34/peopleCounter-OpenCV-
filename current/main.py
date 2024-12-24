import os 

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import requests 

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pandas as pd

df = pd.read_csv('utils/data/logs/counting_data.csv')

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

YOUR_API_KEY = 'API'
SPREADSHEET_ID = ''
RANGE_NAME = 'MAV!A1:D10'  # Область данных, которую вы хотите получить

url = f'https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values/{RANGE_NAME}?key={YOUR_API_KEY}'

response = requests.get(url)
data = response.json()

print(data)

SPREADSHEET_ID = ""

def main():
    credentials = None
    if os.path.exists("token.json"):
        credentials = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())    
        else:
            flow = InstalledAppFlow.from_client_secrets_file("current/Credentials.json", SCOPES)
            credentials = flow.run_local_server(port=0)
        with open("current/token.json", "w") as token:
            token.write(credentials.to_json())
            
    try:
        service = build("sheets", "v4", credentials=credentials) 
        sheets = service.spreadsheets()
       
        for row in range(2, 9): 
            num1 = int(sheets.values().get(spreadsheetId=SPREADSHEET_ID, range=f"MAV!A{row}").execute().get("values")[0][0])
            num2 = int(sheets.values().get(spreadsheetId=SPREADSHEET_ID, range=f"MAV!B{row}").execute().get("values")[0][0]) 
            calculation_result = num1 + num2
            print(f"Processing {num1} + {num2}")
            
            sheets.values().update(spreadsheetId=SPREADSHEET_ID, range=f"MAV!C{row}",
                                    valueInputOption = "USER_ENTERED", body ={"values":[[f"{calculation_result}"]]}).execute()
            
            sheets.values().update(spreadsheetId=SPREADSHEET_ID, range=f"MAV!D{row}",
                                    valueInputOption = "USER_ENTERED", body ={"values":[["Done"]]}).execute()
            
          
        
        
    except HttpError as error:
        print(error)
        
entered_people = []

# В вашем основном цикле, когда человек входит
if person_entered:  # условие для входа
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Текущая дата и время
    entered_people.append((person_id, timestamp))  # Сохраните ID человека и временную метку

    # Записываем информацию в Google Таблицу
    sheet.append_row([person_id, timestamp])

if __name__ == "__main__":  
    main()  
                    
