import hashlib
import timeit
import accounts_database as db
from datetime import datetime


def hash(password):
    return hashlib.sha512(password.encode()).hexdigest()


def is_username_valid(username):
    if type(username) == str:
        if username.isalnum():
            if 0 < len(username) < db.get_len(db.USERNAME):
                return True
    return False


def is_password_valid(password):
    if type(password) == str:
        if password.isalnum():
            if 0 < len(password) < db.get_len(db.USERNAME):
                return True
    return False


def is_email_valid(email):
    return db.is_email_valid(email)


def create_new_user(username, password, email):
    if is_username_valid(username):
        if is_password_valid(password):
            status, column = db.insert_new_user([username, hash(password), email, '1200', '0', db.USER])
            if status == db.VALID:
                return "account created"
            if status == db.INVALID_VALUE_ERROR:
                return f"invalid {column}"
            if status == db.ALREADY_EXISTS_ERROR:
                return f"{column} already exists"
        return f"invalid {db.PASSWORD}"
    return f"invalid {db.USERNAME}"


def delete_user(username):
    if does_username_exist(username):
        db.delete_user(username)
        return True
    return False


def check_password(username, password):
    return hash(password) == db.get_value(username, db.PASSWORD)


def does_username_exist(username):
    return db.is_value_in_column(db.USERNAME, username)


def update_username(username, password, new_username):
    if check_password(username, password):
        db.update_value(username, db.USERNAME, new_username)
        return True
    return False


def update_password(username, old_password, new_password):
    if check_password(username, old_password):
        db.update_value(username, db.PASSWORD, hash(new_password))
        return True
    return False


def update_email(username, password, new_email):
    if check_password(username, password):
        db.update_value(username, db.EMAIL, new_email)
        return True
    return False


def get_email(username):
    return db.get_value(username, db.EMAIL)


def update_elo(username, new_elo):
    return db.update_value(username, db.ELO, new_elo)


def get_elo(username):
    return db.get_value(username, db.ELO)


def update_games_played(username, add):
    return db.update_value(username, db.GAMES_PLAYED, get_games_played(username) + add)


def get_games_played(username):
    return db.get_value(username, db.GAMES_PLAYED)


def update_entry(username):
    return db.update_entry(username)


def get_entry(username):
    entry = db.get_value(username, db.LAST_ENTRY)
    if entry:
        entry = datetime.fromisoformat(str(entry))
        return entry.strftime("(%d/%m/%y, %H:%M:%S)")
    return None


def get_creation_date(username):
    creation = db.get_value(username, db.LAST_ENTRY)
    if creation:
        creation = datetime.fromisoformat(str(creation))
        return creation.strftime("(%d/%m/%y, %H:%M:%S)")
    return None


def admin_reset_password(username):
    if does_username_exist(username):
        db.update_value(username, db.PASSWORD, hash('default'))
        return True
    return False


def set_admin(password, username):
    if does_username_exist(username):
        if db.get_value(username, db.PERMISSIONS) == db.ADMIN:
            if check_password('admin', admin_password):
                if does_username_exist(user_to_set):
                    pass


OWNER_PASSWORD = hashlib.sha384('chaim'.encode()).hexdigest()[34:61]


def reset_table():
    db.reset_table()
    create_new_user()
    create_new_user('admin', hashlib.sha384('chaim mendelson 2005')[30:63], 'chaimke2005@gmail.com')
    create_new_user('test', 'test', 'chaimm2005@gmail.com')


def test():
    """delete_user('test')
    create_new_user('test', 'test', 'chaimm2005@gmail.com')
    start = timeit.default_timer()
    update_email('test', 'test', 'chaimke2005@gmail.com')
    stop = timeit.default_timer()
    print('Time: ', stop - start)
    print(db.printable_table(db.get_all_users()))"""
    print(OWNER_PASSWORD)
if __name__ == '__main__':
    test()
