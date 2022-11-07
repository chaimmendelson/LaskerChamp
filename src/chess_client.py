import socket
import timeit
import time
import chess_chatlib as chatlib
import os_values
import re
from threading import Thread

SERVER_IP = "127.0.0.1"
SERVER_PORT = 5678

# HELPER SOCKET METHODS
pieces = {
    'P': u'\u265F',
    'R': u'\u265C',
    'N': u'\u265E',
    'B': u'\u265D',
    'K': u'\u265A',
    'Q': u'\u265B',
    'p': u'\u2659',
    'r': u'\u2656',
    'n': u'\u2658',
    'b': u'\u2657',
    'k': u'\u2654',
    'q': u'\u2655',
    ' ': ' '
}


def build_send_recv_parse(conn, code, data):
    build_and_send_message(conn, code, data)
    return recv_message_and_parse(conn)


def build_and_send_message(conn, code, data):
    """
    Builds a new message using chatlib, wanted code and message.
    Prints debug info, then sends it to the given socket.
    Parameters: CONN (socket object), code (str), data (str)
    Returns: Nothing
    """
    conn.send(chatlib.build_message(code, data).encode())


def recv_message_and_parse(conn):
    """
    Receives a new message from given socket,
    then parses the message using chatlib.
    Parameters: CONN (socket object)
    Returns: cmd (str) and data (str) of the received message.
    If error occurred, will return None, None"""
    return chatlib.parse_message(conn.recv(1024).decode())


def fen_to_full_board(fen_board) -> list:
    fen_board = fen_board.split('/')
    for i in range(8):
        replacement = []
        for char in fen_board[i]:
            if char.isnumeric():
                for j in range(int(char)):
                    replacement.append(' ')
            else:
                replacement.append(char)
        fen_board[i] = replacement
    return fen_board


def print_board(fen, color):
    between = 2 * ' ' + '|' + ' '
    line = 3 * ' ' + '+' + '----+'*8
    columns = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
    rows = ['8', '7', '6', '5', '4', '3', '2', '1']
    board = fen_to_full_board(fen.split()[0])
    if color == 'black':
        columns.reverse()
        rows.reverse()
        board.reverse()
        for i in range(len(board)):
            board[i].reverse()
    print(line)
    for i in range(8):
        for j in range(len(board[i])):
            board[i][j] = pieces[board[i][j]]
        board[i].insert(0, rows[i])
        print(between.join(board[i]) + between)
        print(line)
    print(' '*5 + (' '*4).join(columns))


def get_rating(conn):
    message_code, data = build_send_recv_parse(conn, chatlib.PROTOCOL_CLIENT["get_my_rating"], "")
    print(message_code, data)


def get_logged_users(conn):
    msg_code, data = build_send_recv_parse(conn, chatlib.PROTOCOL_CLIENT["get_logged_users"], "")
    print(data)


def get_level_choice():
    while True:
        level = input('enter level (0-20): ')
        level_regex = '^(1?[0-9]|20)$'
        if re.search(level_regex, level):
            break
    return level


def get_move_and_send(conn):
    while True:
        move = input('enter move: ')
        if move == 'q':
            x = input('do you really want to quit game? (y/n): ')
            while x not in ['y', 'n']:
                x = input('do you really want to quit game? (y/n): ')
            if x == 'n':
                get_move_and_send(conn)
            else:
                build_and_send_message(conn, chatlib.PROTOCOL_CLIENT["quit_game_msg"], '')
                print("you have quited the game")
                return 'quit'
        elif re.fullmatch(r'^[a-h][1-8][a-h][1-8][qrbn]?$', move):
            break
    build_and_send_message(conn, chatlib.PROTOCOL_CLIENT['my_move_msg'], move)
    return 'sent'


