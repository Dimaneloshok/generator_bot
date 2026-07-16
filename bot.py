import os

# отключаем прокси
for key in [
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "http_proxy",
    "https_proxy",
    "ALL_PROXY",
    "all_proxy"
]:
    os.environ.pop(key, None)


import pandas as pd
import telebot
from telebot import types

from config import BOT_TOKEN

from excel import (
    load_consumers,
    find_generators,
    load_generators,
    get_accessory
)


bot = telebot.TeleBot(
    BOT_TOKEN,
    parse_mode=None
)


users = {}


print("Бот:", bot.get_me())



# ==========================
# СОЗДАНИЕ ПОЛЬЗОВАТЕЛЯ
# ==========================


def create_user(chat_id):

    users[chat_id] = {

        "power": 0,

        "voltage": None,

        "starter": None,

        "generator_type": None,

        "cart": [],

        "selected_generator": None,

        "waiting_power": False,

        "custom_consumer": None

    }



# ==========================
# START
# ==========================


@bot.message_handler(commands=["start"])
def start(message):

    create_user(message.chat.id)


    keyboard = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )


    keyboard.add(
        "Нет, только однофазные (220В)",
        "Да, есть"
    )


    bot.send_message(

        message.chat.id,

        "Здравствуйте!\n\n"
        "Помогу подобрать генератор.\n\n"
        "Есть ли у вас потребители 380В?",

        reply_markup=keyboard

    )



# ==========================
# НАПРЯЖЕНИЕ
# ==========================


@bot.message_handler(
    func=lambda m:
    m.text in [
        "Нет, только однофазные (220В)",
        "Да, есть"
    ]
)
def choose_voltage(message):

    chat_id = message.chat.id


    if chat_id not in users:

        create_user(chat_id)



    if message.text == "Да, есть":

        users[chat_id]["voltage"] = "380В"

    else:

        users[chat_id]["voltage"] = "220В"



    consumers = load_consumers()


    keyboard = types.InlineKeyboardMarkup()



    for _, item in consumers.iterrows():

        keyboard.add(

            types.InlineKeyboardButton(

                text=item["Прибор"],

                callback_data=f"consumer:{item['id']}"

            )

        )



    keyboard.add(

        types.InlineKeyboardButton(

            text="Продолжить подбор",

            callback_data="finish_consumers"

        )

    )



    bot.send_message(

        chat_id,

        "Выберите приборы, которые будут работать одновременно:",

        reply_markup=keyboard

    )



# ==========================
# ПОТРЕБИТЕЛИ
# ==========================


@bot.callback_query_handler(
    func=lambda call:
    call.data.startswith("consumer:")
)
def add_consumer(call):

    chat_id = call.message.chat.id


    consumer_id = call.data.split(":")[1]


    df = load_consumers()


    row = df[
        df["id"].astype(str)
        == consumer_id
    ]


    if row.empty:

        return



    item = row.iloc[0]


    name = item["Прибор"]

    power = item["Мощность, Вт"]



    if pd.isna(power):

        users[chat_id]["waiting_power"] = True

        users[chat_id]["custom_consumer"] = name


        bot.send_message(

            chat_id,

            f"Введите мощность прибора:\n{name}"

        )


        return



    users[chat_id]["power"] += int(power)



    bot.answer_callback_query(call.id)



    bot.send_message(

        chat_id,

        f"Добавлено:\n"
        f"{name}\n"
        f"{power} Вт\n\n"
        f"Всего: "
        f"{users[chat_id]['power']} Вт"

    )



# ==========================
# РУЧНОЙ ВВОД МОЩНОСТИ
# ==========================


@bot.message_handler(
    func=lambda m:
    users.get(m.chat.id, {})
    .get("waiting_power")
)
def custom_power(message):

    chat_id = message.chat.id


    try:

        power = int(message.text)

    except:

        bot.send_message(
            chat_id,
            "Введите число."
        )

        return



    users[chat_id]["power"] += power

    users[chat_id]["waiting_power"] = False

    users[chat_id]["custom_consumer"] = None



    bot.send_message(

        chat_id,

        f"Добавлено {power} Вт\n"
        f"Всего: {users[chat_id]['power']} Вт"

    )



