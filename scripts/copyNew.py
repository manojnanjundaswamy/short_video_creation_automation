import sys
print("Python executable:", sys.executable)
print("sys.path:", sys.path)
# from moviepy.editor import VideoFileClip
from moviepy.editor import *
print("MoviePy import successful!")

def get_debug_info():
    return {
        "status": "success",
        "message": "Debug info printed.",
        "data": {"Python executable": sys.executable, "sys.path": sys.path}
    }

print(get_debug_info())