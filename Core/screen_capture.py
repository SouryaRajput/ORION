import subprocess
import tempfile
from PIL import Image


def capture_screen():

    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)

    # macOS screenshot
    subprocess.run(["screencapture", "-x", tmp.name])

    return tmp.name