# Protocol Constants

CMD_FIELD_LENGTH = 32  # Exact length of cmd field (in bytes)
LENGTH_FIELD_LENGTH = 6  # Exact length of length field (in bytes)
MAX_DATA_LENGTH = 10 ** LENGTH_FIELD_LENGTH - 1  # Max size of data field according to protocol
MSG_HEADER_LENGTH = CMD_FIELD_LENGTH + 1 + LENGTH_FIELD_LENGTH + 1  # Exact size of header (CMD+LENGTH fields)
MAX_MSG_LENGTH = MSG_HEADER_LENGTH + MAX_DATA_LENGTH  # Max size of total message
DELIMITER = "|"  # Delimiter character in protocol
DATA_DELIMITER = "#"  # Delimiter in the data part of the message

# Protocol Messages 
# In this dictionary we will have all the client and server command names

PROTOCOL_CLIENT = {
    "login_msg": "LOGIN",
    "first_login_msg": "NEW_LOGIN",
    "logout_msg": "LOGOUT",
    "my_move_msg": "MY_MOVE",
    "get_update": "UPDATE",
    "quit_game_msg": "QUIT_GAME",
    "multiplayer": "PVP",
    "single-player": "PVE",
    "get_my_rating": "MY_RATING",
    "get_logged_users": "LOGGED"
}

PROTOCOL_SERVER = {
    "login_ok_msg": "LOGIN_OK",
    "account_created_msg": "CREATED",
    "server_pending": "PENDING",
    "invalid_data_msg": "INVALID_DATA",
    "login_failed_msg": "ERROR",
    "logged_users": "LOGGED_USERS",
    "looking_for_opponent_msg": "FINDING_OPPONENT",
    "no_opponent_found_msg": "NO_OPPONENT",
    "game_started_msg": "GAME_STARTED",
    "opponent_quit_msg": "OPPONENT_QUIT",
    "your_move_msg": "YOUR_MOVE",
    "invalid_move_msg": "INVALID_MOVE",
    "not_in_room_msg": "NOT_IN_ROOM",
    "opponent_move_msg": "OPPONENT_MOVE",
    "game_over_msg": "GAME_OVER",
    "get_rating_msg": "YOUR_RATING",
    "logged_users_msg": "LOGGED_USERS",
    "no_update_msg": "NO_UPDATE",

    "you_won": "you won",
    "you_lost": 'you lost',
    "tie": 'tie'
}


PROTOCOL_OWNER = {
    "get_all_users": "GET_ALL_USERS",
    "get_blocked_users": "GET_BLOCKED_USERS",
    "get_active_users": "GET_ACTIVE_USERS",
    "unblock_user": "UNBLOCK_USER",
    "delete_user": "DELETE_USER",
    "block_user": "BLOCK_USER",
    "reset_password": "RESET_PASSWORD",
    "add_admin": "ADD_ADMIN",
    "remove_admin": "REMOVE_ADMIN",
    "get_all_games": "GET_ALL_GAMES",
    "spectate_game": "SPECTATE_GAME",
    "get_user_data": "GET_USER_DATA",
}

PROTOCOL_OWNER_SERVER = {
    "all_users": "ALL_USERS",
    "blocked_users": "BLOCKED_USERS",
    "active_users": "ACTIVE_USERS",
    "user_deleted": "USER_DELETED",
    "user_blocked": "USER_BLOCKED",
    "user_unblocked": "USER_UNBLOCKED",
    "password_reset": "PASSWORD_RESET",
    "admin_added": "ADMIN_ADDED",
    "admin_removed": "ADMIN_REMOVED",
    "all_games": "ALL_GAMES",
    "move_made": "MOVE_MADE",
    "game_over": "GAME_OVER ",
    "user_data": "USER_DATA",
}


ERROR_RETURN = None  # What is returned in case of an error


def build_message(cmd, data):
    """
    Gets command name (str) and data field (str) and creates a valid protocol message
    Returns: str, or None if error occurred
    """
    if len(cmd) > CMD_FIELD_LENGTH or len(data) > MAX_DATA_LENGTH:
        return ERROR_RETURN
    cmd += " " * (CMD_FIELD_LENGTH - len(cmd))
    data_len = str(len(data))
    data_len = "0" * (4 - len(data_len)) + data_len
    full_msg = cmd + DELIMITER + data_len + DELIMITER + data
    return full_msg


def parse_message(data):
    """
    Parses protocol message and returns command name and data field
    Returns: cmd (str), data (str). If some error occurred, returns None, None
    """
    if len(data) > MAX_MSG_LENGTH or data.count(DELIMITER) != 2:
        return ERROR_RETURN, ERROR_RETURN
    data = data.split(DELIMITER)
    for char in data[1]:
        if (ord(char) > 57 or ord(char) < 48) and char!= " ":
            return ERROR_RETURN, ERROR_RETURN
    if len(data[0]) > CMD_FIELD_LENGTH or len(data[1]) > LENGTH_FIELD_LENGTH or len(data[2]) != int(data[1]):
        return ERROR_RETURN, ERROR_RETURN
    msg = data[2]
    cmd = data[0].replace(" ", "")
    return cmd, msg


def split_data(msg, expected_fields):
    """
    Helper method. gets a string and number of expected fields in it. Splits the string
    using protocol's data field delimiter (|#) and validates that there are correct number of fields.
    Returns: list of fields if all ok. If some error occurred, returns None
    """
    num_of_split = msg.count(DATA_DELIMITER) + 1
    if expected_fields == num_of_split:
        return msg.split(DATA_DELIMITER)
    else:
        return False


def join_data(msg_fields):
    """
    Helper method. Gets a list, joins all of its fields to one string divided by the data delimiter.
    Returns: string that looks like cell1#cell2#cell3
    """
    msg = ""
    msg_length = len(msg_fields)
    if msg_length != 0:
        for i in range(msg_length - 1):
            msg += msg_fields[i] + DATA_DELIMITER
        msg += msg_fields[-1]
    return msg
