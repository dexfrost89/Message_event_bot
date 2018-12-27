import telebot
import config
import logging
import dbworker
import threading
from datetime import datetime
from telebot import types
from telebot import apihelper

bot = telebot.TeleBot(config.token)
apihelper.proxy = config.proxy

logging.basicConfig(
        format='%(method)s - %(name)s - %(id)s - %(message)s',
        level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class UserInfo:
    def __init__(self, telegram_user, chat):
        self.user = telegram_user
        self.chat = chat
        self.events = {}

    def add_event(self, event):
        event = EventsInfo(event.id, event.time_start, event.time_end, event.priority, event.description, event.notify)
        self.events[int(event.id)] = event

    def delete_event(self, id):
        del self.events[int(id)]

    def print_events(self):
        str = ''
        for key, value in self.events.items():
            event = EventsInfo(value.id, value.time_start, value.time_end, value.priority, value.description, value.notify)
            str += event.print()
            str += '\n'
        return str


class EventsInfo:
    def __init__(self, id = None, time_start = None, time_end = None, priority = None, description = None, notify = None):
        self.id = id
        self.time_start = time_start
        self.time_end = time_end
        self.priority = priority
        self.description = description
        self.notify = notify

    def print(self):
        return ("ID: %s \n"
        "Время начала: %s \n" 
        "Время окончания: %s \n"
        "Приоритет: %s \n"
        "Описание: %s \n"
        "Оповещать за %s минут \n" %
            (self.id,
            self.time_start,
            self.time_end,
            self.priority,
            self.description,
            self.notify))

# Список пользователей
users = {}
current_event = EventsInfo()


def log_params(method_name, message):
    print(str(message))
    logger.debug("Method: %s \n"
                 "From: %s \n"
                 "chat_id: %d \n"
                 "Text: %s \n" %
                (method_name,
                 message.from_user,
                 message.chat.id,
                 message.text))


@bot.message_handler(commands=["help"])
def help(message):
    log_params('help', message)
    bot.send_message(
        message.chat.id,
        text="""
Возможные команды:
/help - Показать помошь
/reset - Сброс состояния
/add_event - Добавить событие
/remove_event - Удалить событие
/change_event - Изменить событие
/get_events - Показать события
""")


# По команде /reset будем сбрасывать состояния, возвращаясь к началу диалога
@bot.message_handler(commands=["reset"])
def reset(message):
    bot.send_message(message.chat.id, "Перешли в главное меню")
    dbworker.set_state(message.chat.id, config.States.S_START.value)


@bot.message_handler(commands=["add_event"])
def add_event(message):
    log_params('add_event', message)
    add(message, message.from_user)


def add(message, user):
    log_params('add_event', message)
    if user.id not in users:
        users[user.id] = UserInfo(user.id, message.chat.id)
    dbworker.set_state(message.chat.id, config.States.S_ENTER_ID.value)
    bot.send_message(message.chat.id, text="Введите ID события")


@bot.message_handler(func=lambda message: dbworker.get_current_state(message.chat.id) == config.States.S_ENTER_ID.value)
def user_entering_id(message):
    if users[message.from_user.id].events:
        for key, event in users[message.from_user.id].events.items():
            if event.id == message.text:
                bot.send_message(message.chat.id, "Такой ID уже занят, введите другой")
                return

    current_event.id = message.text
    bot.send_message(message.chat.id, "Введите дату и время начала события  \n"
                                      "Например: (26 12 2018 12:00)")
    dbworker.set_state(message.chat.id, config.States.S_ENTER_TIME_START.value)


@bot.message_handler(func=lambda message: dbworker.get_current_state(message.chat.id) == config.States.S_ENTER_TIME_START.value)
def user_entering_start(message):
    current_event.time_start = datetime.strptime(message.text, '%d %m %Y %H:%M')
    bot.send_message(message.chat.id, "Введите дату и время окончания события  \n"
                                      "Например: (26 12 2018 12:30)")
    dbworker.set_state(message.chat.id, config.States.S_ENTER_TIME_END.value)


@bot.message_handler(func=lambda message: dbworker.get_current_state(message.chat.id) == config.States.S_ENTER_TIME_END.value)
def user_entering_end(message):
    current_event.time_end = datetime.strptime(message.text, '%d %m %Y %H:%M')
    bot.send_message(message.chat.id, "Введите приоритет важности события")
    dbworker.set_state(message.chat.id, config.States.S_ENTER_PRIORITY.value)


@bot.message_handler(func=lambda message: dbworker.get_current_state(message.chat.id) == config.States.S_ENTER_PRIORITY.value)
def user_entering_priority(message):
    current_event.priority = message.text
    bot.send_message(message.chat.id, "Введите описание события")
    dbworker.set_state(message.chat.id, config.States.S_ENTER_DESCRIPTION.value)


@bot.message_handler(func=lambda message: dbworker.get_current_state(message.chat.id) == config.States.S_ENTER_DESCRIPTION.value)
def user_entering_description(message):
    current_event.description = message.text
    bot.send_message(message.chat.id, "Введите за сколько минут опестить о событии")
    dbworker.set_state(message.chat.id, config.States.S_ENTER_NOTIFY.value)


@bot.message_handler(func=lambda message: dbworker.get_current_state(message.chat.id) == config.States.S_ENTER_NOTIFY.value)
def user_entering_notify(message):
    current_event.notify = message.text
    users[message.from_user.id].add_event(current_event)
    bot.send_message(message.chat.id, "Созданное вами событие:  \n" + str(current_event.print()))
    dbworker.set_state(message.chat.id, config.States.S_START.value)


@bot.message_handler(commands=["remove_event"])
def remove_event(message):
    remove(message, message.from_user)


def remove(message, user):
    log_params('remove_event', message)
    if user.id not in users or (user.id in users and len(users[user.id].events.items()) == 0):
        bot.send_message(message.chat.id, text="У вас еще нет никаких запланированных событий")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(text='Да', callback_data="add"))
        markup.add(types.InlineKeyboardButton(text='Нет', callback_data="reset"))
        bot.send_message(message.chat.id, "Создать событие?", reply_markup=markup)
        return

    dbworker.set_state(message.chat.id, config.States.S_DELETE_EVENT.value)
    bot.send_message(message.chat.id, text="Введите ID события, которое хотите удалить")


