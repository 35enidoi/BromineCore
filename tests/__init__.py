from os import path as ospath
from sys import path as syspath


syspath.append(ospath.abspath(ospath.join(ospath.dirname(__file__), "..")))
