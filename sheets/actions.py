import os
import datetime as dt

import gspread
from gspread_formatting import (
    format_cell_range, CellFormat,
    Color, TextFormat
)
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
    """Получает все предзаказы из категории"""

    keys = list(products.keys())
    category = keys[key]

    sheet = gc.open_by_key(sheet_id)
    worksheet = sheet.worksheet('Заказы на товар')

    category_cell = worksheet.find(category)

    #  Получаем все значения из столбца и отсеиваем пустые
    category_products = list(filter(
        lambda x: x is not None,
        worksheet.col_values(category_cell)[1:]
        ))

    return category_products


def preorder_create(
    category_pos: int,
    preorder_name: str,
    sheet_id: str,
    count: int = 0,
    parameters: dict = {}
) -> None:
    """Добавление предзаказа в таблицу"""

    sheet = gc.open_by_key(sheet_id)
    worksheet = sheet.worksheet('Заказы на товар')

    keys = list(products.keys())
    category = keys[category_pos]
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
            worksheet.append_row([])
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
    sheet_id: str,
    category_pos: int,
    count: int,
    order_pos: int
) -> None:
    """Обновление уже готового предзаказа"""

    sheet = gc.open_by_key(sheet_id)
    category = list(products.keys())[category_pos]
    worksheet = sheet.worksheet('Заказы на товар')

    # Получаем название заказа и его ячейку
    order = get_category_orders(category_pos, sheet_id)[order_pos]
    order_cell = worksheet.find(order)

    # Получаем номер столбца 'Количество' и значение ячейки
    # (количество параметров + номер столбца с названием + 1 шаг)
    count_col = len(products[category][0]) + order_cell.col + 1
    order_count = int(worksheet.cell(row=order_cell.row, col=count_col).value)
    updated_order = gspread.Cell(
        value=order_count+count,
        row=order_cell.row,
        col=count_col
    )
    worksheet.update_cells([updated_order])


def preorder_delete(
    sheet_id: str,
    category_num: int,
    preorder_name: str
) -> None:
    """Удаление предзаказа"""

    sheet = gc.open_by_key(sheet_id)
    worksheet = sheet.worksheet('Заказы на товар')
    preorder_cell = worksheet.find(preorder_name)

    # Получаем количество параметров и прибавляем две колонки 'Количество'
    # и название категории
    minitable_width = len(list(products.values())[category_num][0]) + 2

    last_row = len(list(filter(
            lambda x: x is not None,
            worksheet.col_values(col=preorder_cell.col)
        )))

    cells_to_remove = [
        gspread.Cell(row=last_row, col=preorder_cell.col + j, value=None)
        for j in range(minitable_width)
    ]

    # Если ячейка не крайняя снизу
    if not worksheet.cell(preorder_cell.row + 1, preorder_cell.col).value:
        # Смещаем все нижние значения на позицию выше
        for col_offset in range(minitable_width):
            parameters: list = worksheet.col_values(
                preorder_cell.col+col_offset
            )
            parameters = list(filter(lambda x: x is not None))
            for pos, parameter in enumerate(
                parameters[preorder_cell.row:], start=1
            ):
                worksheet.update_cell(
                    row=preorder_cell.row + pos,
                    col=preorder_cell.col + col_offset,
                    value=parameter
                )
    worksheet.update_cells(cells_to_remove)
