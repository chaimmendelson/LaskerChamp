import re
import chess
chrs = {
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
CHESS_ROOMS = {}
START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'


def add_room(peer1, peer2, fen=START_FEN):
    global CHESS_ROOMS
    CHESS_ROOMS[(peer1, peer2)] = chess.Board(fen)


def is_client_in_room(peer):
    rooms_dict = list(CHESS_ROOMS.keys())
    for i in range(len(rooms_dict)):
        if peer in rooms_dict[i]:
            return True
    return False


def get_client_room(peer):
    rooms_dict = list(CHESS_ROOMS.keys())
    for i in range(len(rooms_dict)):
        if peer in rooms_dict[i]:
            return rooms_dict[i]
    raise ValueError("client is not in a chess room")


def get_opponent(peer):
    opponent = list(get_client_room(peer))
    opponent.remove(peer)
    return opponent[0]


def is_client_turn(peer):
    return get_client_board(peer).turn != get_client_room(peer).index(peer)


def get_client_board(peer):
    return CHESS_ROOMS[get_client_room(peer)]


def commit_move_if_valid(peer, move):
    regex = r'^[a-h][1-8][a-h][1-8][q,r,b,n]?$'
    if not re.search(regex, move):
        return False
    board = get_client_board(peer)
    if not chess.Move.from_uci(move) in board.legal_moves:
        return False
    board.push(chess.Move.from_uci(move))
    return True


def fen_to_full_board(fen_board):
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
    left_offset = 3 * ' '
    between = 2 * ' ' + '|' + ' '
    line = left_offset + '+' + '----+'*8
    board = fen_to_full_board(fen.split()[0])
    print(line)
    for i in range(8):
        for j in range(len(board[i])):
            board[i][j] = chrs[board[i][j]]
        board[i].insert(0, str(8 - i))
        print(between.join(board[i]) + between)
        print(line)
    print(' '*5 + (' '*4).join(['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']))


def test():
    fen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
    end_game_fen = 'R6k/Q7/K7/8/8/8/8/8 b - - 0 0'
    move = 'e2e4'
    move2 = 'e7e6'
    move3 = 'e1e2'
    """fen = commite_move(fen, 'e2e4')
    print_board(fen)
    fen = commite_move(fen, 'e7e5')
    print_board(fen)"""
    #print(is_move_string_valid('a1a2q\na1a2'))
    board = chess.Board(end_game_fen)
    fen = board.board_fen()
    print(fen)
    print(board.result())
test()