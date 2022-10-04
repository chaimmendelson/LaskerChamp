##############################################################################
#                                server.py                                   #
##############################################################################
import json
import random
import socket
import chess_chatlib as chatlib
import select
import traceback
import logging
import chess_rooms
import time
from datetime import datetime

# GLOBALS
START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
USERS_FILE = "src/users.txt"
MESSAGES_TO_SEND = []
USERS = {}
LOGGED_USERS_CONN = {}
LOGGED_USERS_NAMES = {}  # a dictionary of client hostnames to usernames
WAITING_ROOM = []
PVE_WAITING_FOR_MOVE = []
OPPONENT_QUIT_DURING_TURN = []
ERROR_MSG = "Error!"
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
    rating = str(USERS[username]["rating"])
    build_and_send_message(conn, chatlib.PROTOCOL_SERVER["get_rating_msg"], rating)


def handle_pvp_request_message(conn):
    global WAITING_ROOM
    if WAITING_ROOM:
        player = WAITING_ROOM[0][0]
        chess_rooms.add_room(conn.getpeername(), player.getpeername())
        WAITING_ROOM.remove(WAITING_ROOM[0])
        players = chess_rooms.get_room(player.getpeername()).players
        build_and_send_message(LOGGED_USERS_CONN[players[0]], chatlib.PROTOCOL_SERVER["game_started_msg"], chatlib.join_data(['white', START_FEN]))
        build_and_send_message(LOGGED_USERS_CONN[players[1]], chatlib.PROTOCOL_SERVER["game_started_msg"], chatlib.join_data(['black', START_FEN]))
    else:
        WAITING_ROOM.append([conn, datetime.now()])


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
    peer_name = conn.getpeername()
    state, msg = chess_rooms.commit_move(peer_name, data)
    if not state:
        build_and_send_message(conn, chatlib.PROTOCOL_SERVER['invalid_move_msg'], data)
        return
    if chess_rooms.is_game_over(peer_name):
        handle_game_over(peer_name)
    else:
        data = chatlib.join_data([data, chess_rooms.get_fen(peer_name)])
        build_and_send_message(conn, chatlib.PROTOCOL_SERVER['your_move_msg'], data)
        if chess_rooms.is_pvp_room(peer_name):
            opponent_conn = LOGGED_USERS_CONN[chess_rooms.get_opponent(peer_name)]
            build_and_send_message(opponent_conn, chatlib.PROTOCOL_SERVER['opponent_move_msg'], data)
        else:
            PVE_WAITING_FOR_MOVE.append(peer_name)


def handle_game_over(peer):
    global PVE_WAITING_FOR_MOVE
    result_dict = {-1: chatlib.PROTOCOL_SERVER['tie'],
                   0: chatlib.PROTOCOL_SERVER['you_lost'],
                   1: chatlib.PROTOCOL_SERVER['you_won']}
    msg = chatlib.PROTOCOL_SERVER['game_over_msg']
    opponent = chess_rooms.get_opponent(peer)
    end_move = chess_rooms.get_last_move(peer)
    fen = chess_rooms.get_fen(peer)
    peer_data = chatlib.join_data([result_dict[chess_rooms.get_game_results(peer)], end_move, fen])
    opponent_data = chatlib.join_data([result_dict[chess_rooms.get_game_results(opponent)], end_move, fen])
    build_and_send_message(LOGGED_USERS_CONN[peer], msg, peer_data)
    build_and_send_message(LOGGED_USERS_CONN[opponent], msg, opponent_data)
    chess_rooms.close_room(peer)


def update_pve_players():
    global PVE_WAITING_FOR_MOVE
    temp = []
    for peer in PVE_WAITING_FOR_MOVE:
        if chess_rooms.is_client_turn(peer):
            opponent_move = chess_rooms.get_last_move(peer)
            data = chatlib.join_data([opponent_move, chess_rooms.get_fen(peer)])
            conn = LOGGED_USERS_CONN[peer]
            build_and_send_message(conn, chatlib.PROTOCOL_SERVER['opponent_move_msg'], data)
        else:
            temp.append(peer)
    PVE_WAITING_FOR_MOVE = temp


def handle_logout_message(conn):
    global LOGGED_USERS_NAMES
    client_conn = conn.getpeername()
    if chess_rooms.is_in_room(client_conn):
        opponent = chess_rooms.get_opponent(client_conn)
        if chess_rooms.is_client_turn(client_conn):
            build_and_send_message(LOGGED_USERS_CONN[opponent], chatlib.PROTOCOL_SERVER['opponent_quit_msg'], '')
            chess_rooms.close_room(client_conn)
        else:
            chess_rooms.quit_match(client_conn)
    try:
        del LOGGED_USERS_NAMES[client_conn]
        del LOGGED_USERS_CONN[client_conn]
    except:
        pass
    finally:
        conn.close()
        print("connection closed")


def handle_login_message(conn, data):
    global LOGGED_USERS_NAMES, LOGGED_USERS_CONN
    data = chatlib.split_data(data, 2)
    if data[0] in USERS:
        if data[1] == USERS[data[0]]["password"]:
            if data[0] not in LOGGED_USERS_NAMES.values():
                build_and_send_message(conn, chatlib.PROTOCOL_SERVER["login_ok_msg"], "")
                client_conn = conn.getpeername()
                LOGGED_USERS_NAMES[client_conn] = data[0]
                LOGGED_USERS_CONN[client_conn] = conn
            else:
                build_and_send_message(conn, chatlib.PROTOCOL_SERVER["login_failed_msg"], "user already logged in")
        else:
            build_and_send_message(conn, chatlib.PROTOCOL_SERVER["login_failed_msg"], "password incorrect")
    else:
        build_and_send_message(conn, chatlib.PROTOCOL_SERVER["login_failed_msg"], "user name doesnt exist")


def handle_client_message(conn, cmd, data):
    global OPPONENT_QUIT_DURING_TURN
    client_conn = conn.getpeername()
    if client_conn not in list(LOGGED_USERS_NAMES.keys()):
        if cmd == chatlib.PROTOCOL_CLIENT["login_msg"]:
            handle_login_message(conn, data)
        else:
            build_and_send_message(conn, ERROR_MSG, "first log in")
    elif cmd == chatlib.PROTOCOL_CLIENT["my_move_msg"]:
        if chess_rooms.is_in_room(client_conn):
            if not chess_rooms.did_opponent_quit(client_conn):
                handle_move_message(conn, data)
            else:
                build_and_send_message(conn, chatlib.PROTOCOL_SERVER['opponent_quit_msg'], '')
                chess_rooms.close_room(client_conn)
        else:
            build_and_send_message(conn, chatlib.PROTOCOL_SERVER['not_in_room_msg'], '')
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
            check_waiting_room()
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
