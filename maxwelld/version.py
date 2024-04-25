import os

path = os.path.abspath(os.path.dirname(__file__))

def get_version(filename=f'{path}/version'):
    return open(filename, "r").read().strip()
