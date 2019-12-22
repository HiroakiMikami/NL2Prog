import requests
from typing import Callable

from nl2prog.utils.data import Entry, ListDataset
from .format_annotations import format_annotations

BASE_PATH = "https://raw.githubusercontent.com/" + \
    "odashi/ase15-django-dataset/master/django/"


def default_get(path: str) -> str:
    return requests.get(path).text


def download(base_path: str = BASE_PATH,
             get: Callable[[str], str] = default_get,
             num_train: int = 16000, num_test: int = 1000):
    annotation = get(BASE_PATH + "all.anno").split("\n")
    annotation = format_annotations(annotation)
    code = get(BASE_PATH + "all.code").split("\n")

    def to_group(elem):
        anno, code = elem
        return [Entry(anno, code)]
    data = list(map(to_group, zip(annotation, code)))

    train = ListDataset(data[:num_train])
    test = ListDataset(data[num_train:num_train + num_test])
    valid = ListDataset(data[num_train + num_test:])

    return {"train": train, "test": test, "valid": valid}
