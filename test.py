import gspread
from google.oauth2.service_account import Credentials

# Определяем области доступа
scopes = [
    "https://spreadsheets.google.com/feeds",
    'https://www.googleapis.com/auth/spreadsheets',
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]

# Загружаем учетные данные
creds = Credentials.from_service_account_file('credentials.json', scopes=scopes)
client = gspread.authorize(creds)

# Открываем таблицу по ID
sheet_id = '1BJpwNWvNUc1jINGiOZlUWsCzxdYzuP6aEglwjp-m5Bc'
spreadsheet = client.open_by_key(sheet_id)

# Получаем вторую вкладку (лист)
worksheet = spreadsheet.get_worksheet(1)  # Индекс 1 для второй вкладки

# Записываем данные в новую строку с обработкой исключений
try:
    worksheet.append_row([2, 2, 2, 'test', 'test'])
    print("Данные успешно записаны в таблицу.")
except Exception as e:
    print(f"Произошла ошибка: {e}")