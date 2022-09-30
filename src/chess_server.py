##############################################################################
#                                server.py                                   #
##############################################################################
import json
import random
import socket
import chess_chatlib as chatlib
import select
import requests
import traceback
import logging
import re
import chess_rooms

# GLOBALS
START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
USERS_FILE = "src/users.txt"
MESSAGES_TO_SEND = []
USERS = {}
LOGGED_USERS_CONN = {}
LOGGED_USERS_NAMES = {}  # a dictionary of client hostnames to usernames
WAITING_ROOM = []
PLAYERS_IN_ROOMS = []
ERROR_MSG = "Error! "
SERVER_PORT = 5678
SERVER_IP = "0.0.0.0"
MAX_MSG_SIZE = 1024


# HELPER SOCKET METHODS


def build_and_send_message(conn, code, data):
    global MESSAGES_TO_SEND
    msg = chatlib.build_message(code, data)
    MESSAGES_TO_SEND.append((conn, msg))


def recv_message_and_parse(conn):
    full_msg = conn.recv(MAX_MSG_SIZE).decode()
    cmd, data = chatlib.parse_message(full_msg)
    print("[CLIENT] ", full_msg)
    return cmd, data


def load_user_database():
    with open(USERS_FILE, "r") as codes_file:
        return json.loads(codes_file.read())


def update_user_data():
    data = json.dumps(USERS)
    with open('src/users.txt', "w") as change:
        change.write(data)


def setup_socket():
    print("setting up server...")
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((SERVER_IP, SERVER_PORT))
    server_socket.listen()
    return server_socket


def send_error(conn, error_msg):
    build_and_send_message(conn, ERROR_MSG + error_msg)


def handle_get_rating_message(conn, username):
    rating = str(USERS[username]["rating"])
    build_and_send_message(conn, chatlib.PROTOCOL_SERVER["get_rating_msg"], rating)


def handle_pvp_request_message(conn):
    global WAITING_ROOM
    if WAITING_ROOM:
        players = [WAITING_ROOM[0], conn]
        random.shuffle(players)
        chess_rooms.add_room(players[0].getpeername(), players[1].getpeername())
        WAITING_ROOM.remove(WAITING_ROOM[0])
        build_and_send_message(players[0], chatlib.PROTOCOL_SERVER["game_started_msg"], 'white' + chatlib.DATA_DELIMITER + START_FEN)
        build_and_send_message(players[1], chatlib.PROTOCOL_SERVER["game_started_msg"], 'black' + chatlib.DATA_DELIMITER + START_FEN)
    else:
        WAITING_ROOM.append(conn)


def handle_move_message(conn, data):
    if not chess_rooms.is_client_turn(conn.getpeername()):
        build_and_send_message(conn, ERROR_MSG, "wait for opponent to make a move")
    else:
        if not chess_rooms.commit_move_if_valid(conn.getpeername(), data):
            build_and_send_message(conn, chatlib.PROTOCOL_SERVER['invalid_move_msg'], '')
            return
        fen = chess_rooms.get_client_board(conn.getpeername()).board_fen()
        opponent = LOGGED_USERS_CONN[chess_rooms.get_opponent(conn.getpeername())]
        build_and_send_message(conn, chatlib.PROTOCOL_SERVER["your_move_msg"], data + chatlib.DATA_DELIMITER + fen)
        build_and_send_message(opponent, chatlib.PROTOCOL_SERVER["opponent_move_msg"], data + chatlib.DATA_DELIMITER + fen)


def handle_logout_message(conn):
    global LOGGED_USERS_NAMES
    client_conn = conn.getpeername()
    try:
        del LOGGED_USERS_NAMES[client_conn]
        del LOGGED_USERS_CONN[client_conn]
    except:
        pass
    finally:
        conn.close()
        print("connection closed")


def handle_login_message(conn, data):
    global USERS
    global LOGGED_USERS_NAMES
    data = chatlib.split_data(data, 1)
    if data[0] in USERS:
        if data[1] == USERS[data[0]]["password"]:
            build_and_send_message(conn, chatlib.PROTOCOL_SERVER["login_ok_msg"], "")
            client_conn = conn.getpeername()
            LOGGED_USERS_NAMES[client_conn] = data[0]
            LOGGED_USERS_CONN[client_conn] = conn
        else:
            build_and_send_message(conn, chatlib.PROTOCOL_SERVER["login_failed_msg"], "password incorrect")
    else:
        build_and_send_message(conn, chatlib.PROTOCOL_SERVER["login_failed_msg"], "user name doesnt exist")


def handle_client_message(conn, cmd, data):
    client_conn = conn.getpeername()
    if client_conn not in list(LOGGED_USERS_NAMES.keys()):
        if cmd == chatlib.PROTOCOL_CLIENT["login_msg"]:
            handle_login_message(conn, data)
        else:
            build_and_send_message(conn, ERROR_MSG, "first log in")
    elif chess_rooms.is_client_in_room(client_conn):
        if cmd == chatlib.PROTOCOL_CLIENT["my_move_msg"]:
            handle_move_message(conn, data)
        else:
            build_and_send_message(conn, ERROR_MSG, "you are currently in game")
    elif cmd == chatlib.PROTOCOL_CLIENT["get_my_rating"]:
        handle_get_rating_message(conn, LOGGED_USERS_NAMES[client_conn])
    elif cmd == chatlib.PROTOCOL_CLIENT["multiplayer"]:
        handle_pvp_request_message(conn)
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
        print("{}\t".format(c))


def main():
    global USERS
    global MESSAGES_TO_SEND
    print("Welcome to chess Server!")
    USERS = load_user_database()
    server_socket = setup_socket()
    print("listening for clients...")
    client_sockets = []
    try:
        while True:
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
                    print("[SERVER]  {}".format(data))
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
