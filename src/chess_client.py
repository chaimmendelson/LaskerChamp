import socket
import chess_chatlib as chatlib

SERVER_IP = "127.0.0.1"  # Our server will run on same computer as client
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
    Parameters: conn (socket object), code (str), data (str)
    Returns: Nothing
    """
    conn.send(chatlib.build_message(code, data).encode())


def recv_message_and_parse(conn):
    """
    Receives a new message from given socket,
    then parses the message using chatlib.
    Parameters: conn (socket object)
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


def print_board(fen):
    between = 2 * ' ' + '|' + ' '
    line = 3 * ' ' + '+' + '----+'*8
    board = fen_to_full_board(fen.split()[0])
    print(line)
    for i in range(8):
        for j in range(len(board[i])):
            board[i][j] = pieces[board[i][j]]
        board[i].insert(0, str(8 - i))
        print(between.join(board[i]) + between)
        print(line)
    print(' '*5 + (' '*4).join(['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']))


def get_rating(conn):
    message_code, data = build_send_recv_parse(conn, chatlib.PROTOCOL_CLIENT["get_my_rating"], "")
    print(message_code, data)


def get_logged_users(conn):
    msg_code, data = build_send_recv_parse(conn, chatlib.PROTOCOL_CLIENT["get_logged_users"], "")
    print(data)


def play_pvp_game(conn):
    msg_code, data = build_send_recv_parse(conn, chatlib.PROTOCOL_CLIENT["multiplayer"], "")
    if msg_code == chatlib.PROTOCOL_SERVER['no_opponent_found_msg']:
        print('no opponent found')
        return
    color, fen = data.split(chatlib.DATA_DELIMITER)
    if color == 'white':
        print_board(fen)
        move = input('enter move: ')
        build_and_send_message(conn, chatlib.PROTOCOL_CLIENT['my_move_msg'], move)
    else:
        print_board(fen)
        print("waiting for opponent move")
    while True:
        msg_code, data = recv_message_and_parse(conn)
        if msg_code == chatlib.PROTOCOL_SERVER['opponent_move_msg']:
            move, fen = chatlib.split_data(data, 2)
            print_board(fen)
            print(f"opponent move was {move}")
            move = input('enter move: ')
            build_and_send_message(conn, chatlib.PROTOCOL_CLIENT['my_move_msg'], move)
        elif msg_code == chatlib.PROTOCOL_SERVER['your_move_msg']:
            move, fen = data.split(chatlib.DATA_DELIMITER, 2)
            print_board(fen)
            print("waiting for opponent move")
        elif msg_code == chatlib.PROTOCOL_SERVER['invalid_move_msg']:
            move = input('enter valid move: ')
            build_and_send_message(conn, chatlib.PROTOCOL_CLIENT['my_move_msg'], move)
        elif msg_code == chatlib.PROTOCOL_SERVER['opponent_quit_msg']:
            print('your opponent has quit the game')
            break
        elif msg_code == chatlib.PROTOCOL_SERVER['game_over_msg']:
            result, move, fen = data.split(chatlib.DATA_DELIMITER, 3)
            print_board(fen)
            print(f"{result}")
            break


def connect():
    the_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    the_socket.connect((SERVER_IP, SERVER_PORT))
    return the_socket


def error_and_exit(error_msg):
    print(error_msg)
    exit()


def login(conn):
    username = input("Please enter username: ")
    password = input("please enter password: ")
    build_and_send_message(conn, chatlib.PROTOCOL_CLIENT["login_msg"], chatlib.join_data([username, password]))
    cmd, data = recv_message_and_parse(conn)
    if cmd == chatlib.PROTOCOL_SERVER["login_ok_msg"]:
        print("logged in")
        return
    print(data)
    login(conn)


def logout(conn):
    build_and_send_message(conn, chatlib.PROTOCOL_CLIENT["logout_msg"], "")
    conn.close()
    print("goodbye")


def main():
    conn = connect()
    login(conn)
    while True:
        print("p        play PvP game\n"
              "s        Get my rating\n"
              "l        Get logged users list\n"
              "q        Quit\n")
        choice = input("Please enter your choice:")
        if choice == "s":
            get_rating(conn)
        elif choice == "p":
            play_pvp_game(conn)
        elif choice == "l":
            get_logged_users(conn)
        elif choice == "q":
            break
    logout(conn)
if __name__ == '__main__':
    main()
