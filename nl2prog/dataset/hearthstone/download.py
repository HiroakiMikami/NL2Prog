import requests
from typing import Callable

from nl2prog.utils.data import Entry, ListDataset

BASE_PATH = "https://raw.githubusercontent.com/" + \
    "deepmind/card2code/master/third_party/hearthstone/"


def default_get(path: str) -> str:
    return requests.get(path).text


def download(base_path: str = BASE_PATH,
             get: Callable[[str], str] = default_get):
    dataset = {}
    for name in ["train", "dev", "test"]:
        target = name
        if name == "test":
            target = "valid"
        if name == "dev":
            target = "test"
        query = get("{}/{}_hs.in".format(base_path, name)).split("\n")
        code = get("{}/{}_hs.out".format(base_path, name)).split("\n")
        code = [c.replace("§", "\n").replace("and \\", "and ") for c in code]
        groups = []
        for q, c in zip(query, code):
            if q == "" and c == "":
                continue
            groups.append([Entry(q, c)])
        dataset[target] = ListDataset(groups)
    return dataset