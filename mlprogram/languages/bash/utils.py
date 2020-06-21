from typing import Union

from mlprogram.asts import Root


def is_subtype(subtype: Union[str, Root], basetype: Union[str, Root]) -> bool:
    if isinstance(basetype, Root):
        return True
    if basetype == "Node" and subtype != "str":
        return True
    if basetype == subtype:
        return True
    return False
