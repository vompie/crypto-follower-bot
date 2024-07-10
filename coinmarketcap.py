from requests import Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
import json


class CMC:
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            'Accepts': 'application/json',
            'X-CMC_PRO_API_KEY': self.api_key,
        }
        self.quotes_url = f'{self.base_url}v2/cryptocurrency/quotes/latest'
        self.session = Session()
        self.session.headers.update(self.headers)
        self.coins = self.read_json('coins.json')

    def read_json(self, file: str) -> dict:
        try:
            with open(file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(e)
            return {}

    def pars_json_coins(self, data: dict) -> None:
        coins = {}
        for coin in data:
            name = coin.get('name', None)
            if not name: 
                continue
            coins[name] = {
                'id': coin.get('id', None),
                'symbol': coin.get('symbol', None),
                'slug': coin.get('slug', None)
            }
        with open('coins.json', 'w') as f:
            f.write(json.dumps(coins))

    def write_json_coins(self, data: str) -> None:
        from uuid import uuid1
        with open(f'{str(uuid1())}.txt', 'w') as f:
            f.write(data)

    def get_coin_quotes(self, coins: list) -> dict:
        parameters = {
            'id': ','.join(str(coin['coin_id']) for coin in coins),
            'aux': 'is_active,cmc_rank'
        }
        response = self.get_response(parameters=parameters)
        return response['data'] if response else {}

    def get_response(self, parameters: dict) -> dict:
        try:
            response = self.session.get(self.quotes_url, params=parameters)
            # self.write_json_coins(response.text)
            data = json.loads(response.text)
            if not ('statusCode' in data or data['status']['error_code']):
                return data
            return {}
        except (ConnectionError, Timeout, TooManyRedirects) as e:
            # print(f'{e}')
            return {}


if __name__ == "__main__":
    pass
