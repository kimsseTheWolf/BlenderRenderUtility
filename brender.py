from InquirerPy import inquirer
from pathlib import Path
import os
import json
import sys
import butil

# For prettier display
import time
from rich.console import Console, Group
from rich.panel import Panel
from rich.progress import (
    Progress,
    BarColumn,
    TaskProgressColumn,
)
from rich.table import Table
from rich.text import Text
from rich.live import Live

# Import configs from json config file
CONFIG_DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
VERSION = "1.0"

# Rich console
console = Console()

def promptCreateConfig():

    # Create new config file, prompt user to fill in data.
    print("SETUP Brenderer")
    blender_path = inquirer.filepath(
        message="Enter the path to your blender executable.",
        default="/home/$user/Documents/blender/blender"
    ).execute()

    input_path = inquirer.filepath(
        message="Enter the folder to read all .blend files. (If left empty, you have to manually indicate the location every time)",
        default="/home/$user/Documents/blender_render_pool"
    ).execute()

    output_path = inquirer.filepath(
        message="Enter the folder to store all rendered artifacts.",
        default="/home/$user/Documents/blender_render_result"
    ).execute()

    # Compile information and write to config.json
    with open(CONFIG_DATA_PATH, "w", encoding="utf-8") as cfg:
        json.dump(
            {
                "blender_path": blender_path,
                "input_path": input_path,
                "output_path": output_path
            },
            cfg, indent=2, ensure_ascii=False
        )

    print("Config file created successfully! Rerun `brender` to start. Write `brender config` to edit the config file.")

def promptNewRenderJob()->tuple[butil.BRender, dict]:

    # Ask user for all necessary information, then send them to job submitter.
    print("CREATE new render job")

    # First get list of files under the input folder
    blend_files:list[str] | None = None
    try:
        blend_folder = Path(CONFIG_DATA["input_path"])
        blend_files = [str(path) for path in blend_folder.iterdir() if path.is_file()]
    except Exception as e:
        print("Fetch blend files FAILED. Fix your input_path in your config file.")
        print(e)

    input_path = ""
    if blend_files is None:
        input_path = inquirer.filepath(
            message="Choose the location of your blend file"
        ).execute()
    else:
        blend_files.append("Other...")
        input_path = inquirer.fuzzy(
            message="Choose a blend file:",
            choices=blend_files
        ).execute()

        if input_path == "Other...":
            input_path = inquirer.filepath(
                message="Choose the location of your blend file"
            ).execute()

    output_path = ""
    # If config data misses output_path field or the field is empty, prompt the user for a path
    try:
        if CONFIG_DATA["output_path"] == "":
            raise Exception("Wrong or empty path field")
        else:
            output_path = os.path.join(CONFIG_DATA["output_path"], Path(input_path).stem)
    except:
        output_path = inquirer.filepath(
            "Choose the folder to store your output:"
        ).execute()

    start_frame = inquirer.text(
        message="Enter start frame: ",
        validate=lambda value: value.isdigit(),
        invalid_message="This field has to be a number."
    ).execute()
    start_frame = int(start_frame)

    end_frame = inquirer.text(
        message="Enter end frame: ",
        validate=lambda value: value.isdigit(),
        invalid_message="This field has to be a number."
    ).execute()
    end_frame = int(end_frame)

    file_type = inquirer.fuzzy(
        message="Choose file format for generated frames (no relation to video, since video generation is in a different step)",
        choices=["PNG", "JPEG"]
    ).execute()

    generate_video = inquirer.confirm(
        message="Do you want brender to automatically compose video after rendering?",
        default=False
    ).execute()

    video_framerate = 24
    if generate_video:
        video_framerate = inquirer.text(
            message="Enter the desire framerate for video",
            default="24",
            validate=lambda value: value.isdigit(),
            invalid_message="This field has to be a number."
        ).execute()

    # Print summary, and ask for user confirmation
    printJobSubmitSummary(input_path, output_path, start_frame, end_frame, file_type, generate_video, video_framerate)
    start_job_confirm = inquirer.confirm(
        message="Is the information above CORRECT? If confirmed, brender will start your job immediately!",
        default=True
    ).execute()

    # Terminate this operation if not confirmed. Otherwise return a generated BRender Object
    if not start_job_confirm:
        raise Exception("User not confirmed")

    return (
        butil.BRender(
            CONFIG_DATA["blender_path"],
            input_path,
            output_path,
            start_frame,
            end_frame,
            file_type
        ),
        {
            "do_video": generate_video,
            "fps": video_framerate
        }
    )

