import pandas as pd


FILE = "database.xlsx"


# ==========================
# ЗАГРУЗКА БАЗЫ
# ==========================

def load_database():

    df = pd.read_excel(
        FILE,
        sheet_name="Генераторы"
    )

    df.columns = df.columns.str.strip()

    return df



# ==========================
# ГЕНЕРАТОРЫ
# ==========================

def load_generators():

    df = load_database()


    return df[
        df["категория"]
        .astype(str)
        .str.lower()
        == "генератор"
    ]



# ==========================
# СОПУТКА
# ==========================

def load_accessories():

    df = load_database()


    return df[
        df["категория"]
        .astype(str)
        .str.lower()
        == "сопутка"
    ]



# ==========================
# ПОТРЕБИТЕЛИ
# ==========================

def load_consumers():

    df = pd.read_excel(
        FILE,
        sheet_name="Потребители"
    )


    df.columns = df.columns.str.strip()


    if "id" not in df.columns:

        df.insert(
            0,
            "id",
            range(1, len(df)+1)
        )


    # если нет пусковых токов
    # используем обычную мощность

    if "Пусковые токи, Вт" not in df.columns:

        df["Пусковые токи, Вт"] = (
            df["Мощность, Вт"]
        )


    df["Пусковые токи, Вт"] = (
        df["Пусковые токи, Вт"]
        .fillna(
            df["Мощность, Вт"]
        )
    )


    return df



# ==========================
# РАСЧЁТ МОЩНОСТИ
# ==========================

def calculate_power(ids):

    df = load_consumers()


    selected = df[
        df["id"].isin(ids)
    ]


    work_power = (
        selected["Мощность, Вт"]
        .sum()
    )


    start_power = (
        selected["Пусковые токи, Вт"]
        .sum()
    )


    total = max(
        work_power,
        start_power
    )


    result = int(
        total * 1.3
    )


    return {

        "work": int(work_power),

        "start": int(start_power),

        "result": result

    }



# ==========================
# ПОИСК ГЕНЕРАТОРОВ
# ==========================

def find_generators(
        voltage=None,
        power=None,
        starter=None,
        avr=None,
        display=None,
        generator_type=None
):

    df = load_generators()



    if voltage:

        df = df[
            df["Напряжение"] == voltage
        ]



    if power:

        df = df[
            df["Максимальная мощность"]
            >= power
        ]



    if starter:

        df = df[
            df["Стартер"] == starter
        ]



    if avr:

        df = df[
            df["АВР"] == avr
        ]



    if display:

        df = df[
            df["Дисплей"] == display
        ]



    if generator_type:

        df = df[
            df["Тип генератора"]
            == generator_type
        ]



    return df.head(5)



# ==========================
# СОПУТКА ПО НАЗВАНИЮ
# ==========================

def get_accessory(name):

    df = load_accessories()


    item = df[
        df["Модель"] == name
    ]


    if item.empty:

        return None


    return item.iloc[0]