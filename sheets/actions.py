import os
import datetime as dt

import gspread
from gspread_formatting import format_cell_range, CellFormat, Color
from sqlalchemy.orm import sessionmaker
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

from models.models import Shop, User
from engine import engine
from .sheets import (
    create_cash_worksheet,
    create_orders,
    create_spendings_month,
    create_work_schedule_sheet,
    month_days,
    get_char_by_index,
    months_ru,
    products
)


load_dotenv()
SHEET_KEY = os.getenv('SHEET_KEY')
FOLDER_ID = os.getenv('FOLDER_ID')


def get_credentials() -> str | None:
    files = os.listdir('./google')
    for file in files:
        if file.endswith('.json'):
            return file
    return None


scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']

credentials = ServiceAccountCredentials.from_json_keyfile_name(
    f'./google/{get_credentials()}', scope)

gc = gspread.authorize(credentials)


Session = sessionmaker(bind=engine)


class AccessDeniedException(Exception):
    pass


def check_permission(is_admin: bool = False):
    """Проверка прав доступа"""
    def decorator(func):
        def wrapper(user, worksheet, *args, **kwargs):
            with Session() as sess:
                user_shop = user.shop
                current_shop = sess.query(Shop)\
                    .filter(Shop.wokrsheet == worksheet).first()
            if user.is_admin == is_admin and user_shop is current_shop:
                return func(*args, **kwargs)
            raise AccessDeniedException('Нет прав доступа')
        return wrapper
    return decorator


def workshift_open(user: User, sheet_id: str,
                   open: bool = True, money: int = 0) \
        -> None:
    """Отмечает открытую смену в таблицах"""
    sheet = gc.open_by_key(sheet_id)
    date = dt.date.today()
    worksheet = sheet.worksheet(f'График работы {date.year}')

    days_range = '1-15' if date.day <= 15 \
        else f'16-{month_days(date.month)}'
    # Поиск крайней левой ячейки месяца и временного отрезка
    today_cell = worksheet.find(f'{months_ru[date.month]}\n({days_range})')
    name_cell = worksheet.find(
        user.first_name,
        in_column=today_cell.col + 1
    )
    if not name_cell:
        name_cell = worksheet.update_cell(
            row=today_cell.row,
            col=today_cell.col + 1,
            value=user.first_name
        )
    # Поиск текущей даты
    workshift_cell = worksheet.find(
        f'{date.strftime("%d.%m.%Y")}',
        in_row=name_cell.row,
        in_column=date.day + 2 if date.day < 16
        else date.day - 13
    )
    if not open:
        worksheet.update_cell(name_cell.row, workshift_cell.col, money)
        return

    format_cell_range(
        worksheet,
        f'{get_char_by_index(workshift_cell.col)}{name_cell.row}',
        CellFormat(Color(173, 216, 163))  # Светло-зеленый
    )


def shop_open(shop: Shop) -> None:
    """Создает все таблицы для магазина"""
    sheet = gc.create(
        title=f'{shop.city} {shop.address}',
        folder_id=FOLDER_ID
    )
    with Session() as sess:
        shop.wokrsheet = sheet.id
        sess.add(shop)
        sess.commit()

    create_work_schedule_sheet(sheet)
    create_cash_worksheet(sheet)
    create_orders(sheet)
    create_spendings_month(sheet)


def get_category_orders(key: int, sheet_id: str) -> list[str, None]:
    """Получает все заказы из категории"""

    keys = list(products.keys())
    category = keys[key]

    sheet = gc.open_by_key(sheet_id)
    worksheet = sheet.worksheet('Заказы на товар')

    category_cell = worksheet.find(category)
    background_color = category_cell.background.color
    category_products = []
    next_cell = worksheet.cell(category_cell.row + 1, category_cell.col)

    while next_cell.background.color == background_color:
        category_products.append(next_cell.value)
        next_cell = worksheet.cell(next_cell.row + 1, next_cell.col)

    return category_products


def preorder_create(
    category_num: int,
    preorder_name: str,
    count: int,
    worksheet_id: str,
    parameters: dict = {}
) -> None:
    """Добавление предзаказа в таблицу"""

    sheet = gc.open_by_key(worksheet_id)
    worksheet = sheet.worksheet('Заказы на товар')

    keys = list(products.keys())
    category = keys[category_num]
    category_cell = worksheet.find(category)

    # Дописать поиск, добавление ячеек, цвет

    if category_cell:
        #  Получаем все значения столбца
        col_values = worksheet.col_values(category_cell.col)
        #  Ищем свободную ячейку
        if not col_values[-1]:
            row = col_values.index(None) + 1
        else:
            #  Добавляем новую строку
            worksheet.append_row()
            row = worksheet.row_count

    preorder_cell = gspread.Cell(row, category_cell.col, preorder_name)

    #  Проверяем на каком месте столбец 'Количество' после категории
    count_col_place = len(products[category][0])
    preorder_count_cell = gspread.Cell(row, count_col_place, str(count))

    worksheet.update_cells([preorder_cell, preorder_count_cell])

    #  Проверяем дополнительные параметры
    if parameters:
        for parameter, value in parameters:
            parameter_col = (products[category][0].index(parameter)
                             + 1 + preorder_cell.col)
            worksheet.update_cell(row, parameter_col, str(value))

    cell_range = (f'{get_char_by_index(preorder_cell.col)}{row}:'
                  f'{get_char_by_index(preorder_count_cell)}{row}')

    #  Красим новые ячейки
    format_cell_range(
        worksheet,
        CellFormat(
            backgroundColor=Color(products[category][1]),
            horizontalAlignment='CENTER'
        ),
        name=cell_range
    )


def preorder_update(
    worksheet_id: str,
    category_num: int,
    count: int,
    preorder_name: str
) -> None:
    """Обновление уже готового предзаказа"""
    pass


def preorder_delete() -> None:
    """Удаление предзаказа"""
