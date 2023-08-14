from jinja2 import Environment, FileSystemLoader, select_autoescape
import re

env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape()
)

def render_new_member_joined_message(params: dict) -> str:
    return _render_tpl("new_member_joined_message.j2", params)

def _render_tpl(name: str, params: dict) -> str:
    tpl = env.get_template(name)
    return tpl.render(params)

def _escape_rendered_template(rendered: str) -> str:
    compiled = re.compile("([_*\[\]\(\)~`>\#\+\-=|\{\}\.\,\!])")
    return compiled.sub("\\\\1", rendered)