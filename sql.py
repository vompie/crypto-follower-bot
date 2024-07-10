import aiosqlite
from config import *


# create database
async def create_database() -> None:
    try:
        async with aiosqlite.connect(DB_FILE) as db:
            # create table user_follows
            await db.execute(f'''
                CREATE TABLE IF NOT EXISTS user_follows (
                    id INTEGER PRIMARY KEY,
                    tlg_id INTEGER,
                    coin_id INTEGER,
                    coin_name TEXT,
                    min_value REAL DEFAULT null,
                    max_value REAL DEFAULT null
                )'''
            )
            await db.commit()
    except Exception as e:
        return None
    

# execute query
async def execute_query(sql_query: str, data: tuple=None) -> bool:
    try:
        async with aiosqlite.connect(DB_FILE) as db:
            cursor = await db.cursor()
            if data:
                await cursor.execute(sql_query, data)
            else:
                await cursor.execute(sql_query)
            await db.commit()
        return True
    except Exception as e:
        # print(e)
        return False


# execute selection query
async def execute_selection_query(sql_query: str, data: tuple=None) -> None|aiosqlite.Row:
    try:
        async with aiosqlite.connect(DB_FILE) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.cursor()
            if data:
                await cursor.execute(sql_query, data)
            else:
                await cursor.execute(sql_query)
            rows = await cursor.fetchall()
        return rows
    except Exception as e:
        # print(e)
        return None


# insert user follow coin
async def insert_row(tlg_id: int, coin_id: int, coin_name: str, value: float, value_type: str) -> bool:
    sql_query = f'''INSERT INTO user_follows (tlg_id, coin_id, coin_name, {value_type}) VALUES (?,?,?,?)'''
    return await execute_query(sql_query, (tlg_id, coin_id, coin_name, value))


# get unique coins id
async def get_distinct_coins_id() -> None|aiosqlite.Row:
    sql_query = '''SELECT DISTINCT coin_id FROM user_follows'''
    return await execute_selection_query(sql_query)


# get users whos follow coins and condition is true
async def get_users_follow_coin(coin_id: int, coin_value: float) -> None|aiosqlite.Row:
    sql_query = f'''
        SELECT tlg_id, min_value, max_value, MIN(min_value) as mi, MAX(max_value) as ma FROM user_follows 
        WHERE coin_id = {coin_id} AND ( 
                (min_value not null AND min_value > {coin_value}) OR (
                (max_value not null AND max_value < {coin_value})
            )
        )
        GROUP BY tlg_id
        ORDER BY id DESC
    '''
    return await execute_selection_query(sql_query)


# get user follows coins
async def get_user_follows(tlg_id: int, offset: int=0):
    sql_query = f'SELECT * FROM user_follows WHERE tlg_id = ? LIMIT {NEXT+1} OFFSET {offset}'
    return await execute_selection_query(sql_query, (tlg_id, ))


# delete row by row_id
async def delete_row(row_id: int):
    sql_query = 'DELETE FROM user_follows WHERE id = ?'
    return await execute_query(sql_query, (row_id, ))


if __name__ == "__main__":
    pass
