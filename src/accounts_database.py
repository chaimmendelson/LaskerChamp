import platform
import re

import psycopg2 as pg2
import requests


TABLE_NAME = 'accounts'

USERNAME = 'username'
PASSWORD = 'password_hash'
EMAIL = 'email_address'
ELO = 'elo'
GAMES_PLAYED = 'games_played'
LAST_ENTRY = 'last_entry'
CREATION_DATE = 'creation_date'

C_TYPE = 'type'
C_LEN = 'len'
C_CONSTRAINS = 'constrains'

COLUMNS = {
    USERNAME:       {C_TYPE: 'string',      C_LEN: 32,   C_CONSTRAINS: 'unique not null primary key'},
    PASSWORD:       {C_TYPE: 'string',      C_LEN: 40,   C_CONSTRAINS: 'not null'},
    EMAIL:          {C_TYPE: 'email',       C_LEN: None, C_CONSTRAINS: 'unique not null'},
    ELO:            {C_TYPE: 'number',      C_LEN: None, C_CONSTRAINS: 'not null'},
    GAMES_PLAYED:   {C_TYPE: 'number',      C_LEN: None, C_CONSTRAINS: 'not null'},
    LAST_ENTRY:     {C_TYPE: 'timestamp',   C_LEN: None, C_CONSTRAINS: 'not null'},
    CREATION_DATE:  {C_TYPE: 'timestamp',   C_LEN: None, C_CONSTRAINS: 'not null'}
}

MANUALLY_MUTABLE_COLUMNS = [USERNAME, PASSWORD, EMAIL, ELO, GAMES_PLAYED]
COLUMNS_L = list(COLUMNS)

ERROR = 0
COMPLETE = 1
VALID = 1
ARGUMENTS_ERROR = 2
INVALID_COLUMN_ERROR = 3
INVALID_VALUE_ERROR = 4
ALREADY_EXISTS_ERROR = 5


def get_len(column):
    if column in COLUMNS:
        return COLUMNS[column][C_LEN]
    return None


def get_type(column):
    if column in COLUMNS:
        return COLUMNS[column][C_TYPE]
    return None


def get_constrains(column):
    if column in COLUMNS:
        return COLUMNS[column][C_CONSTRAINS]
    return None


def execute(code, fetchall=False, fetchmany=False, amount=1):
    data = ""
    if platform.uname().system == 'Windows':
        connection = pg2.connect(database='chess_users', user='postgres', password=132005)
    else:
        connect_str = "dbname='chess_users' user='lasker' host='localhost' password='132005'"
        connection = pg2.connect(connect_str)
    cursor = connection.cursor()
    cursor.execute(code)
    if fetchall:
        data = cursor.fetchall()
    if fetchmany:
        data = cursor.fetchmany(amount)
    connection.commit()
    connection.close()
    return data


def create_table():
    c_type_dict = {'number': 'integer', 'string': 'varchar', 'serial': 'serial',
                   'email': 'text', 'timestamp': 'timestamp'}
    columns = ""
    for column in COLUMNS:
        columns += f"{column} {c_type_dict[get_type(column)]} "
        if get_len(column):
            columns += f"({get_len(column)})"
        columns += f"{get_constrains(column)},\n"
    execute(f"create table if not exists {TABLE_NAME}({columns[:-2]});")


def drop_table():
    execute(f"drop table if exists {TABLE_NAME};")


def reset_table():
    drop_table()
    create_table()


def is_value_in_column(column, value):
    if column in COLUMNS:
        return execute(f"select * from {TABLE_NAME} where {column} = '{value}';", fetchmany=True) != []
    return False


def delete_user(username):
    if is_value_in_column(USERNAME, username):
        execute(f"delete from {TABLE_NAME} where {USERNAME} = '{username}';")
        return COMPLETE
    return INVALID_VALUE_ERROR


def check_value(column, value):
    if column not in COLUMNS:
        return INVALID_COLUMN_ERROR
    if get_type(column) == 'string':
        if type(value) != str:
            return INVALID_VALUE_ERROR
    if get_type(column) == 'number':
        if not value.isnumeric() or type(value) != str:
            return INVALID_VALUE_ERROR
    if get_len(column):
        if len(value) > get_len(column):
            return INVALID_VALUE_ERROR
    if not value:
        if 'not null' in get_constrains(column):
            return INVALID_VALUE_ERROR
    if 'unique' in get_constrains(column):
        if is_value_in_column(column, value):
            return ALREADY_EXISTS_ERROR
    if get_type(column) == 'email':
        if not is_email_valid(value):
            return INVALID_VALUE_ERROR
    return VALID


def insert_new_user(user_data):
    if len(user_data) > len(MANUALLY_MUTABLE_COLUMNS) or len(user_data) < len(MANUALLY_MUTABLE_COLUMNS):
        return ARGUMENTS_ERROR
    for column, value in dict(zip(MANUALLY_MUTABLE_COLUMNS, user_data)).items():
        status = check_value(column, value)
        if status != VALID:
            return status, column
    temp = []
    x = 0
    for column in COLUMNS_L:
        if get_type(column) == 'timestamp':
            temp.append('current_timestamp')
        else:
            temp.append(f"'{user_data[x]}'")
            x += 1
    execute(f"insert into {TABLE_NAME}({', '.join(list(COLUMNS))}) values({', '.join(temp)});")
    return COMPLETE, None


def get_all_users():
    return execute(f'select * from {TABLE_NAME};', fetchall=True)


def printable_table(table):
    table.insert(0, COLUMNS_L)
    for i in range(len(table)):
        table[i] = list(table[i])
        for j in range(len(table[0])):
            table[i][j] = str(table[i][j])
    for i in range(len(table[0])):
        longest = 0
        for row in table:
            if len(row[i]) > longest:
                longest = len(row[i])
        longest += 2
        for j in range(len(table)):
            table[j][i] += ' ' * (longest - len(table[j][i]))
    data = ""
    for line in table:
        data += ' | '.join(line) + '\n'
    return data[:-1]


def is_email_valid(email):
    email_regex = r'^[\w.%+-]{1,64}@[A-Za-z\d.-]{1,253}\.[A-Z|a-z]{2,4}$'
    if re.fullmatch(email_regex, email):
        try:
            response = requests.get("https://isitarealemail.com/api/email/validate", params={'email': email})
            status = response.json()['status']
            return status == "valid"
        except:
            return True
    return False


def get_value(username, column):
    if is_value_in_column(USERNAME, username) and column in COLUMNS:
        data = execute(f"select {column} from {TABLE_NAME} where {USERNAME} = '{username}';", fetchmany=True)
        return data[0][0]
    return None


def update_value(username, column, new_value):
    if column in MANUALLY_MUTABLE_COLUMNS:
        if is_value_in_column(USERNAME, username):
            if check_value(column, new_value):
                execute(f"update {TABLE_NAME} set {column} = '{new_value}'  where {USERNAME} = '{username}';")
                return COMPLETE
        return INVALID_VALUE_ERROR
    return INVALID_COLUMN_ERROR


def update_entry(username):
    if is_value_in_column(USERNAME, username):
        execute(f"update {TABLE_NAME} set {LAST_ENTRY} = current_timestamp  where {USERNAME} = '{username}';")
        return True
    return INVALID_VALUE_ERROR


def main():
    reset_table()


if __name__ == '__main__':
    main()
