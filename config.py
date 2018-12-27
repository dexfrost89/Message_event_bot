# -*- coding: utf-8 -*-

from enum import Enum

token = '720928388:AAFyPChvMdjRSxwGIVnLIqDjNOp2TALQMcc'
# proxy = {'https': 'socks5://telegram:telegram@nhklb.tgproxy.me:1080'}
# proxy = {'https': 'socks5://581691421:sJceswTF@phobos.public.opennetwork.cc:1090'}
# proxy = {'https': 'socks5://581691421:sJceswTF@deimos.public.opennetwork.cc:1090'}
proxy = {'https': 'socks5://SX1_581691421:mIqWBsktndFW29eE@0x5c.private.ss5.ch:1080'}
# proxy = {'https': 'socks5://telegram.vpn99.net:55655'}

db_file = "database.vdb"


class States(Enum):
    """
    Мы используем БД Vedis, в которой хранимые значения всегда строки,
    поэтому и тут будем использовать тоже строки (str)
    """
    S_START = "0"  # Начало нового диалога
    S_ENTER_ID = "1"
    S_ENTER_TIME_START = "2"
    S_ENTER_TIME_END = "3"
    S_ENTER_PRIORITY = "4"
    S_ENTER_DESCRIPTION = "5"
    S_ENTER_NOTIFY = "6"
    S_DELETE_EVENT = "7"
    S_CHANGE_EVENT = "8"
    S_CHANGE_TIME_START = "9"
    S_CHANGE_TIME_END = "10"
    S_CHANGE_PRIORITY = "11"
    S_CHANGE_DESCRIPTION = "12"
    S_CHANGE_NOTIFY = "13"
    S_SHOW_EVENT = "14"