@bot.message_handler(func=lambda message: dbworker.get_current_state(message.chat.id) == config.States.S_DELETE_EVENT.value)
def user_delete(message):
    if int(message.text) in users[message.from_user.id].events.keys():
        users[message.from_user.id].delete_event(message.text)
        bot.send_message(message.chat.id, "Удаление успешно")
        dbworker.set_state(message.chat.id, config.States.S_START.value)
    else:
        bot.send_message(message.chat.id, "Введите еще раз")


@bot.message_handler(commands=["change_event"])
def change_event(message):
    get(message, message.from_user)


def change(message, user):
    log_params('change_event', message)
    if user.id not in users or (user.id in users and len(users[user.id].events.items()) == 0):
        bot.send_message(message.chat.id, text="У вас еще нет никаких запланированных событий")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(text='Да', callback_data="add"))
        markup.add(types.InlineKeyboardButton(text='Нет', callback_data="reset"))
        bot.send_message(message.chat.id, "Создать событие?", reply_markup=markup)
        return

    dbworker.set_state(message.chat.id, config.States.S_CHANGE_EVENT.value)
    bot.send_message(message.chat.id, text="Введите ID события, которое хотите изменить")


@bot.message_handler(func=lambda message: dbworker.get_current_state(message.chat.id) == config.States.S_CHANGE_EVENT.value)
def user_changed(message):
    if int(message.text) in users[message.from_user.id].events.keys():
        global current_event
        current_event = users[message.from_user.id].events[int(message.text)]
        bot.send_message(message.chat.id, "Выбранное вами событие:  \n" + str(current_event.print()))

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton(text='Изменить время начала', callback_data="change_time_start"),
               types.InlineKeyboardButton(text='Изменить время окончания', callback_data="change_time_end"),
               types.InlineKeyboardButton(text='Изменить приоритет', callback_data="change_priority"),
               types.InlineKeyboardButton(text='Изменить описание', callback_data="change_description"),
               types.InlineKeyboardButton(text='Изменить время оповещения', callback_data="change_notify"))

    bot.send_message(message.chat.id, "Выберете то, что хотите изменить в событии:", reply_markup=markup)


