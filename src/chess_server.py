##############################################################################
#                                server.py                                   #
##############################################################################
import socket
import threading

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
START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
MESSAGES_TO_SEND = []
LOGGED_USERS_CONN = {}
LOGGED_USERS_NAMES = {}  # a dictionary of client hostnames to usernames
WAITING_ROOM = []
OPPONENT_QUIT_DURING_TURN = []
CREATION_THREAD = []
ERROR_MSG = "Error!"
SERVER_PORT = 5678
SERVER_IP = "0.0.0.0"
MAX_MSG_SIZE = 1024


def build_and_send_message(conn, code, data):
    global MESSAGES_TO_SEND
    msg = chatlib.build_message(code, data)
    MESSAGES_TO_SEND.append((conn, msg))


def recv_message_and_parse(conn):
    full_msg = conn.recv(MAX_MSG_SIZE).decode()
    cmd, data = chatlib.parse_message(full_msg)
    print("[CLIENT] ", full_msg)
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
            time.sleep(5)
    return server_socket


def send_error(conn, error_msg):
    build_and_send_message(conn, ERROR_MSG, error_msg)


def handle_get_rating_message(conn, username):
    rating = hd.get_elo(username)
    build_and_send_message(conn, chatlib.PROTOCOL_SERVER["get_rating_msg"], rating)


def handle_pvp_request_message(conn):
    global WAITING_ROOM
    if WAITING_ROOM:
        player = WAITING_ROOM[0][0]
        chess_rooms.add_room(conn.getpeername(), player.getpeername())
        WAITING_ROOM.remove(WAITING_ROOM[0])
        player = chess_rooms.get_white_player(player.getpeername())
        msg = chatlib.PROTOCOL_SERVER["game_started_msg"]
        build_and_send_message(LOGGED_USERS_CONN[player], msg, chatlib.join_data(['white', START_FEN]))
        build_and_send_message(LOGGED_USERS_CONN[chess_rooms.get_opponent(player)], msg, chatlib.join_data(['black', START_FEN]))
    else:
        WAITING_ROOM.append([conn, datetime.now()])


def handle_pve_request_message(conn, level):
    color_dict = {0: 'white', 1: 'black'}
    player = conn.getpeername()
    level_regex = '^(1?[0-9]|20)$'
    if not re.search(level_regex, level):
        build_and_send_message(conn, chatlib.PROTOCOL_SERVER['invalid_level'], '')
    else:
        chess_rooms.add_room(conn.getpeername(), level=level)
        color = color_dict[chess_rooms.color(player)]
        msg = chatlib.PROTOCOL_SERVER["game_started_msg"]
        build_and_send_message(LOGGED_USERS_CONN[player], msg, chatlib.join_data([color, START_FEN]))
        if chess_rooms.color(player):
            chess_rooms.update_status(player)


def check_waiting_room():
    global WAITING_ROOM
    temp_waiting_room = []
    for i in range(len(WAITING_ROOM)):
        now = datetime.now()
        difference = now - WAITING_ROOM[i][1]
        if difference.seconds > 60:
            build_and_send_message(WAITING_ROOM[i][0], chatlib.PROTOCOL_SERVER["no_opponent_found_msg"], '')
        else:
            temp_waiting_room.append(WAITING_ROOM[i])
    WAITING_ROOM = temp_waiting_room


def handle_move_message(conn, data):
    player = conn.getpeername()
    if not chess_rooms.is_in_room(player):
        build_and_send_message(conn, chatlib.PROTOCOL_SERVER['not_in_room_msg'], '')
    elif chess_rooms.did_opponent_quit(player):
        chess_rooms.update_status(player)
        update_quiting_status(player)
        return
    else:
        state, msg = chess_rooms.commit_move(player, data)
        if not state:
            build_and_send_message(conn, chatlib.PROTOCOL_SERVER['invalid_move_msg'], data)
        elif chess_rooms.is_game_over(player):
            handle_game_over(player)
        else:
            data = chatlib.join_data([data, chess_rooms.get_fen(player)])
            build_and_send_message(conn, chatlib.PROTOCOL_SERVER['your_move_msg'], data)


def send_game_over_msg(player):
    result_dict = {-1: chatlib.PROTOCOL_SERVER['tie'],
                   0: chatlib.PROTOCOL_SERVER['you_lost'],
                   1: chatlib.PROTOCOL_SERVER['you_won']}
    msg = chatlib.PROTOCOL_SERVER['game_over_msg']
    end_move = chess_rooms.get_last_move(player)
    fen = chess_rooms.get_fen(player)
    data = chatlib.join_data([result_dict[chess_rooms.get_game_results(player)], end_move, fen])
    build_and_send_message(LOGGED_USERS_CONN[player], msg, data)


def handle_game_over(player):
    send_game_over_msg(player)
    if chess_rooms.is_pvp_room(player):
        send_game_over_msg(chess_rooms.get_opponent(player))
    chess_rooms.close_room(player)


def update_quiting_status(player):
    opponent = chess_rooms.get_opponent(chess_rooms.get_quiting_player(player))
    if chess_rooms.is_client_turn(opponent) and not chess_rooms.is_waiting(player):
        return
    if chess_rooms.is_pvp_room(player):
        build_and_send_message(LOGGED_USERS_CONN[opponent], chatlib.PROTOCOL_SERVER['opponent_quit_msg'], '')
    chess_rooms.close_room(player)


