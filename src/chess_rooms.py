import re
import chess.engine
import chess
import platform
from random import shuffle
from stockfish import Stockfish
import threading
if platform.uname().system == 'Windows':
    STOCKFISH_PATH = r"C:\Users\chaim\OneDrive\Desktop\python\stockfish_15_win_x64_avx2\stockfish_15_x64_avx2.exe"
else:
    STOCKFISH_PATH = r"/usr/local/bin/stockfish"
START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'

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


class ChessRoom:

    def __init__(self, player1, player2='stockfish', fen=START_FEN):
        self.players = [player1, player2]
        shuffle(self.players)
        self.board = chess.Board(fen)
        self.opponent_left_match = False

    def __len__(self):
        return len(self.board.move_stack)

    def __str__(self):
        return self.board.fen()

    def __repr__(self):
        return f'chess.Board({self.board.fen()})'

CHESS_ROOMS = []


def quit_match(player):
    get_room(player).opponent_left_match = True


def did_opponent_quit(player):
    return get_room(player).opponent_left_match


def is_pvp_room(player):
    return 'stockfish' not in get_room(player).players


def get_fen(player):
    return str(get_room(player))


def get_opponent(player):
    players = get_room(player).players
    if player == players[0]:
        return players[1]
    return players[0]


def get_last_move(player):
    board = get_room(player).board
    move = board.pop()
    board.push(move)
    return str(move)


def is_client_turn(player) -> bool:
    board = get_room(player).board
    return board.turn != color(player)


def color(player):
    return get_room(player).players.index(player)


def is_game_over(player) -> bool:
    return get_room(player).board.result() != '*'


def get_game_results(player) -> int:
    room = get_room(player)
    if is_game_over(player):
        result = room.board.result().split('-')
        if result[0] == '1/2':
            return -1
        if color(player):
            return int(result[0])
        return int(result[1])
    return None


def commit_move(player, move) -> bool:
    regex = r'^[a-h][1-8][a-h][1-8][q,r,b,n]?$'
    if not re.search(regex, move):
        return False, 'invalid move string'
    board = get_room(player).board
    if not chess.Move.from_uci(move) in board.legal_moves:
        return False, 'invalid move'
    if not is_client_turn(player):
        return False, 'not your turn'
    board.push(chess.Move.from_uci(move))
    return True, ''


def add_room(player1, player2='stockfish', fen=START_FEN) -> None:
    global CHESS_ROOMS
    CHESS_ROOMS.append(ChessRoom(player1, player2, fen))


def is_in_room(player) -> bool:
    for room in CHESS_ROOMS:
        if player in room.players:
            return True
    return False


def get_room(player) -> ChessRoom:
    for room in CHESS_ROOMS:
        if player in room.players:
            return room
    raise ValueError("client is not in a chess room")


def close_room(player) -> None:
    global CHESS_ROOMS
    CHESS_ROOMS.remove(get_room(player))


def commit_engine_move(player, level):
    global ANSWERED
    stockfish = Stockfish(STOCKFISH_PATH)
    stockfish.set_skill_level(level)
    fen = str(get_room(player))
    stockfish.set_fen_position(fen)
    get_room(player).board.push(chess.Move.from_uci(stockfish.get_best_move()))


def get_engine_move(player, level):
    t = threading.Thread(target=commit_engine_move, args=(player, level, ))
    t.start()
    return t


def test():
    end_game_fen = 'R6k/Q7/K7/8/8/8/8/8 b - - 0 0'
    moves = ['f2f3', 'e7e5', 'g2g4', 'd8h4']
    """now = datetime.now()
    for char in ['a', 'b', 'c', 'd', 'e', 'f']:
        add_pve_room(char)
        get_engine_move(char)
    while not did_engine_return('c'):
        pass
    print(ANSWERED)
    now2 = datetime.now()
    print(now2 - now)"""
    player = 'a'
    add_room(player)
    room = get_room(player)
    while True:
        # print_board(room.board.fen())
        t = get_engine_move(player, 10)
        t.join()
        if is_game_over(player):
            break
        # print_board(room.board.fen())
        t = get_engine_move(player, 1)
        t.join()
        if is_game_over(player):
            break
    print_board(room.board.fen())
    print(room.board.result())



def main():
    test()

if __name__ == '__main__':
    main()

"""
רשימה שמכילה את כל מי שמחכה למהלך וברגע שזה תורו סימן שהשני ביצע מהלך, מאוד מקל על הסרדינג ומפחית את העומס קוד סך הכל
בנתיים הסטוקפיש עובד על שתי המערכות הפעלה שזה אחלה, גם מקל על ההרצה של הקוד
צריך לברר איך עושים את הסרדינג לפי הסדר כי זה מאוד מוזר שזה פשוט מסיים כל אחד בזמן אחר
לברר מה שונה בין כל חיבור וחיבור אם זה מתרחש מאותו מחשב ואם יש צורך לעבור לשימוש בשם משמש מה שאוליי קצת יסבך אבל לא בצורה קשה
לנסות למצוא דרך לעקוף את ההורדה של חומת האש כשצריך להתחבר עם מחשב אחר, אוליי להוריד חלק מסויים?
להתמודד טוב גם עם התנתקות של השני מהמשחק לגבי משחק עם מנוע, שלא תקרוס התכנית
להתמודד יותר טוב עם הודעות לא קשורות לדוגמא על הודעה של מהלך כשהוא לא במשחק וכאלה
אוליי פונקציה שבסוף כל ריצה תבדוק מצב של כל הלוחות? או שפשוט עדיף אחרי כל מהלך ואז בנות פונקציה שתודיע ותסגור את החדר
לגבי השורה הראשונה אפשר פשוט לקבל את המהלך האחרון שנעשה... לא בעיה
לבדוק דרך לשמור את כל המהלכים? צ"ע
אם זמן התגובה של המנועים ארוך מדי אוליי למצוא דרך לפתוח פול ככה שהכל יהיה בו-זמנית?
להבין למה הקוד לא מורץ מהטרמינל, מאוד מוזר
אוליי דיווח על הקריסה לכל הקליינטים אחרי שגיאה או שאין צורך
כן להבין איך הקליינט ידע שהשרת קרס וידע לסיים את הריצה או משהו כזה, אוליי לחכות שהשרת יחזור
"""