# ==========================
# ЗАВЕРШЕНИЕ ПОТРЕБИТЕЛЕЙ
# ==========================


@bot.callback_query_handler(
    func=lambda call:
    call.data == "finish_consumers"
)
def finish_consumers(call):

    chat_id = call.message.chat.id


    power = users[chat_id]["power"]


    power = int(power * 1.3)


    users[chat_id]["power"] = power



    keyboard = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )


    keyboard.add(

        "Электрический стартер",

        "Ручной запуск"

    )



    bot.send_message(

        chat_id,

        f"Расчётная мощность: {power} Вт\n\n"
        "Какой запуск генератора вам удобнее?",

        reply_markup=keyboard

    )# ==========================
# ВЫБОР СТАРТЕРА
# ==========================


@bot.message_handler(
    func=lambda m:
    m.text in [
        "Электрический стартер",
        "Ручной запуск"
    ]
)
def choose_starter(message):

    chat_id = message.chat.id


    if message.text == "Электрический стартер":

        users[chat_id]["starter"] = "Электрический"

    else:

        users[chat_id]["starter"] = "Ручной"



    keyboard = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )


    keyboard.add(
        "Да",
        "Нет"
    )


    bot.send_message(

        chat_id,

        "Будете подключать чувствительную технику?\n\n"
        "(котёл, компьютер, телевизор)\n\n"
        "Для такой техники лучше подходит инверторный генератор.",

        reply_markup=keyboard

    )





# ==========================
# ТИП ГЕНЕРАТОРА
# ==========================


@bot.message_handler(
    func=lambda m:
    m.text in [
        "Да",
        "Нет"
    ]
)
def choose_generator_type(message):

    chat_id = message.chat.id



    if message.text == "Да":

        users[chat_id]["generator_type"] = "Инверторный"

    else:

        users[chat_id]["generator_type"] = None



    data = users[chat_id]



    results = find_generators(

        voltage=data["voltage"],

        power=data["power"],

        starter=data["starter"],

        generator_type=data["generator_type"]

    )



    if results.empty:


        bot.send_message(

            chat_id,

            "Не удалось подобрать генератор.\n"
            "Попробуйте изменить параметры."

        )

        return



    keyboard = types.InlineKeyboardMarkup()


    text = "Подходящие генераторы:\n\n"



    for _, row in results.iterrows():


        text += (

            f"⚡ {row['Модель']}\n"

            f"Бренд: {row['Бренд']}\n"

            f"Мощность: {row['Мощность']} Вт\n"

            f"Тип: {row['Тип генератора']}\n"

            f"Стартер: {row['Стартер']}\n"

            f"Цена: {row['цена']} ₽\n\n"

        )



        keyboard.add(

            types.InlineKeyboardButton(

                text=row["Модель"],

                callback_data=f"generator:{row['id']}"

            )

        )



    bot.send_message(

        chat_id,

        text,

        reply_markup=keyboard

    )





# ==========================
# ВЫБОР ГЕНЕРАТОРА
# ==========================


@bot.callback_query_handler(
    func=lambda call:
    call.data.startswith("generator:")
)
def select_generator(call):

    chat_id = call.message.chat.id


    generator_id = call.data.split(":")[1]


    df = load_generators()



    row = df[

        df["id"].astype(str)
        == generator_id

    ]



    if row.empty:

        return



    generator = row.iloc[0]



    users[chat_id]["selected_generator"] = generator


    users[chat_id]["cart"].append(generator)



    bot.answer_callback_query(call.id)



    bot.send_message(

        chat_id,

        "Отличный выбор!\n\n"
        f"⚡ {generator['Модель']}\n"
        f"Цена: {generator['цена']} ₽"

    )



    start_accessories(chat_id)
    # ==========================
# СОПУТСТВУЮЩИЕ ТОВАРЫ
# ==========================


def start_accessories(chat_id):


    # АВР только если выбран электрический стартер

    if users[chat_id]["starter"] == "Электрический":

        show_accessory(

            chat_id,

            "АВР",

            "Хотите, чтобы генератор включался автоматически при отключении электричества?"

        )

    else:

        show_accessory(

            chat_id,

            "Масло Huter 10W40",

            "Вам нужно моторное масло для обкатки и дальнейшей работы?"

        )





