import hashlib

import accounts_database as db


def hash(password):
    return hashlib.sha1(password.encode(), usedforsecurity=True).hexdigest()


def insert_new_user():
    username = 'helo'
    password = hash('hi')
    email = 'chaimke2005@gmail.com'
    elo = '90'
    db.insert_new_row([username, password, email, elo])
    print(db.printable_table())

db.create_table()
insert_new_user()
