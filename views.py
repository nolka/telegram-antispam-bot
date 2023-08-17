"""
Contains function for rendering certain messages to send to groups
"""

import re

from jinja2 import Environment, FileSystemLoader, select_autoescape

env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape()
)


def render_new_member_joined_message(params: dict) -> str:
    """
    Renders message for new members joined onto group
    """
    return _render_tpl("new_member_joined_message.j2", params)


def _render_tpl(name: str, params: dict) -> str:
    tpl = env.get_template(name)
    return tpl.render(params)


def _escape_rendered_template(rendered: str) -> str:
    """
    Function for escaping telegram markdownV2 markup.
    TODO: Fix this function for correct escaping
    """
    compiled = re.compile(r"([_*\[\]\(\)~`>\#\+\-=|\{\}\.\,\!])")
    return compiled.sub("\\\\1", rendered)
