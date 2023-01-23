import os

def Mkdir(path: str):
    try:
        os.mkdir(path)
    except FileExistsError:
        pass