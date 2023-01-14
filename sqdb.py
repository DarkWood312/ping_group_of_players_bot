import psycopg2


class Sqdb:
    def __init__(self, host, password, port, database, user):
        self.connection = psycopg2.connect(host=host,
                                           password=password,
                                           port=port,
                                           database=database,
                                           user=user)
        self.cursor = self.connection.cursor()

    async def is_user_exists(self, user_id):
        with self.connection:
            self.cursor.execute(f"SELECT COUNT(*) from gay_users WHERE user_id = {user_id}")
            if_exist = self.cursor.fetchone()
            return if_exist[0]

    async def add_user(self, user_id, username, user_name, user_surname):
        with self.connection:
            self.cursor.execute(f"SELECT COUNT(*) from gay_users WHERE user_id = {user_id}")
            if_exist = self.cursor.fetchone()[0]
            if not if_exist:
                self.cursor.execute(
                    f"INSERT INTO gay_users (user_id, username, user_name, user_surname) VALUES ({user_id}, '{username}', '{user_name}', '{user_surname}')")
                return True
            else:
                self.cursor.execute(
                    f"UPDATE gay_users set username = '{username}', user_name = '{user_name}', user_surname = '{user_surname}' WHERE user_id = {user_id}")
                return False

    async def get_data(self, user_id, data):
        with self.connection:
            self.cursor.execute(f'SELECT {data} FROM gay_users WHERE user_id = {user_id}')
            return self.cursor.fetchone()[0]

    async def get_users(self, only_anonymous=False):
        with self.connection:
            if only_anonymous:
                self.cursor.execute('SELECT user_id FROM gay_users WHERE anonymous = true')
                return [i[0] for i in self.cursor.fetchall()]
            else:
                self.cursor.execute('SELECT * FROM gay_users')
                return self.cursor.fetchall()

    async def update_data(self, user_id, name, data):
        with self.connection:
            self.cursor.execute(f"UPDATE gay_users set {name} = '{data}' WHERE user_id = {user_id}")

    async def update_non_text_data(self, user_id, name, data):
        with self.connection:
            self.cursor.execute(f"UPDATE gay_users set {name} = {data} WHERE user_id = {user_id}")