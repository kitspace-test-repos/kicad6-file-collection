"""
Retrieves and writes all the KiCad 6 files we can find by using the Sourcegraph
API.

SPDX-License-Identifier: MIT
"""
import json
import os
import re
import requests

# you need to get sourcegraph access token and set the SRC_ACCESS_TOKEN env variable
# https://docs.sourcegraph.com/cli/how-tos/creating_an_access_token
token = os.environ["SRC_ACCESS_TOKEN"]


def get_file_list():
    url = "https://sourcegraph.com/.api/search/stream"
    params = {"q": "file:\\.kicad_sch$ select:file.path count:all"}
    headers = {"Authorization": f"token {token}", "Accept": "text/event-stream"}
    res = requests.get(url, params=params, headers=headers, stream=True)
    files = []
    for line in res.iter_lines():
        if line.startswith(b"data: "):
            data = json.loads(line[6:])
            if isinstance(data, list):
                files += [
                    itm
                    for itm in data
                    if "type" in itm and itm["type"] == "path"
                    # let's use the offical kicad repo on gitlab
                    and itm["repository"] != "github.com/KiCad/kicad-source-mirror"
                ]
    return files


def request_content(repo, path):
    url = "https://sourcegraph.com/.api/graphql"
    headers = {"Authorization": f"token {token}", "Accept": "application/json"}
    gql = """
        query ($q: String!) {
          search(query: $q, version: V3) {
            results {
              results {
                ... on FileMatch {
                  file {
                    content
                  }
                }
              }
            }
          }
        }
    """
    payload = {
        "query": gql,
        "variables": {"q": f"repo:^{re.escape(repo)}$ file:^{re.escape(path)}$"},
    }
    res = requests.post(url, data=json.dumps(payload), headers=headers)
    body = res.json()
    try:
        content = body["data"]["search"]["results"]["results"][0]["file"]["content"]
    except IndexError:
        return None

    return content


def write_contents(files, existing_sch_files):
    for f in files:
        repo = f["repository"]
        sch_path = f["path"]

        sch_content = request_content(repo, sch_path)
        pcb_content = None
        pro_content = None

        if sch_content is None:
            raise Exception(f"Could not retrieve {repo}/{sch_path}")

        if sch_content in existing_sch_files:
            print(f"Contents of {repo}/{sch_path} already exists, skipping.")
            continue

        full_sch_path = os.path.join("files", repo, sch_path)
        folder = os.path.dirname(full_sch_path)
        os.makedirs(folder, exist_ok=True)
        print(f"Writing {repo}/{sch_path}")
        with open(full_sch_path, "w", newline="\n") as f:
            f.write(sch_content)
        existing_sch_files.append(sch_content)

        # get the .kicad_pcb with the same name, if available
        pcb_path = re.sub(r"\.kicad_sch$", ".kicad_pcb", sch_path)
        pcb_content = request_content(repo, pcb_path)
        if pcb_content is not None:
            # if there is a pcb there should be a .kicad_pro of that name too
            pro_path = re.sub(r"\.kicad_sch$", ".kicad_pro", sch_path)
            pro_content = request_content(repo, pro_path)

            if pro_content is not None:

                full_pcb_path = os.path.join("files", repo, pcb_path)
                print(f"Writing {repo}/{pcb_path}")
                with open(full_pcb_path, "w", newline="\n") as f:
                    f.write(pcb_content)

                full_pro_path = os.path.join("files", repo, pro_path)
                print(f"Writing {repo}/{pro_path}")
                with open(full_pro_path, "w", newline="\n") as f:
                    f.write(pro_content)


def read_existing_files():
    existing_sch_files = []
    for root, _, files in os.walk("files"):
        for file in files:
            if file.endswith(".kicad_sch"):
                path = os.path.join(root, file)
                with open(path) as f:
                    contents = f.read()
                existing_sch_files.append(contents)

    return existing_sch_files


files = get_file_list()
print(f"Found {len(files)} .kicad_sch files")
existing = read_existing_files()
write_contents(files, existing)
