import asyncpg
from asyncpg.pool import Pool
from asyncpg import Connection

#  psql -U manish -h localhost -d music_qr_db
DATABASE_NAME = "music_qr_db"
DATABASE_URL = f"postgresql://manish@localhost/{DATABASE_NAME}"

pool: Pool = None

async def connect_to_db():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL)


async def close_db_connection():
    await pool.close()


async def get_db_connection() -> Connection:
    async with pool.acquire() as connection:
        yield connection


async def save_file_to_disk(file_path: str, file: bytes):
    with open(file_path, "wb") as f:
        f.write(file)


async def save_file_to_db(connection: Connection, id: str, music_name: str, file_path: str):
    query = "INSERT INTO music (id, music_name, file_path) VALUES ($1, $2, $3)"
    status = await connection.execute(query, id, music_name, file_path)
    print(status)