def change_field(message):
    log_params('change_field', message)
    bot.send_message(message.chat.id, "Введите новое значение")


@bot.message_handler(func=lambda message: dbworker.get_current_state(message.chat.id) == config.States.S_CHANGE_TIME_START.value)
def user_changed_time_start(message):
    current_event.time_start = datetime.strptime(message.text, '%d %m %Y %H:%M')
    bot.send_message(message.chat.id, "Значение 'время начала' изменено")
    users[message.from_user.id].delete_event(current_event.id)
    users[message.from_user.id].add_event(current_event)
    bot.send_message(message.chat.id, "Изменненое событие:  \n" + str(current_event.print()))
    dbworker.set_state(message.chat.id, config.States.S_START.value)


@bot.message_handler(func=lambda message: dbworker.get_current_state(message.chat.id) == config.States.S_CHANGE_TIME_END.value)
def user_changed_time_end(message):
    current_event.time_end = datetime.strptime(message.text, '%d %m %Y %H:%M')
    bot.send_message(message.chat.id, "Значение 'время окончания' изменено")
    users[message.from_user.id].delete_event(current_event.id)
    users[message.from_user.id].add_event(current_event)
    bot.send_message(message.chat.id, "Изменненое событие:  \n" + str(current_event.print()))
    dbworker.set_state(message.chat.id, config.States.S_START.value)


@bot.message_handler(func=lambda message: dbworker.get_current_state(message.chat.id) == config.States.S_CHANGE_PRIORITY.value)
def user_changed_priority(message):
    current_event.priority = message.text
    bot.send_message(message.chat.id, "Значение 'приоритет' изменено")
    users[message.from_user.id].delete_event(current_event.id)
    users[message.from_user.id].add_event(current_event)
    bot.send_message(message.chat.id, "Изменненое событие:  \n" + str(current_event.print()))
    dbworker.set_state(message.chat.id, config.States.S_START.value)


@bot.message_handler(func=lambda message: dbworker.get_current_state(message.chat.id) == config.States.S_CHANGE_DESCRIPTION.value)
def user_changed_description(message):
    current_event.description = message.text
    bot.send_message(message.chat.id, "Значение 'описание' изменено")
    users[message.from_user.id].delete_event(current_event.id)
    users[message.from_user.id].add_event(current_event)
    bot.send_message(message.chat.id, "Изменненое событие:  \n" + str(current_event.print()))
    dbworker.set_state(message.chat.id, config.States.S_START.value)


@bot.message_handler(func=lambda message: dbworker.get_current_state(message.chat.id) == config.States.S_CHANGE_NOTIFY.value)
def user_changed_notify(message):
    current_event.notify = message.text
    bot.send_message(message.chat.id, "Значение 'время оповещения' изменено")
    users[message.from_user.id].delete_event(current_event.id)
    users[message.from_user.id].add_event(current_event)
    bot.send_message(message.chat.id, "Изменненое событие:  \n" + str(current_event.print()))
    dbworker.set_state(message.chat.id, config.States.S_START.value)


@bot.message_handler(commands=["get_events"])
def get_events(message):
    log_params('get_events', message)
    get(message, message.from_user)