def show_accessory(chat_id, name, question):


    item = get_accessory(name)



    if item is None:

        next_accessory(chat_id)

        return



    users[chat_id]["current_accessory"] = name



    keyboard = types.InlineKeyboardMarkup()



    keyboard.add(

        types.InlineKeyboardButton(

            text="Да, добавить",

            callback_data="add_accessory"

        ),

        types.InlineKeyboardButton(

            text="Нет",

            callback_data="skip_accessory"

        )

    )



    bot.send_message(

        chat_id,

        f"{question}\n\n"
        f"📦 {item['Модель']}\n"
        f"Цена: {item['цена']} ₽",

        reply_markup=keyboard

    )





def next_accessory(chat_id):


    order = [

        "АВР",

        "Масло Huter 10W40",

        "Комплект колёса+ручка",

        "Удлинитель 25м 16А"

    ]



    current = users[chat_id].get(
        "current_accessory"
    )



    if current in order:

        index = order.index(current) + 1

    else:

        index = 0



    # пропускаем АВР для ручного запуска

    if users[chat_id]["starter"] != "Электрический":

        if index == 0:

            index = 1



    if index >= len(order):

        show_cart(chat_id)

        return



    name = order[index]



    questions = {


        "АВР":

        "Хотите, чтобы генератор включался автоматически при отключении электричества?",


        "Масло Huter 10W40":

        "Вам нужно моторное масло для обкатки и дальнейшей работы?",


        "Комплект колёса+ручка":

        "Вам важна мобильность генератора?",


        "Удлинитель 25м 16А":

        "Также рекомендуем удлинитель 25м 16А.\nДобавить?"

    }



    show_accessory(

        chat_id,

        name,

        questions[name]

    )





# ==========================
# ОТВЕТ ПО СОПУТКЕ
# ==========================


@bot.callback_query_handler(
    func=lambda call:
    call.data in [
        "add_accessory",
        "skip_accessory"
    ]
)
def accessory_answer(call):

    chat_id = call.message.chat.id



    if call.data == "add_accessory":


        name = users[chat_id]["current_accessory"]


        item = get_accessory(name)



        if item is not None:


            users[chat_id]["cart"].append(item)



            bot.send_message(

                chat_id,

                f"Добавлено:\n"
                f"{item['Модель']}\n"
                f"{item['цена']} ₽"

            )



    next_accessory(chat_id)





# ==========================
# КОРЗИНА
# ==========================


def show_cart(chat_id):


    text = "Ваш комплект:\n\n"


    total = 0



    for item in users[chat_id]["cart"]:


        price = int(item["цена"])


        total += price



        text += (

            f"✅ {item['Модель']} — "
            f"{price} ₽\n"

        )



    text += (

        f"\n💰 Итого: {total} ₽"

    )



    keyboard = types.InlineKeyboardMarkup()



    keyboard.add(

        types.InlineKeyboardButton(

            text="Сформировать заказ",

            callback_data="create_order"

        )

    )



    bot.send_message(

        chat_id,

        text,

        reply_markup=keyboard

    )





# ==========================
# ЗАКАЗ
# ==========================


@bot.callback_query_handler(
    func=lambda call:
    call.data == "create_order"
)
def create_order(call):


    chat_id = call.message.chat.id



    text = "📝 Ваш заказ:\n\n"


    total = 0



    for item in users[chat_id]["cart"]:


        price = int(item["цена"])


        total += price



        text += (

            f"{item['Модель']} — "
            f"{price} ₽\n"

        )



    text += (

        f"\nИтого: {total} ₽"

    )



    bot.send_message(

        chat_id,

        text

    )


    bot.send_message(

        chat_id,

        "Спасибо за обращение!\n"
        "Менеджер свяжется с вами."

    )





# ==========================
# ЗАПУСК
# ==========================


print("Бот запущен")


bot.infinity_polling(
    timeout=30,
    long_polling_timeout=30
)