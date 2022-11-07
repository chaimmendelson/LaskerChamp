##############################################################################
#                                server.py                                   #
##############################################################################
import socket
import threading
from concurrent.futures import ThreadPoolExecutor

import chess_chatlib as chatlib
import select
import traceback
import logging
import chess_rooms
import time
from datetime import datetime
import re
import handle_database as hd

# GLOBALS
import os_values

EXECUTOR = ThreadPoolExecutor(max_workers=10)
BLACK_LIST = []
MSG_COUNT = {}
LAST_COUNT_RESET = datetime.now()
START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
MESSAGES_TO_SEND = []
LOGGED_USERS_CONN = {}
WAITING_ROOM = {}
OPPONENT_QUIT_DURING_TURN = []
CREATION_THREAD = []
ERROR_MSG = "Error!"
SERVER_PORT = 5678
SERVER_IP = "0.0.0.0"
MAX_MSG_SIZE = 1024


def get_username(conn):
    for username, connection in LOGGED_USERS_CONN.items():
        if conn == connection:
            return username
    return None


def get_conn(username):
    return LOGGED_USERS_CONN[username]


def print_log(conn, msg, from_client=True):
    spaces = 15
    if conn in LOGGED_USERS_CONN.values():
        player = get_username(conn)
    else:
        player = get_ip(conn)
    text = 'sending to'
    if from_client:
        text = 'sent from '
    print(f"{text} [{player}]: {' ' * (spaces - len(player))}{msg}")


def build_and_send_message(conn, code, data):
    global MESSAGES_TO_SEND
    msg = chatlib.build_message(code, data)
    MESSAGES_TO_SEND.append((conn, msg))


def recv_message_and_parse(conn):
    full_msg = conn.recv(MAX_MSG_SIZE).decode()
    cmd, data = chatlib.parse_message(full_msg)
    print_log(conn, full_msg)
    return cmd, data


def setup_socket():
    print("setting up server...")
    while True:
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.bind((SERVER_IP, SERVER_PORT))
            server_socket.listen()
            break
        except:
            time.sleep(1)
    return server_socket


def send_error(conn, error_msg):
    build_and_send_message(conn, ERROR_MSG, error_msg)


def handle_get_rating_message(username):
    rating = str(int(hd.get_elo(username)))
    build_and_send_message(get_conn(username), chatlib.PROTOCOL_SERVER["get_rating_msg"], rating)


def handle_pvp_request_message(username):
    global WAITING_ROOM
    if WAITING_ROOM:
        opponent = list(WAITING_ROOM.keys())[0]
        chess_rooms.add_room(username, opponent)
        del WAITING_ROOM[opponent]
        w_player = chess_rooms.get_white_player(username)
        msg = chatlib.PROTOCOL_SERVER["game_started_msg"]
        build_and_send_message(get_conn(w_player), msg, chatlib.join_data(['white', START_FEN]))
        build_and_send_message(get_conn(chess_rooms.get_opponent(w_player)), msg,
                               chatlib.join_data(['black', START_FEN]))
        hd.update_games_played(username, 1)
        hd.update_games_played(opponent, 1)
    else:
        WAITING_ROOM[username] = datetime.now()


def handle_pve_request_message(username, level):
    color_dict = {0: 'white', 1: 'black'}
    level_regex = '^(1?[0-9]|20)$'
    if not re.search(level_regex, level):
        build_and_send_message(get_conn(username), chatlib.PROTOCOL_SERVER['invalid_level'], '')
    else:
        chess_rooms.add_room(username, level=level)
        color = color_dict[chess_rooms.color(username)]
        msg = chatlib.PROTOCOL_SERVER["game_started_msg"]
        build_and_send_message(get_conn(username), msg, chatlib.join_data([color, START_FEN]))
        if chess_rooms.color(username):
            chess_rooms.update_status(username)


def check_waiting_room():
    global WAITING_ROOM
    waiting_users = list(WAITING_ROOM.keys())
    for user in waiting_users:
        now = datetime.now()
        difference = now - WAITING_ROOM[user]
        if difference.seconds > 60:
            build_and_send_message(get_conn(user), chatlib.PROTOCOL_SERVER["no_opponent_found_msg"], '')
            del WAITING_ROOM[user]


