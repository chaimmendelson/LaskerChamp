import psycopg2 as pg2
import hashlib
import requests
CONN = pg2.connect(database='chess_users', user='postgres', password=132005)
CONN.autocommit = True
C_TYPE = 'type'
C_LEN = 'len'
C_CONSTRAINS = 'constrains'
TABLE = 'accounts'
COLUMNS = {
           'user_id':       {C_TYPE: 'serial', C_LEN: None, C_CONSTRAINS: 'primary key'},
           'username':      {C_TYPE: str,      C_LEN: 20,   C_CONSTRAINS: 'unique not null'},
           'password_hash': {C_TYPE: str,      C_LEN: 40,   C_CONSTRAINS: 'not null'},
           'elo':           {C_TYPE: int,      C_LEN: None, C_CONSTRAINS: 'not null'}
          }
ID = True
USER_ID = 'user_id'
USERNAME = 'user_name'
PASSWORD = 'password_hash'
ELO = 'elo'


def get_len(column):
    return COLUMNS[column][C_LEN]


def get_type(column):
    return COLUMNS[column][C_TYPE]


def get_constrains(column):
    return COLUMNS[column][C_CONSTRAINS]


def hash(password):
    return hashlib.sha1(password.encode(), usedforsecurity=True).hexdigest()


def get_column_names():
    return list(COLUMNS.keys())


def drop_table():
    execute(f"drop table if exists {TABLE}")


def execute(code):
    cur = CONN.cursor()
    cur.execute(code)
    return cur


def create_table():
    c_type_dict = {int: 'integer', str: 'varchar', 'serial': 'serial'}
    columns = ""
    for column in COLUMNS:
        columns += f"{column} {c_type_dict[get_type(column)]} "
        if get_len(column):
            columns += f"({get_len(column)}) "
        columns += f"{get_constrains(column)},\n"
    execute(f"create table if not exists {TABLE}({columns[:-2]});")


def check_value(column, value):
    if type(value) != get_type(column):
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
    columns = list(COLUMNS.keys())
    if ID:
        columns = columns[1:]
    if len(row) == len(columns):
        for column, value in dict(zip(columns, row)).items():
            if not check_value(column, value):
                return False
        for i in range(len(row)):
            row[i] = char(row[i])
        execute(f"insert into {TABLE}({', '.join(columns)}) values({', '.join(row)});")
        return True
    return False


def print_table():
    data = execute(f'select * from {TABLE}').fetchall()
    data.insert(0, get_column_names())
    for i in range(len(data)):
        data[i] = list(data[i])
        for j in range(len(data[0])):
            data[i][j] = str(data[i][j])
    for i in range(len(data[0])):
        longest = 0
        for row in data:
            if len(row[i]) > longest:
                longest = len(row[i])
        longest += 2
        for j in range(len(data)):
            data[j][i] += ' ' * (longest - len(data[j][i]))
    for line in data:
        print(' | '.join(line))


def is_value_in_column(column, value):
    try:
        execute(f'select * from {TABLE} where {column} = {char(value)}').fetchall()[0]
        return True
    except IndexError:
        return False


def char(text):
    return f"'{text}'"


# now functions made only for my table

def is_password_correct(user_name, password):
    real_pass = execute(f'select * from {TABLE} '
                        f'where {USERNAME} = {char(user_name)}').fetchall()[0][2]
    return real_pass == hash(password)


def does_user_exist(username):
    return is_value_in_column(USERNAME, username)


def validate_email(email):
    response = requests.get(
        "https://isitarealemail.com/api/email/validate",
        params={'email': email})

    status = response.json()['status']
    return status == "valid"


def main():
    global CONN
    print(validate_email('chaimke2005@gmail.com'))
    drop_table()
    create_table()
    insert_new_row(['test', hash('test123'), 10])
    insert_new_row(['chaim', hash('chaim123'), 20])
    print_table()
    drop_table()
    CONN.close()

if __name__ == '__main__':
    main()
