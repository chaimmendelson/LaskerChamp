import os
import sys
import time
import timeit
from platform import uname
import psycopg2 as pg2
from concurrent.futures import ThreadPoolExecutor

CHAIM = 'chaim'
ELCHAI = 'elchai'
CLOUD_SERVER = 'cloud_server'
BAGNO_SERVER = 'bagno_server'
USERS_l = [CHAIM, ELCHAI, CLOUD_SERVER, BAGNO_SERVER]
USER = CHAIM

DB_CONN = None


def set_user():
    global USER
    print("where is the program running?")
    for i in range(len(USERS_l)):
        print(f"{i} - {USERS_l[i]}")
    while True:
        user = input("enter num: ")
        if user.isnumeric():
            user = int(user)
            if user < len(USERS_l):
                break
    USER = USERS_l[user]
    if uname().system == "Linux":
        status = str(os.popen("service postgresql status").read())
        print(status)
        if 'down' in status:
            os.system("sudo service postgresql start")
        print("database operational")
    set_database_conn()


def set_server_ip():
    choice = input("0 - local\n1 - cloud\nenter location: ")
    while choice not in ['0', '1']:
        choice = input("enter location: ")
    if choice == '0':
        return "127.0.0.1"
    return "34.125.51.194"

    
def get_stockfish_path():
    if uname().system == 'Windows' and USER == CHAIM:
        return r"C:\Users\chaim\OneDrive\Desktop\python\stockfish_15_win_x64_avx2\stockfish_15_x64_avx2.exe"
    else:
        if USER == CLOUD_SERVER:
            return r"/home/elchairoy/Stockfish/src/stockfish"
        else:
            return r"/usr/local/bin/stockfish"


def set_database_conn():
    global DB_CONN
    if USER != CHAIM:
        DB_CONN = db2()
    if uname().system == 'Windows' and USER == CHAIM:
        DB_CONN = pg2.connect(database='chess_users', user='postgres', password=132005)
    else:
        connect_str = "dbname='chess_users' user='lasker' host='localhost' password='132005'"
        DB_CONN = pg2.connect(connect_str)

    DB_CONN.autocommit = True


def db2():
    dbname = 'df5ufprlqdf7vu'
    user = 'etclpmibqharrp'
    password = 'aca56302ad12416b27cd971adfb965287a955176c422548782c76e32fba594b0'
    host = 'ec2-52-208-164-5.eu-west-1.compute.amazonaws.com'
    port = '5432'
    return pg2.connect(dbname=dbname, user=user, password=password, host=host, port=port)

def update_elo_tester():
    """
    RatA + K * (score - (1 / (1 + 10(RatB - RatA)/400)))
    K = 400/(games_played**1.5) + 16
    """
    p_elo = 1500
    o_elo = 1500
    p_K = 400 / 1 + 16
    o_K = 400 / 1 + 16
    p_score = 1
    o_score = 0
    p_new_elo = p_elo + p_K * (p_score - (1 / (1 + 10 ** ((o_elo - p_elo) / 400))))
    o_new_elo = o_elo + o_K * (o_score - (1 / (1 + 10 ** ((p_elo - o_elo) / 400))))
    print(p_new_elo)
    print(o_new_elo)


def input_thread(name, age):
    print(f"{name}, {age}\n")


# from multiprocessing.pool import ThreadPool

def main():
    executor = ThreadPoolExecutor(max_workers=10)
    start = timeit.default_timer()
    a = executor.submit(input_thread, 'chaim', 10)
    a.cancel()
    stop = timeit.default_timer()
    print(stop - start)


def send_whatsapp_msg():
    import pywhatkit
    elchai = "+972559328853"
    me = "+972536239778"
    if uname().system == 'Windows':
        pywhatkit.sendwhatmsg_instantly(me, "using a python bot here, just testing", tab_close=True)


if __name__ == '__main__':
    main()
