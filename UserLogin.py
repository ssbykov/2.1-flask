

class UserLogin():
    def fromDB(self, db, session, user_id):
        self.__user = db.get_user(session, user_id)
        return self

    def create(self, user):
        self.__user = user
        return self

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymus(self):
        return False

    def get_id(self):
        return str(self.__user.id)

