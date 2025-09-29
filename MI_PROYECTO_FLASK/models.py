from flask_login import UserMixin

class User(UserMixin):
    def _init_(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password