def play_game(conn, pvp=True):
    if pvp:
        msg = chatlib.PROTOCOL_CLIENT["multiplayer"]
        data = ''
    else:
        data = get_level_choice()
        msg = chatlib.PROTOCOL_CLIENT['single-player']
    msg_code, data = build_send_recv_parse(conn, msg, data)
    if msg_code == chatlib.PROTOCOL_SERVER['no_opponent_found_msg']:
        print('no opponent found')
        return
    color, fen = data.split(chatlib.DATA_DELIMITER)
    if color == 'white':
        print_board(fen, color)
        if get_move_and_send(conn) == 'quit':
            return
    else:
        print_board(fen, color)
        print("waiting for opponent move")
    while True:
        msg_code, data = recv_message_and_parse(conn)
        if msg_code == chatlib.PROTOCOL_SERVER['opponent_move_msg']:
            move, fen = chatlib.split_data(data, 2)
            print_board(fen, color)
            print(f"opponent move was {move}")
            if get_move_and_send(conn) == 'quit':
                break
        elif msg_code == chatlib.PROTOCOL_SERVER['your_move_msg']:
            move, fen = data.split(chatlib.DATA_DELIMITER, 2)
            print_board(fen, color)
            print("waiting for opponent move")
        elif msg_code == chatlib.PROTOCOL_SERVER['invalid_move_msg']:
            if get_move_and_send(conn) == 'quit':
                break
        elif msg_code == chatlib.PROTOCOL_SERVER['opponent_quit_msg']:
            print('your opponent has quit the game')
            break
        elif msg_code == chatlib.PROTOCOL_SERVER['game_over_msg']:
            result, move, fen = data.split(chatlib.DATA_DELIMITER, 3)
            print_board(fen, color)
            print(f"{result}")
            break


def connect():
    global SERVER_IP
    # SERVER_IP = os_values.set_server_ip()
    SERVER_IP = '127.0.0.1'
    the_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    the_socket.connect((SERVER_IP, SERVER_PORT))
    return the_socket


def error_and_exit(error_msg):
    print(error_msg)
    exit()


def first_login(conn):
    while True:
        username = input("enter new username: ")
        password = input("enter new password: ")
        email = input("enter your email: ")
        build_and_send_message(conn, chatlib.PROTOCOL_CLIENT["first_login_msg"], chatlib.join_data([username, password, email]))
        cmd, data = recv_message_and_parse(conn)
        if cmd == chatlib.PROTOCOL_SERVER["account_created_msg"]:
            print("account created")
            login(conn)
            break
        elif cmd == chatlib.PROTOCOL_SERVER["invalid_data_msg"]:
            print(data)


def login(conn):
    while True:
        username = input("enter username: ")
        password = input("enter password: ")
        build_and_send_message(conn, chatlib.PROTOCOL_CLIENT["login_msg"], chatlib.join_data([username, password]))
        cmd, data = recv_message_and_parse(conn)
        if cmd == chatlib.PROTOCOL_SERVER["login_ok_msg"]:
            print("logged in")
            break
        print(data)


def logout(conn):
    build_and_send_message(conn, chatlib.PROTOCOL_CLIENT["logout_msg"], "")
    conn.close()
    print("goodbye")


def dos2():
    start = timeit.default_timer()
    for i in range(10000):
        conn = connect()
        logout(conn)
    stop = timeit.default_timer()
    print(stop - start)


def dos():
    conn_list = []
    start = timeit.default_timer()
    for i in range(1000):
        conn_list.append(connect())
    for conn in conn_list:
        build_and_send_message(conn, chatlib.PROTOCOL_CLIENT["login_msg"], chatlib.join_data(['test', 'test1234']))
    stop = timeit.default_timer()
    print(stop - start)

def main():
    conn = connect()
    has_acc = ""
    while has_acc not in ['n', 'y', 'N', 'Y']:
        has_acc = input("do you have an account? (y/n): ")
    if has_acc.lower() == 'y':
        login(conn)
    else:
        first_login(conn)
    while True:
        print("p        Play PvP game\n"
              "e        Play PvE game\n"
              "s        Get my rating\n"
              "l        Get logged users list\n"
              "q        Quit\n")
        choice = input("enter choice:")
        if choice == "s":
            get_rating(conn)
        elif choice == "p":
            play_game(conn)
        elif choice == "e":
            play_game(conn, False)
        elif choice == "l":
            get_logged_users(conn)
        elif choice == "q":
            break
    logout(conn)
if __name__ == '__main__':
    dos2()
