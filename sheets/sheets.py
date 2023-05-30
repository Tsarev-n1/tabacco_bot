import gspread

import os


def get_credentials():
    files = os.listdir('./google')
    for file in files:
        if file.endswith('.json'):
            return file
    return None


credentials = get_credentials()
gc = gspread.service_account(filename=f'./google/{credentials}')

sh = gc.open('Табачный магазин')
print(sh.sheet1.get('B1'))
