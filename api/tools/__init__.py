"""Tools: small functions you can run on a ticker from the dashboard.

To add a tool, create a new file in this folder with three things:

    TITLE = "Short name shown on the button"
    DESCRIPTION = "One sentence saying what it does."

    def run(ticker):
        return {...}   # a dictionary, or a list of dictionaries (shown as a table)

Then rebuild (docker compose up -d --build). The dashboard finds it by itself.
Files whose names start with an underscore are ignored.
"""
import importlib
import os

TOOLS = {}  # tool name (the file name without .py) -> the loaded module

folder = os.path.dirname(__file__)
for filename in sorted(os.listdir(folder)):
    if filename.endswith(".py") and not filename.startswith("_"):
        name = filename[:-3]
        TOOLS[name] = importlib.import_module("tools." + name)


def list_tools():
    result = []
    for name, module in TOOLS.items():
        result.append({"name": name, "title": module.TITLE, "description": module.DESCRIPTION})
    return result
