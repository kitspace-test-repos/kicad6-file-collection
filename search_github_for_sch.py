from __future__ import print_function
import json
import math
import subprocess
import time
import os
import sys

if sys.version_info[0] < 3:
    from urllib2 import urlopen
else:
    from urllib.request import urlopen

PAGE_SIZE = 100
TERM = 'language:"kicad+layout"'


def query(term, page):
    url = "https://api.github.com/search/repositories?q={}&page={}&per_page={}".format(
        term, page, PAGE_SIZE
    )
    print(url)
    response_body = urlopen(url).read()
    return json.loads(response_body)

def get_files(repo_full_name):
    url = "https://api.github.com/repos/{}/git/trees/HEAD?recursive=true".format(repo_full_name)
    response_body = urlopen(url).read()
    d = json.loads(response_body)
    return [x["path"] for x in d["tree"]]



print("Searching github for '{}'".format(TERM))
data = query(TERM, page=1)
repos = data["items"]

total = min(1000, data["total_count"])
pages = int(math.ceil(total / PAGE_SIZE))

print("Requesting {} repositories. {} pages.".format(total, pages))

for n in range(2, pages + 1):
    # avoid github API rate-limits
    time.sleep(3)
    print("Requesting page {}.".format(n))
    data = query(TERM, page=n)
    repos += data["items"]



for i, repo in enumerate(repos):
    # avoid github API rate-limits
    time.sleep(10)

    print("Checking files for {}".format(repo["full_name"]))
    files = get_files(repo["full_name"])

    has_sch = False
    for file in files:
        if file.lower().endswith('.kicad_sch'):
            has_sch = True
            break

    if has_sch:
        folder = os.path.join('repositories', repo["full_name"])
        if not os.path.exists(folder):
            print("Cloning {}".format(repo["full_name"]))
            cmd = ["git", "clone", repo["clone_url"], folder, "--filter=blob:none", "--depth=1", "--quiet"]
            subprocess.call(cmd)
