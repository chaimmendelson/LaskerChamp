import psycopg2 as pg2
import hashlib
import requests


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


def get_len(column):
    return COLUMNS[column][C_LEN]


def get_type(column):
    return COLUMNS[column][C_TYPE]


def get_constrains(column):
    return COLUMNS[column][C_CONSTRAINS]


def execute(code, fetchall=False, fetchmany=False, amount=1):
    data = ""
    connection = pg2.connect(database='chess_users', user='postgres', password=132005)
    print(code)
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


def is_value_in_column(column, value):
    return execute(f"select * from {TABLE_NAME} where {column} = '{value}';", fetchmany=True) != []


def delete_row(username):
    execute(f"delete from {TABLE_NAME} where {USERNAME} = '{username}';")


def check_value(column, value):
    match get_type(column):
        case 'string':
            if type(value) != str:
                return False
        case 'number':
            if not value.isnumeric():
                return False
        case 'email':
            if not validate_email(value):
                return False
    if get_len(column):
        if len(str(value)) > get_len(column):
            return False
    if len(str(value)) == 0:
        if 'not null' in get_constrains(column):
            return False
    if 'unique' in get_constrains(column):
        if is_value_in_column(column, value):
            return False
    return True


def insert_new_row(row):
    columns = []
    for column in list(COLUMNS):
        if get_type(column) != 'timestamp':
            columns.append(column)
    if len(row) == len(columns):
        for column, value in dict(zip(columns, row)).items():
            if not check_value(column, value):
                return False
        temp = []
        x = 0
        for column in list(COLUMNS):
            if get_type(column) == 'timestamp':
                temp.append('current_timestamp')
            else:
                temp.append(f"'{row[x]}'")
                x += 1
        execute(f"insert into {TABLE_NAME}({', '.join(list(COLUMNS))}) values({', '.join(temp)});")
        return True
    return False


def get_all_users():
    return execute(f'select * from {TABLE_NAME};', fetchall=True)


def printable_table(table=get_all_users()):
    table.insert(0, list(COLUMNS))
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


def does_user_exist(username):
    return is_value_in_column(USERNAME, username)


def get_data(username):
    data = list(execute(f"select * from {TABLE_NAME} where {USERNAME} = '{username}';").fetchone())
    return dict(zip(list(COLUMNS), data))


def validate_email(email):
    response = requests.get("https://isitarealemail.com/api/email/validate", params={'email': email})
    status = response.json()['status']
    return status == "valid"


def update_entry(username):
    execute(f"update {TABLE_NAME} set {LAST_ENTRY} = current_timestamp  where {USERNAME} = '{username}';")


def hash(password):
    return hashlib.sha1(password.encode(), usedforsecurity=True).hexdigest()


def main():
    pass


if __name__ == '__main__':
    main()
