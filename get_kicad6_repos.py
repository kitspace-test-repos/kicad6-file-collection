import json
import math
import subprocess
import time
import os
import sys
import requests
from pprint import pprint


token = os.environ["SOURCEGRAPH_API_TOKEN"]
url = "https://sourcegraph.com/.api/search/stream"
params = {"q": "file:\\.kicad_sch$ select:file.path count:all"}
headers = {"Authorization": f"token {token}", "Accept": "text/event-stream"}
r = requests.get(url, params=params, headers=headers, stream=True)
result = []
for line in r.iter_lines():
    if line.startswith(b'data: '):
        data = json.loads(line[6:])
        if isinstance(data, list):
            result += [i for i in data if "type" in i and i["type"] == "path"]

print(len(result))
# url = "https://sourcegraph.com/.api/graphql"
# payload = {"query": "query { currentUser { username } }"}
# r = requests.post(url, data=json.dumps(payload), headers=headers)
# body = r.json()
# print(body)

# from urllib.request import urlopen, Request
#
#
# data = json.dumps().encode('utf-8')
# print(data)
# req = Request(url=url, method="POST", data=data)
# req.add_header("", f"token {token}")
# res = urlopen(req)
#
# print(res)
#