def update_players():
    for player, conn in LOGGED_USERS_CONN.items():
        if chess_rooms.is_in_room(player):
            if chess_rooms.is_game_over(player):
                handle_game_over(player)
            elif chess_rooms.did_opponent_quit(player):
                update_quiting_status(player)
            elif chess_rooms.is_waiting(player):
                if chess_rooms.is_client_turn(player):
                    send_opponent_msg(player)
                elif not chess_rooms.is_pvp_room(player):
                    chess_rooms.get_engine_move(player)


def send_opponent_msg(player):
    opponent_move = chess_rooms.get_last_move(player)
    data = chatlib.join_data([opponent_move, chess_rooms.get_fen(player)])
    build_and_send_message(LOGGED_USERS_CONN[player], chatlib.PROTOCOL_SERVER['opponent_move_msg'], data)
    chess_rooms.update_status(player)


def handle_quit_msg(player):
    if chess_rooms.did_opponent_quit(player):
        chess_rooms.close_room(player)
    else:
        chess_rooms.quit_match(player)


def handle_logout_message(conn):
    global LOGGED_USERS_NAMES
    player = conn.getpeername()
    if chess_rooms.is_in_room(player):
        handle_quit_msg(player)
    try:
        del LOGGED_USERS_NAMES[player]
        del LOGGED_USERS_CONN[player]
    except:
        pass
    finally:
        conn.close()
        print("connection closed")


def handle_login_message(conn, data):
    global LOGGED_USERS_NAMES, LOGGED_USERS_CONN
    data = chatlib.split_data(data, 2)
    if not data:
        build_and_send_message(conn, chatlib.PROTOCOL_SERVER["login_failed_msg"], "invalid value count")
        return
    username, password = data
    if hd.does_username_exist(username):
        if hd.check_password(username, password):
            if username not in LOGGED_USERS_NAMES.values():
                build_and_send_message(conn, chatlib.PROTOCOL_SERVER["login_ok_msg"], "")
                client_conn = conn.getpeername()
                LOGGED_USERS_NAMES[client_conn] = username
                LOGGED_USERS_CONN[client_conn] = conn
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
        build_and_send_message(conn, chatlib.PROTOCOL_SERVER["account_created_msg"], "")
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
    threading.Thread(target=registration_thread, args=(conn, data, )).start()


def handle_client_message(conn, cmd, data):
    global OPPONENT_QUIT_DURING_TURN
    client_conn = conn.getpeername()
    if client_conn not in list(LOGGED_USERS_NAMES.keys()):
        if client_conn in CREATION_THREAD:
            build_and_send_message(conn, chatlib.PROTOCOL_SERVER["server_pending"], "creating account")
        if cmd == chatlib.PROTOCOL_CLIENT["login_msg"]:
            handle_login_message(conn, data)
        elif cmd == chatlib.PROTOCOL_CLIENT["first_login_msg"]:
            handle_registration_message(conn, data)
        else:
            build_and_send_message(conn, ERROR_MSG, "first log in")
    elif cmd == chatlib.PROTOCOL_CLIENT["my_move_msg"]:
        handle_move_message(conn, data)
    elif cmd == chatlib.PROTOCOL_CLIENT["get_my_rating"]:
        handle_get_rating_message(conn, LOGGED_USERS_NAMES[client_conn])
    elif cmd == chatlib.PROTOCOL_CLIENT["multiplayer"]:
        handle_pvp_request_message(conn)
    elif cmd == chatlib.PROTOCOL_CLIENT["single-player"]:
        handle_pve_request_message(conn, data)
    elif cmd == chatlib.PROTOCOL_CLIENT["get_logged_users"]:
        handle_logged_message(conn)
    else:
        build_and_send_message(conn, ERROR_MSG, "command does not exist")


def handle_logged_message(conn):
    conn_list = list(LOGGED_USERS_NAMES.values())
    logged = chatlib.join_data(conn_list)
    if len(logged) > 1:
        chatlib.join_data(logged)
    build_and_send_message(conn, chatlib.PROTOCOL_SERVER["logged_users"], logged)


def print_client_sockets():
    logged_list = list(LOGGED_USERS_NAMES.keys())
    for c in logged_list:
        print(f"{c}\t")


def main():
    global MESSAGES_TO_SEND
    print("Welcome to chess Server!")
    hd.db.reset_table()
    server_socket = setup_socket()
    print("listening for clients...")
    client_sockets = []
    try:
        while True:
            check_waiting_room()
            update_players()
            ready_to_read, ready_to_write, in_error = select.select([server_socket] + client_sockets, client_sockets, [])
            for current_socket in ready_to_read:
                if current_socket is server_socket:
                    (client_socket, client_address) = current_socket.accept()
                    print("new client joined!", client_address)
                    client_sockets.append(client_socket)
                else:
                    print("new data from client")
                    try:
                        cmd, data = recv_message_and_parse(current_socket)
                    except ConnectionResetError:
                        client_sockets.remove(current_socket)
                        handle_logout_message(current_socket)
                        print_client_sockets()
                    else:
                        if cmd == "" or cmd is None or cmd == chatlib.PROTOCOL_CLIENT["logout_msg"]:
                            client_sockets.remove(current_socket)
                            handle_logout_message(current_socket)
                            print_client_sockets()
                        else:
                            handle_client_message(current_socket, cmd, data)
            for message in MESSAGES_TO_SEND:
                c, data = message
                if c in ready_to_write:
                    print(f"[SERVER]  {data}")
                    c.send(data.encode())
                    MESSAGES_TO_SEND.remove(message)
    except:
        conn_list = list(LOGGED_USERS_CONN.values())
        for client in conn_list:
            handle_logout_message(client)
        server_socket.close()
        print("\nserver crash due to an unexpected error as shown below")
        logging.error(traceback.format_exc())


if __name__ == '__main__':
    main()
