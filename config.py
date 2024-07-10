import os
from dotenv import load_dotenv 


load_dotenv() 


DB_FILE = 'db.sqlite'
BASE_URL = 'https://pro-api.coinmarketcap.com/'

PREV = 0
NEXT = 4

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("API_KEY")