def handle_move_message(username, data):
    if not chess_rooms.is_in_room(username):
        build_and_send_message(get_conn(username), chatlib.PROTOCOL_SERVER['not_in_room_msg'], '')
    elif chess_rooms.did_opponent_quit(username):
        chess_rooms.update_status(username)
        update_quiting_status(username)
    else:
        state, msg = chess_rooms.commit_move(username, data)
        if not state:
            if username in OPPONENT_QUIT_DURING_TURN:
                build_and_send_message(get_conn(username), chatlib.PROTOCOL_SERVER["opponent_quit_msg"], '')
            build_and_send_message(get_conn(username), chatlib.PROTOCOL_SERVER['invalid_move_msg'], data)
        elif chess_rooms.is_game_over(username):
            handle_game_over(username)
        else:
            data = chatlib.join_data([data, chess_rooms.get_fen(username)])
            build_and_send_message(get_conn(username), chatlib.PROTOCOL_SERVER['your_move_msg'], data)


def send_game_over_msg(username):
    result_dict = {-1: chatlib.PROTOCOL_SERVER['tie'],
                   0: chatlib.PROTOCOL_SERVER['you_lost'],
                   1: chatlib.PROTOCOL_SERVER['you_won']}
    msg = chatlib.PROTOCOL_SERVER['game_over_msg']
    end_move = chess_rooms.get_last_move(username)
    fen = chess_rooms.get_fen(username)
    data = chatlib.join_data([result_dict[chess_rooms.get_game_results(username)], end_move, fen])
    build_and_send_message(get_conn(username), msg, data)


def handle_game_over(user):
    send_game_over_msg(user)
    if chess_rooms.is_pvp_room(user):
        send_game_over_msg(chess_rooms.get_opponent(user))
        update_elo(user)
    chess_rooms.close_room(user)


def update_quiting_status(user):
    if chess_rooms.did_opponent_quit(user) and chess_rooms.is_waiting(user):
        build_and_send_message(get_conn(user), chatlib.PROTOCOL_SERVER['opponent_quit_msg'], '')
        chess_rooms.close_room(user)


def update_players():
    for user, conn in LOGGED_USERS_CONN.items():
        if chess_rooms.is_in_room(user):
            update_quiting_status(user)
            if chess_rooms.is_game_over(user):
                handle_game_over(user)
            elif chess_rooms.is_waiting(user):
                if chess_rooms.is_client_turn(user):
                    send_opponent_msg(user)
                elif not chess_rooms.is_pvp_room(user):
                    chess_rooms.get_engine_move(user)


def game_update_req(username):
    if not chess_rooms.is_in_room(username):
        build_and_send_message(get_conn(username), chatlib.PROTOCOL_SERVER['not_in_room_msg'], '')
    if username in OPPONENT_QUIT_DURING_TURN:
        build_and_send_message(get_conn(username), chatlib.PROTOCOL_SERVER["opponent_quit_msg"], '')
    else:
        build_and_send_message(get_conn(username), chatlib.PROTOCOL_SERVER["no_update"], '')


def send_opponent_msg(user):
    opponent_move = chess_rooms.get_last_move(user)
    data = chatlib.join_data([opponent_move, chess_rooms.get_fen(user)])
    build_and_send_message(get_conn(user), chatlib.PROTOCOL_SERVER['opponent_move_msg'], data)
    chess_rooms.update_status(user)


def handle_quit_msg(user):
    if chess_rooms.did_opponent_quit(user):
        chess_rooms.close_room(user)
    else:
        if chess_rooms.is_pvp_room(user):
            update_elo(user, False)
            chess_rooms.quit_match(user)
        else:
            chess_rooms.close_room(user)


