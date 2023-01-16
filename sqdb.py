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

    async def get_data(self, user_id, data, table='gay_users'):
        with self.connection:
            self.cursor.execute(f'SELECT {data} FROM {table} WHERE user_id = {user_id}')
            return self.cursor.fetchone()[0]

    async def get_all(self, table='gay_users'):
        with self.connection:
            self.cursor.execute(f'SELECT * FROM {table}')
            return self.cursor.fetchall()

    async def get_from_all(self, data, table='gay_users'):
        with self.connection:
            self.cursor.execute(f'SELECT {data} FROM {table}')
            return [i[0] for i in self.cursor.fetchall()]

    async def update_data(self, user_id, name, data):
        with self.connection:
            self.cursor.execute(f"UPDATE gay_users set {name} = '{data}' WHERE user_id = {user_id}")

    async def add_user_to_group(self, groupname, user_id):
        with self.connection:
            self.cursor.execute(f"SELECT users from gay_groups WHERE name = '{groupname}'")
            extract = [i[0] for i in self.cursor.fetchall()]
            if user_id not in extract:
                self.cursor.execute(f"UPDATE gay_groups SET users = array_append(users, {user_id}) WHERE name = '{groupname}'")

    async def remove_user_from_group(self, groupname, user_id):
        with self.connection:
            self.cursor.execute(
                f"UPDATE gay_groups SET users = array_remove(users, {user_id}) WHERE name = '{groupname}'")

    async def get_group_users(self, groupname):
        with self.connection:
            self.cursor.execute(f"SELECT users from gay_groups WHERE name = '{groupname}'")
            data = self.cursor.fetchall()
            if len(data[0]) == 0:
                return []
            else:
                return [i[0] for i in data][0]

    async def update_non_text_data(self, user_id, name, data):
        with self.connection:
            self.cursor.execute(f"UPDATE gay_users set {name} = {data} WHERE user_id = {user_id}")