def printJobSubmitSummary(
        input_path, 
        output_path, 
        start_frame, 
        end_frame, 
        file_type, 
        do_video, 
        vid_framerate):

    print("==========[RENDER JOB SUMMARY]==========")
    print(f"File     : {input_path}")
    print(f"Output   : {output_path}")
    print(f"Start    : Frame {start_frame}")
    print(f"End      : Frame {end_frame}")
    print(f"Img Type : Frame {file_type}")
    print(f"Video?   : {do_video}")
    print(f"FPS      : {vid_framerate} fps")
    print("========================================")

def printJobStatusPanel(job:butil.BRender, progress:Progress, progressTask, elapsed):
    status = job.getStatus()

    # Update progress bar
    progress.update(progressTask, completed=status["progress"] * 100)

    # File name
    title = Text(
        job.inputPath.split("/")[-1],
        style="bold"
    )

    # State
    state = Text(
        status["state"].capitalize(),
        style="bold green"
    )

    # Data table
    info = Table.grid(
        padding=(0, 2)
    )

    info.add_column(style="bold")
    info.add_column()

    info.add_row(
        "Frame",
        f"{status['frame']} / {status['endFrame']}"
    )

    info.add_row(
        "Samples",
        f"{status['sample']} / {status['totalSamples']}"
    )

    info.add_row(
        "Elapsed",
        time.strftime(
            "%H:%M:%S",
            time.gmtime(elapsed)
        )
    )

    info.add_row(
        "Output",
        job.outputPath
    )

    # Combine everything
    content = Group(
        title,
        Text(""),
        state,
        progress,
        Text(""),
        info
    )

    return Panel(
        content,
        title="BRender",
        border_style="blue",
        padding=(1, 2)
    )

def submitRenderJob(job:butil.BRender):

    job.render()

    progress = Progress(
        BarColumn(),
        TaskProgressColumn(),
        expand=True,
        auto_refresh=False
    )

    progressTask = progress.add_task(
        "Rendering",
        total=100
    )

    startTime = time.time()

    with Live(refresh_per_second=10, console=console) as live:

        while True:
            status = job.getStatus()

            elapsed = time.time() - startTime

            display = printJobStatusPanel(
                job,
                progress,
                progressTask,
                elapsed
            )

            live.update(display)

            if status["state"] != "rendering":
                break

            time.sleep(0.5)

    # Print post-job information. WIP
    print(f"Job finished with status: {job.getStatus()["state"]}")
    print(f"Frame has been stored to: {job.outputPath}")


if __name__ == "__main__":

    print(f"brender by kimsseTheWolf: Version {VERSION}")

    # Try to load config file. If config file does not exists, prompt to create a new one!
    if not os.path.exists(CONFIG_DATA_PATH):
        promptCreateConfig()
        sys.exit(0)

    with open(CONFIG_DATA_PATH, "r", encoding="utf-8") as cfg:
        try:
            CONFIG_DATA = json.load(cfg)
        except Exception as e:
            print("Invalid config file. Check if there is a typo for json structure? Also use `brender config` to edit config file.")
            print(e)
            sys.exit(1)

    # Check passed in parameters, to see what operations the program will proceed?

    if len(sys.argv) == 1:
        # Initiate render job prompt. Will have try/except after development
        (new_job, vid_job) = promptNewRenderJob()

        # Submit the job
        submitRenderJob(new_job)

        # Process the video job WIP

        sys.exit(0)
        pass
    elif len(sys.argv) >= 2:
        # Check the sub-command and arguments to performe other actions.WIP
        pass
    else:
        print("Invalid argument. Type `brender help` for help.")
        sys.exit(1)
    pass