def update_elo(user, is_game_over=True):
    """
    RatA + K * (score - (1 / (1 + 10(RatB - RatA)/400)))
    K = 400/(games_played**1.5) + 16
    """
    p_username = user
    o_username = chess_rooms.get_opponent(user)
    p_elo = float(hd.get_elo(p_username))
    o_elo = float(hd.get_elo(o_username))
    p_K = 400 / (hd.get_games_played(p_username)) + 16
    o_K = 400 / (hd.get_games_played(o_username)) + 16
    if not is_game_over:
        p_score = 0
        o_score = 1
    else:
        p_score = chess_rooms.get_game_results(user)
        o_score = chess_rooms.get_game_results(chess_rooms.get_opponent(user))
    p_new_elo = p_elo + p_K * (p_score - (1 / (1 + 10 ** ((o_elo - p_elo) / 400))))
    o_new_elo = o_elo + o_K * (o_score - (1 / (1 + 10 ** ((p_elo - o_elo) / 400))))
    hd.update_elo(p_username, p_new_elo)
    hd.update_elo(o_username, o_new_elo)


def handle_logout_message(conn):
    global LOGGED_USERS_CONN, WAITING_ROOM
    user = get_ip(conn)
    if conn in LOGGED_USERS_CONN.values():
        user = get_username(conn)
        if user in list(WAITING_ROOM.keys()):
            del WAITING_ROOM[user]
        if chess_rooms.is_in_room(user):
            handle_quit_msg(user)
        del LOGGED_USERS_CONN[get_username(conn)]
    conn.close()
    print(f"connection to {user} closed")


def handle_login_message(conn, data):
    global LOGGED_USERS_NAMES, LOGGED_USERS_CONN
    data = chatlib.split_data(data, 2)
    if not data:
        build_and_send_message(conn, chatlib.PROTOCOL_SERVER["login_failed_msg"], "invalid value count")
        return
    username, password = data
    if hd.does_username_exist(username):
        if hd.check_password(username, password):
            if username not in LOGGED_USERS_CONN.keys():
                build_and_send_message(conn, chatlib.PROTOCOL_SERVER["login_ok_msg"], "")
                LOGGED_USERS_CONN[username] = conn
                hd.update_entry(username)
            else:
                build_and_send_message(conn, chatlib.PROTOCOL_SERVER["login_failed_msg"], "user already logged in")
        else:
            build_and_send_message(conn, chatlib.PROTOCOL_SERVER["login_failed_msg"], "password incorrect")
    else:
        build_and_send_message(conn, chatlib.PROTOCOL_SERVER["login_failed_msg"], "user name doesnt exist")


def registration_thread(conn, data):
    global CREATION_THREAD
    status = hd.create_new_user(data[0], data[1], data[2])
    if status == "account created":
        build_and_send_message(conn, chatlib.PROTOCOL_SERVER['account_created_msg'], "")
    else:
        build_and_send_message(conn, chatlib.PROTOCOL_SERVER['invalid_data_msg'], status)
    CREATION_THREAD.remove(conn.getpeername())


def handle_registration_message(conn, data):
    global CREATION_THREAD
    data = chatlib.split_data(data, 3)
    if not data:
        msg = "please send username, password and email account"
        build_and_send_message(conn, chatlib.PROTOCOL_SERVER['invalid_data_msg'], msg)
        return
    CREATION_THREAD.append(conn.getpeername())
    EXECUTOR.submit(registration_thread, conn, data)


def handle_client_message(conn, cmd, data):
    global OPPONENT_QUIT_DURING_TURN
    client_conn = conn.getpeername()
    if conn not in list(LOGGED_USERS_CONN.values()):
        if client_conn in CREATION_THREAD:
            build_and_send_message(conn, chatlib.PROTOCOL_SERVER["server_pending"], "creating account")
        elif cmd == chatlib.PROTOCOL_CLIENT["login_msg"]:
            handle_login_message(conn, data)
        elif cmd == chatlib.PROTOCOL_CLIENT["first_login_msg"]:
            handle_registration_message(conn, data)
        else:
            build_and_send_message(conn, ERROR_MSG, "first log in")
        return
    username = get_username(conn)
    if cmd == chatlib.PROTOCOL_CLIENT["my_move_msg"]:
        handle_move_message(username, data)
    elif cmd == chatlib.PROTOCOL_CLIENT["quit_game_msg"]:
        handle_quit_msg(username)
    elif cmd == chatlib.PROTOCOL_CLIENT["get_update"]:
        game_update_req(username)
    elif cmd == chatlib.PROTOCOL_CLIENT["get_my_rating"]:
        handle_get_rating_message(username)
    elif cmd == chatlib.PROTOCOL_CLIENT["multiplayer"]:
        handle_pvp_request_message(username)
    elif cmd == chatlib.PROTOCOL_CLIENT["single-player"]:
        handle_pve_request_message(username, data)
    elif cmd == chatlib.PROTOCOL_CLIENT["get_logged_users"]:
        handle_logged_message(username)
    else:
        build_and_send_message(conn, ERROR_MSG, "command does not exist")


