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
                    itm for itm in data if "type" in itm and itm["type"] == "path"
                ]
    return files


def write_contents(files, existing):
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
    url = "https://sourcegraph.com/.api/graphql"
    headers = {"Authorization": f"token {token}", "Accept": "application/json"}
    for f in files:
        repo = f["repository"]
        path = f["path"]
        payload = {
            "query": gql,
            "variables": {"q": f"repo:^{re.escape(repo)}$ file:^{re.escape(path)}$"},
        }
        res = requests.post(url, data=json.dumps(payload), headers=headers)
        body = res.json()
        file_path = os.path.join("files", repo, path)
        try:
            content = body["data"]["search"]["results"]["results"][0]["file"]["content"]
        except IndexError:
            print(f"Warning: Could not retrieve {file_path}")
            continue
        if content in existing["sch"]:
            print(f"Contents of {path} already exists, skipping")
        else:
            folder = os.path.dirname(file_path)
            os.makedirs(folder, exist_ok=True)
            print(f"Writing {file_path}")
            with open(file_path, "w", newline="\n") as f:
                f.write(content)
            existing["sch"].append(content)


def read_existing_files():
    existing_sch_files = []
    existing_pcb_files = []
    for root, _, files in os.walk("files"):
        for file in files:
            path = os.path.join(root, file)
            with open(path) as f:
                contents = f.read()
            if file.endswith(".kicad_sch"):
                existing_sch_files.append(contents)
            elif file.endswith(".kicad_pcb"):
                existing_pcb_files.append(contents)

    return {"sch": existing_sch_files, "pcb": existing_pcb_files}


files = get_file_list()
print(f"Found {len(files)} .kicad_sch files")

existing = read_existing_files()

write_contents(files, existing)
