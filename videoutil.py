import subprocess
from pathlib import Path

def renderGIF(framesDest, start, end, fps, filetype="JPEG"):

    framesv = end - start + 1

    extension = "png" if filetype == "PNG" else "jpg"

    command = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-start_number", str(start),
        "-i", f"%04d.{extension}",
        "-frames:v" , str(framesv),
        "-filter_complex", "[0:v]scale=iw/2:ih/2:flags=lanczos,split[a][b];[a]palettegen=stats_mode=full[p];[b][p]paletteuse=dither=sierra2_4a",
        "-loop", str(0),
        "output_gif.gif"
    ]

    subprocess.run(
        command,
        cwd=framesDest,
        check=True
    )

    pass