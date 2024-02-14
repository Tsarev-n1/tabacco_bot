import datetime

import gspread
from gspread.worksheet import Worksheet
from gspread_formatting import format_cell_range, TextFormat, CellFormat, Color


months_ru = {
    1: "Январь",
    2: "Февраль",
    3: "Март",
    4: "Апрель",
    5: "Май",
    6: "Июнь",
    7: "Июль",
    8: "Август",
    9: "Сентябрь",
    10: "Октябрь",
    11: "Ноябрь",
    12: "Декабрь",
}

products = {
    'Одноразки': [['Затяжки'], (255, 255, 153)],
    'Под системы': [[], (186, 153, 255)],
    'Испарители': [['Сопротивление'], (153, 204, 255)],
    'Жидкости 5%': [[], (153, 255, 187)],
    'Жидкости 2%': [[], (255, 204, 153)],
    'Табак': [[], (204, 153, 255)],
    'Прочее': [[], (153, 255, 255)],
}


def month_days(month: int = 0) -> int:
    """Возвращает количество дней в текущем месяце, либо в определенном"""
    today = datetime.datetime.now()
    if not month:
        current_month = today.replace(day=1)
        next_month = today.replace(month=today.month + 1, day=1)
    else:
        current_month = datetime.date(year=today.year, month=month)
        next_month = current_month.replace(month=month + 1, day=1)

    if month or today.month == 12:
        next_month.replace(year=today.year + 1)

    return (next_month - current_month).days


def get_last_char(worksheet: Worksheet, column=True) -> str:
    """
    Возвращает последний символ в таблице


    :param column: Вернет последний символ стоблца if True else строки
    """

    count = worksheet.col_count if column else worksheet.row_count

    last_char = chr(ord('A') + count - 1)

    return last_char


def get_char_by_index(index: int) -> str | None:
    """Возвращает символ по номеру столбца/строки"""

    if 1 <= index <= 26:
        char = chr(64 + index)
        return char

    return None


def create_cash_worksheet(sheet: gspread.Spreadsheet) -> None:
    """ Создание таблицы 'Денежные средства' """

    global months_ru
    today = datetime.date.today()
    worksheet = sheet.add_worksheet(
        title=f'Денежные средства {months_ru[today.month]} {today.year}',
        rows=month_days(), cols=13,)

    # Редактируем первый столбец с датой
    format_cell_range(worksheet, f'A1:A{worksheet.row_count}',
                      CellFormat(
                        horizontalAlignment='CENTER',
                        textFormat=TextFormat(bold=True))
                    )

    date_cells = worksheet.range(2, 1, worksheet.row_count, 1)

    day = 1
    for cell in date_cells:
        cell.value = datetime.date.today().replace(day=day)

    worksheet.update_cells(date_cells)

    # Заливаем первую строку

    format_cell_range(
        worksheet, f'A1:{get_last_char()}1',
        CellFormat(
            backgroundColor=Color(255, 192, 203),
            horizontalAlignment='CENTER',  # Розовый
            textFormat=TextFormat(bold=True, fontSize=11)),
        )

    # Добавляем заголовки

    headers = {
        'Общий приход': 2,  # Номер столбца
        'Наличка': 3,
        'Безналичка': 4,
        'Расход': 5,
        'Итого': 6,
        'Забрал деньги': 8,
        'Сумма': 9,
        'Переводы на карту': 11,
        'Кому': 12
    }

    for head, column in headers:
        worksheet.update_cell(1, column, head)

    # Заливаем стобцы для разграничения

    columns = [7, 10]

    for column in columns:
        char = get_char_by_index(column)

        format_cell_range(
            worksheet,
            f'{char}1:{char}{worksheet.row_count}',
            CellFormat(backgroundColor=Color(220, 220, 220))  # Светло-серый
        )

    # Ровняем текст в оставшихся ячейках

    format_cell_range(
        worksheet,
        f'B2:F{worksheet.row_count}',
        CellFormat(horizontalAlignment='RIGHT')
    )


