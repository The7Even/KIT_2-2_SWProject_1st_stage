import os

import requests

url = ('https://api.odcloud.kr/api/15123287/v1/uddi:d6c67241-a722-48c4-8041-d66ff243cf57?'
       'page=1&perPage=10&returnType=JSON')
params = {
    'serviceKey': os.environ['ODCLOUD_SERVICE_KEY'],
    'searchKeyword': '우현동'
}

response = requests.get(url, params=params)
print(response.text)