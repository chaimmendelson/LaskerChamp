# Protocol Constants

CMD_FIELD_LENGTH = 32  # Exact length of cmd field (in bytes)
LENGTH_FIELD_LENGTH = 4  # Exact length of length field (in bytes)
MAX_DATA_LENGTH = 10 ** LENGTH_FIELD_LENGTH - 1  # Max size of data field according to protocol
MSG_HEADER_LENGTH = CMD_FIELD_LENGTH + 1 + LENGTH_FIELD_LENGTH + 1  # Exact size of header (CMD+LENGTH fields)
MAX_MSG_LENGTH = MSG_HEADER_LENGTH + MAX_DATA_LENGTH  # Max size of total message
DELIMITER = "|"  # Delimiter character in protocol
DATA_DELIMITER = "#"  # Delimiter in the data part of the message

# Protocol Messages 
# In this dictionary we will have all the client and server command names

PROTOCOL_CLIENT = {
    "login_msg": "LOGIN",
    "logout_msg": "LOGOUT",
    "my_move_msg": "MY_MOVE",
    "multiplayer": "PVP",
    "get_my_rating": "MY_RATING",
    "get_logged_users": "LOGGED"
}

PROTOCOL_SERVER = {
    "login_ok_msg": "LOGIN_OK",
    "login_failed_msg": "ERROR",
    "looking_for_opponent_msg": "LOOKING_FOR_OPPONENT",
    "no_opponent_found_msg": "NO_OPPONENT_FOUND",
    "game_started_msg": "GAME_STARTED",
    "opponent_quit_msg": "OPPONENT_QUIT",
    "your_move_msg": "YOUR_MOVE",
    "invalid_move_msg": "INVALID_MOVE",
    "not_in_room_msg": "NOT_IN_ROOM",
    "opponent_move_msg": "OPPONENT_MOVE",
    "game_over_msg": "GAME_OVER",
    "get_rating_msg": "YOUR_RATING",
    "logged_users_msg": "LOGGED_USERS_NAMES",
    "you_won": "you won",
    "you_lost": 'you lost',
    "tie": 'tie'
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
        return ERROR_RETURN


def join_data(msg_fields):
    """
    Helper method. Gets a list, joins all of it's fields to one string divided by the data delimiter.
    Returns: string that looks like cell1#cell2#cell3
    """
    msg = ""
    msg_length = len(msg_fields)
    if msg_length != 0:
        for i in range(msg_length - 1):
            msg += msg_fields[i] + DATA_DELIMITER
        msg += msg_fields[-1]
    return msg

