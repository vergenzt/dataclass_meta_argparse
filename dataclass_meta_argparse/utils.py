import re
from typing import Callable, Union


def default_envize_string(s: str, keep_case: Union[bool, Callable[[str], bool]] = lambda s: len(s) == 1) -> str:
    subbed = re.sub(r'[^a-zA-Z0-9]+', '_', s).strip('_')
    return subbed if (keep_case is True or callable(keep_case) and keep_case(subbed)) else subbed.upper()
