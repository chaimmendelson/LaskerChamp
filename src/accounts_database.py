import re

import psycopg2 as pg2
import requests


class InvalidUserData(Exception):
    pass


class InvalidUserName(Exception):
    pass


class TooFewArguments(Exception):
    pass


class TooManyArguments(Exception):
    pass


class InvalidColumn(Exception):
    pass

TABLE_NAME = 'accounts'

USERNAME = 'username'
PASSWORD = 'password_hash'
EMAIL = 'email_address'
ELO = 'elo'
LAST_ENTRY = 'last_entry'
CREATION_DATE = 'creation_date'

C_TYPE = 'type'
C_LEN = 'len'
C_CONSTRAINS = 'constrains'

COLUMNS = {
    USERNAME: {C_TYPE: 'string', C_LEN: 20, C_CONSTRAINS: 'unique not null primary key'},
    PASSWORD: {C_TYPE: 'string', C_LEN: 40, C_CONSTRAINS: 'not null'},
    EMAIL: {C_TYPE: 'email', C_LEN: None, C_CONSTRAINS: 'unique not null'},
    ELO: {C_TYPE: 'number', C_LEN: None, C_CONSTRAINS: 'not null'},
    LAST_ENTRY: {C_TYPE: 'timestamp', C_LEN: None, C_CONSTRAINS: ''},
    CREATION_DATE: {C_TYPE: 'timestamp', C_LEN: None, C_CONSTRAINS: ''}
}

MANUALLY_MUTABLE_COLUMNS = [USERNAME, PASSWORD, EMAIL, ELO]
COLUMNS_L = list(COLUMNS)


def get_len(column):
    return COLUMNS[column][C_LEN]


def get_type(column):
    return COLUMNS[column][C_TYPE]


def get_constrains(column):
    return COLUMNS[column][C_CONSTRAINS]


def execute(code, fetchall=False, fetchmany=False, amount=1):
    data = ""
    connection = pg2.connect(database='chess_users', user='postgres', password=132005)
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
    validate_column(column)
    return execute(f"select * from {TABLE_NAME} where {column} = '{value}';", fetchmany=True) != []


def validate_user_name(username):
    if not is_value_in_column(USERNAME, username):
        raise InvalidUserName("user name doesnt exists")


def validate_column(column):
    if column not in COLUMNS_L:
        raise InvalidColumn(f"column {column} does not exists in {TABLE_NAME}")


def delete_user(username):
    validate_user_name(username)
    execute(f"delete from {TABLE_NAME} where {USERNAME} = '{username}';")


def check_value(column, value):
    if get_type(column) == 'string':
        if type(value) != str:
            raise InvalidUserData(f"{column} must be string")
    if get_type(column) == 'number':
        if not value.isnumeric() or type(value) != str:
            raise InvalidUserData(f"{column} must be numeric string")
    if get_len(column):
        if len(str(value)) > get_len(column):
            raise InvalidUserData(f"{column} length must be less then {get_len(column)} digits")
    if len(str(value)) == 0:
        if 'not null' in get_constrains(column):
            raise InvalidUserData(f"{column} cant be null")
    if 'unique' in get_constrains(column):
        if is_value_in_column(column, value):
            raise InvalidUserData(f"the {column} ({value}) already exists")
    if column == ELO:
        if int(value) > 3000 or int(value) < 0:
            raise InvalidUserData(f"elo cant exceed 3000 or be less then 0")
    if get_type(column) == 'email':
        if not validate_email(value):
            raise InvalidUserData(f"invalid email")


def insert_new_user(user_data):
    if len(user_data) < len(MANUALLY_MUTABLE_COLUMNS):
        raise TooFewArguments()
    if len(user_data) > len(MANUALLY_MUTABLE_COLUMNS):
        raise TooManyArguments()
    for column, value in dict(zip(MANUALLY_MUTABLE_COLUMNS, user_data)).items():
        check_value(column, value)
    temp = []
    x = 0
    for column in COLUMNS_L:
        if get_type(column) == 'timestamp':
            temp.append('current_timestamp')
        else:
            temp.append(f"'{user_data[x]}'")
            x += 1
    execute(f"insert into {TABLE_NAME}({', '.join(list(COLUMNS))}) values({', '.join(temp)});")


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
    return data


def validate_email(email):
    email_regex = r'^[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9.-]{0,253}\.[A-Z|a-z]{2,4}$'
    try:
        if re.fullmatch(email_regex, email):
            response = requests.get("https://isitarealemail.com/api/email/validate", params={'email': email})
            status = response.json()['status']
            return status == "valid"
        return False
    except:
        return re.fullmatch(email_regex, email)


def get_value(username, column):
    validate_user_name(username)
    validate_column(column)
    data = execute(f"select {column} from {TABLE_NAME} where {USERNAME} = '{username}';", fetchmany=True)
    return data[0][0]


def update_value(username, column, new_value):
    validate_user_name(username)
    validate_column(column)
    if column not in MANUALLY_MUTABLE_COLUMNS:
        raise InvalidColumn(f"column {column} cant be set manually")
    check_value(column, new_value)
    execute(f"update {TABLE_NAME} set {column} = '{new_value}'  where {USERNAME} = '{username}';")


def update_entry(username):
    validate_user_name(username)
    execute(f"update {TABLE_NAME} set {LAST_ENTRY} = current_timestamp  where {USERNAME} = '{username}';")


def main():
    try:
        raise InvalidUserData("invalid email")
    except Exception as e:
        print(e)


if __name__ == '__main__':
    main()