def handle_logged_message(user):
    conn_list = list(LOGGED_USERS_CONN)
    logged = chatlib.join_data(conn_list)
    if len(logged) > 1:
        chatlib.join_data(logged)
    build_and_send_message(get_conn(user), chatlib.PROTOCOL_SERVER["logged_users"], logged)


def print_client_sockets():
    logged_list = list(LOGGED_USERS_CONN.keys())
    for c in logged_list:
        print(f"{c}\t")


def get_ip(conn):
    try:
        ip = conn.getpeername()[0]
    except OSError:
        ip = '0.0.0.0'
    return ip


def update_black_list(client_conn: socket.socket, clients: list) -> list:
    global BLACK_LIST
    ip = get_ip(client_conn)
    client_conn.close()
    BLACK_LIST.append(ip)
    temp = clients.copy()
    for conn in temp:
        if get_ip(conn) == ip:
            handle_logout_message(conn)
            clients.remove(conn)
    return clients


def update_msg_follow():
    global MSG_COUNT, LAST_COUNT_RESET
    now = datetime.now()
    difference = now - LAST_COUNT_RESET
    if difference.seconds > 1:
        MSG_COUNT = {}
        LAST_COUNT_RESET = datetime().now()


def msg_count_update(client_conn, clients):
    global MSG_COUNT
    ip = get_ip(client_conn)
    if ip in MSG_COUNT:
        MSG_COUNT[ip] += 1
        if MSG_COUNT[ip] >= 5:
            return update_black_list(client_conn, clients)
    else:
        MSG_COUNT[ip] = 1
    return clients
            


def main():
    global MESSAGES_TO_SEND, BLACK_LIST
    print("Welcome to chess Server!")
    server_socket = setup_socket()
    os_values.set_user()
    # hd.reset_table()
    print("listening for clients...")
    client_sockets = []
    try:
        while True:
            update_msg_follow()
            check_waiting_room()
            update_players()
            ready_to_read, ready_to_write, in_error = select.select([server_socket] + client_sockets, client_sockets, [])
            for current_socket in ready_to_read:
                if current_socket is server_socket:
                    (client_socket, client_address) = current_socket.accept()
                    ip = get_ip(client_socket)
                    if ip in BLACK_LIST:
                        client_socket.close()
                    else:
                        count = len(list(filter(lambda obj: get_ip(obj) == ip, client_sockets)))
                        if count < 5:
                            print("new client joined!", client_address)
                            client_sockets.append(client_socket)
                        else:
                            client_sockets = update_black_list(client_socket, client_sockets)
                else:
                    try:
                        cmd, data = recv_message_and_parse(current_socket)
                    except ConnectionResetError:
                        print(1)
                        client_sockets.remove(current_socket)
                        handle_logout_message(current_socket)
                    else:
                        if cmd == "" or cmd is None or cmd == chatlib.PROTOCOL_CLIENT["logout_msg"]:
                            print(2)

                            client_sockets.remove(current_socket)
                            handle_logout_message(current_socket)
                        else:
                            handle_client_message(current_socket, cmd, data)
            for message in MESSAGES_TO_SEND:
                conn, data = message
                if conn in ready_to_write:
                    print_log(conn, data, from_client=False)
                    conn.send(data.encode())
                    MESSAGES_TO_SEND.remove(message)
    except:
        server_socket.close()
        os_values.DB_CONN.close()
        print("\nserver crash due to an unexpected error as shown below")
        logging.error(traceback.format_exc())


if __name__ == '__main__':
    main()
    