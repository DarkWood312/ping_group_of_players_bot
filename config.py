from dotenv import load_dotenv
from os import environ
from sqdb import Sqdb

load_dotenv()
token = environ['API_TOKEN']
sql = Sqdb(environ['SQL_HOST'], environ['SQL_PASSWORD'], environ['SQL_PORT'], environ['SQL_DATABASE'],
           environ['SQL_USER'])


async def available_groups():
    return await sql.get_from_all('name', 'gay_groups')


ping_templates = ['Пошли играть!']