def create_work_schedule_sheet(sheet: gspread.Spreadsheet) -> None:
    """ Создание таблицы 'График работы' """

    worksheet = sheet.add_worksheet(
        f'График работы {datetime.date.today().year}',
        rows=96, cols=24
    )

    row = 1
    for _ in worksheet.row_count // 4:

        # Красим ряд над месяцами
        format_cell_range(
            worksheet,
            f'A{row}:R{row}',
            CellFormat(backgroundColor=Color(255, 192, 203),  # Розовый
                       horizontalAlignment='CENTER',
                       textFormat=TextFormat(bold=True)),
            )

        row += 1
        # Объединяем и выставляем параметры ячеек месяца и выручки
        for column in 'AX':
            worksheet.merge_cells(f'{column}{row}:{column}{row+2}')
            format_cell_range(
                worksheet,
                f'{column}{row}:{column}{row+2}',
                CellFormat(
                    horizontalAlignment='CENTER',
                    verticalAlignment='CENTER',
                    backgroundColor=Color(173, 216, 163)  # Зеленый
                    if column == 'X'
                    else None,
                    textFormat=TextFormat(bold=True, fontSize=12))
                )

            # Записываем месяц с датами
            if column == 'A':
                if row-1 == 1:
                    month_count = 1
                else:
                    month_count = row-1 if row % 2 else row-2
                month_half = '1-15' if (row-1) % 2 else \
                    f'16-{month_days(month_count)}'
                text = f'{months_ru[month_count]}\n({month_half})'
                worksheet.update_acell(f'A{row}', text)

        # Редактируем ячейки имен работников
        format_cell_range(
            worksheet,
            f'B{row}:B{row+2}',
            CellFormat(horizontalAlignment='CENTER',
                       textFormat=TextFormat(bold=True))
        )

        #  Редактируем ячейки смены
        #  TODO: Дописать редактор ячеек смен
        format_cell_range(
            worksheet,
            f'{get_char_by_index(row):3}'
        )

        # Подписываем подсчет в конце
        data = {
            'U': 'Выручка',
            'V': 'Кол-во смен',
            'W': 'Зарплата',
            'X': 'Общая выручка'
        }
        for column in data:
            row = 1
            row_range = worksheet.row_count
            while row < row_range:
                worksheet.update_acell(f'{column}{row}', data[column])
                row += 3

        #  TODO: Дописать формулы
        pass


def create_spendings_month(sheet: gspread.Spreadsheet, month: int = 1) -> None:
    """Создание таблицы с расходами по месяцам"""

    current_year = datetime.date.today().year
    worksheet = sheet.add_worksheet(
        f'Расходы {months_ru[month]} {current_year}',
        cols=3,
        rows=month_days(current_year)
    )

    # Редактирование головной строки
    format_cell_range(
        worksheet,
        'A1:C1',
        CellFormat(
            horizontalAlignment='CENTER',
            backgroundColor=Color(255, 192, 203),
            textFormat=TextFormat(bold=True, fontSize=11)
        )       
    )

    data = ['Дата', 'Информация', 'Сумма']

    for col, title in enumerate(data, start=1):
        worksheet.update_cell(1, col, title)


def create_orders(sheet: gspread.Spreadsheet) -> None:
    """ Создание таблицы с предзаказами"""

    worksheet = sheet.add_worksheet(
        'Заказы на товар',
        cols=26,
        rows=50)

    old_count = column_count = 1
    for category in products:
        for options, color in products[category]:
            worksheet.update_cell(1, column_count, category)
            column_count += 1
            if options:
                for option in options:
                    worksheet.update_cell(1, column_count, option)
                    column_count += 1
            worksheet.update_cell(1, column_count, 'Количество')
            column_count += 1

        cell_range = f'{get_char_by_index(old_count)}1:' \
            f'{get_char_by_index(column_count)}1'

        old_count = column_count

        format_cell_range(
            worksheet=worksheet,
            cell_format=CellFormat(
                backgroundColor=Color(color),
                horizontalAlignment='CENTER',
                textFormat=TextFormat(bold=True, fontSize=11)
            ),
            name=cell_range,
        )
