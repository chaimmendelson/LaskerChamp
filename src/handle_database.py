import hashlib
import accounts_database as db
from datetime import datetime


class InvalidPassword(Exception):
    pass


def hash(password):
    return hashlib.sha1(password.encode()).hexdigest()


def insert_new_user(username, password, email):
    db.insert_new_user([username, hash(password), email, '1400'])


def delete_user(username):
    db.delete_user(username)


def validate_password(username, password):
    return hash(password) == db.get_value(username, db.PASSWORD)


def does_username_exist(username):
    return db.is_value_in_column(db.USERNAME, username)


def update_username(username, password, new_username):
    validate_password(username, password)
    db.update_value(username, db.USERNAME, new_username)


def update_password(username, old_password, new_password):
    validate_password(username, old_password)
    db.update_value(username, db.PASSWORD, hash(new_password))


def update_email(username, password, new_email):
    validate_password(username, password)
    db.update_value(username, db.EMAIL, new_email)


def get_email(username):
    return db.get_value(username, db.EMAIL)


def update_elo(username, new_elo):
    db.update_value(username, db.ELO, new_elo)


def get_elo(username):
    return db.get_value(username, db.ELO)


def update_entry(username):
    db.update_entry(username)


def get_entry(username):
    entry = datetime.fromisoformat(str(db.get_value(username, db.LAST_ENTRY)))
    return entry.strftime("(%d/%m/%y, %H:%M:%S)")


def get_creation_date(username):
    creation = datetime.fromisoformat(str(db.get_value(username, db.CREATION_DATE)))
    return creation.strftime("(%d/%m/%y, %H:%M:%S)")


def admin_reset_password(username):
    db.update_value(username, db.EMAIL, '12345678')


def test():
    a, b = [1, 2]
    print(a)


if __name__ == '__main__':
    test()