def get(message, user):
    log_params('get_events', message)
    if len(users[user.id].events.items()) != 0:
        bot.send_message(message.chat.id, users[user.id].print_events())
    else:
        bot.send_message(message.chat.id, "Событий нет")
    dbworker.set_state(message.chat.id, config.States.S_START.value)


@bot.message_handler(content_types=["text"])
def input_messages(message):
    markup = types.InlineKeyboardMarkup()
    possible_options = 0
    has_delete = has_add = has_change = has_output = False
    keys_for_output = [
        'показать', 'покажи', 'предоставь', 'посмотреть', 'список', 'события', 'вывод',
        'вывести', 'выведи', 'расписание'
    ]
    keys_for_added = [
        'добавь', 'создай', 'добавить', 'создать', 'новое', 'написать', 'напиши'
    ]
    keys_for_deleted = [
        'удали', 'убери', 'удалить', 'убрать', 'очистить', 'стереть', 'стери'
    ]
    keys_for_changed = [
        'поменять', 'изменить', 'поменяй', 'измени', 'поменяй', 'поменять'
    ]
    word_list = message.text.lower().split()
    for word in word_list:
        if word in keys_for_output and not has_output:
            possible_options = possible_options + 1
            markup.add(types.InlineKeyboardButton(text='Вывод событий', callback_data="output"))
            has_output = True
        if word in keys_for_added and not has_add:
            possible_options = possible_options + 1
            markup.add(types.InlineKeyboardButton(text='Добавление событий', callback_data="add"))
            has_add = True
        if word in keys_for_changed and not has_change:
            possible_options = possible_options + 1
            markup.add(types.InlineKeyboardButton(text='Изменение событий', callback_data="change"))
            has_change = True
        if word in keys_for_deleted and not has_delete:
            possible_options = possible_options + 1
            markup.add(types.InlineKeyboardButton(text='Удаление событий', callback_data="delete"))
            has_delete = True
    if possible_options:
        bot.send_message(message.chat.id, "Необходимо выбрать один вариант:", reply_markup=markup)
    else:
        help(message)


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    # Если сообщение из чата с ботом
    if call.message:
        if call.data == "output":
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Вывод")
            get(call.message, call.from_user)
        if call.data == "add":
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Добавление")
            add(call.message, call.from_user)
        if call.data == "change":
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Изменение")
            change(call.message, call.from_user)
        if call.data == "delete":
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Удаление")
            remove(call.message, call.from_user)
        if call.data == "reset":
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Возвращение в главное меню")
            reset(call.message)
        if call.data == "change_time_start":
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Изменение время начала")
            dbworker.set_state(call.message.chat.id, config.States.S_CHANGE_TIME_START.value)
            change_field(call.message)
        if call.data == "change_time_end":
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Изменение время окончания")
            dbworker.set_state(call.message.chat.id, config.States.S_CHANGE_TIME_END.value)
            change_field(call.message)
        if call.data == "change_priority":
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Изменение приоритета")
            dbworker.set_state(call.message.chat.id, config.States.S_CHANGE_PRIORITY.value)
            change_field(call.message)
        if call.data == "change_description":
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Изменение описания")
            dbworker.set_state(call.message.chat.id, config.States.S_CHANGE_DESCRIPTION.value)
            change_field(call.message)
        if call.data == "change_notify":
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Изменение время оповещения")
            dbworker.set_state(call.message.chat.id, config.States.S_CHANGE_NOTIFY.value)
            change_field(call.message)


def check():
    threading.Timer(60.0, check).start()
    if len(users.items()) != 0:
        for k, user in users.items():
            for key, event in user.events.items():
                now = datetime.now()
                if (event.time_start.year == now.year and
                    event.time_start.month == now.month and
                    event.time_start.day == now.day and
                    event.time_start.hour == now.hour and
                    event.time_start.minute == now.minute):
                    bot.send_message(user.chat, "Напоминаем, наступило следующее событие:  \n" + event.print())
check()


if __name__ == '__main__':
    bot.polling(none_stop=True)
