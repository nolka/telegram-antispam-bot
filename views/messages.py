"""
Contains function for rendering certain messages to send to groups
"""

from jinja2 import Environment, FileSystemLoader, select_autoescape

from views.custom_filters import escape

env = Environment(loader=FileSystemLoader("templates"), autoescape=select_autoescape())
env.filters["escape"] = escape


def render_new_member_joined_message(params: dict) -> str:
    """
    Renders message for new members joined onto group
    """
    return _render_tpl("new_member_joined_message.j2", params)


def _render_tpl(name: str, params: dict) -> str:
    tpl = env.get_template(name)
    return tpl.render(params)
