import logging

from maxwelld.server.maxwelld_server import run_server

logging.basicConfig(level=logging.INFO)
if __name__ == "__main__":
    run_server()
