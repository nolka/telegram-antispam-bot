import re


def escape(content: str) -> str:
    """
    Function for escaping telegram markdownV2 markup.
    TODO: Fix this function for correct escaping
    """
    compiled = re.compile(r"([_*\[\]\(\)~`>\#\+\-=|\{\}\.\,\!])")
    return compiled.sub(r"\\\1", content)
