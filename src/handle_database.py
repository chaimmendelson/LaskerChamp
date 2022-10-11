import hashlib
import accounts_database as db


def hash(password):
    return hashlib.sha1(password.encode(), usedforsecurity=True).hexdigest()


def insert_new_user(username, password, email, elo):
    password = hash(password)
    return db.insert_new_row([username, password, email, elo])

db.delete_row('chaim')
print(db.printable_table(db.get_all_users()))
insert_new_user('chaim', '13467', 'chaimke2005@gmail.com', '780')
print(db.printable_table(db.get_all_users()))
