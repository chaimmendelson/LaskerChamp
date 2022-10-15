import os
from platform import uname
import psycopg2 as pg2
CHAIM = 'chaim'
ELCHAI = 'elchai'
SERVER = 'server'
USERS_l = [CHAIM, ELCHAI, SERVER]
USER = CHAIM


def set_user():
    global USER
    print("where is the program running?")
    for i in range(len(USERS_l)):
        print(f"{i} - {USERS_l[i]}")
    while True:
        user = input("enter num: ")
        if user.isnumeric():
            user = int(user)
            if user < len(USERS_l) - 1:
                break
    USER = USERS_l[user]
    if uname().system == "Linux":
        status = str(os.popen("service postgresql status").read())
        print(status)
        if 'down' in status:
            os.system("sudo service postgresql start")
        print("database operational")


def get_stockfish_path():
    if uname().system == 'Windows' and USER == CHAIM:
        return r"C:\Users\chaim\OneDrive\Desktop\python\stockfish_15_win_x64_avx2\stockfish_15_x64_avx2.exe"
    else:
        if USER == SERVER:
            return r"/home/elchairoy/Stockfish/src/stockfish"
        else:
            return r"/usr/local/bin/stockfish"


def get_database_conn():
    if uname().system == 'Windows' and USER == CHAIM:
        return pg2.connect(database='chess_users', user='postgres', password=132005)
    else:
        connect_str = "dbname='chess_users' user='lasker' host='localhost' password='132005'"
        return pg2.connect(connect_str)