from InquirerPy import inquirer
from pathlib import Path
import os
import json
import sys
import butil

# Import configs from json config file
CONFIG_DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
VERSION = "1.0"

def promptCreateConfig():

    # Create new config file, prompt user to fill in data.
    print("SETUP Brenderer")
    blender_path = inquirer.filepath(
        message="Enter the path to your blender executable. (If it is already in path, enter the command here)",
        default="/home/$user/Documents/blender/blender"
    ).execute()

    input_path = inquirer.filepath(
        message="Enter the folder to read all .blend files. (If left empty, you have to manually indicate the location every time)",
        default="/home/$user/Documents/blender_render_pool"
    ).execute()

    output_path = inquirer.filepath(
        message="Enter the foldvideo_framerateer to store all rendered artifacts.",
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
    except:
        print("Fetch blend files FAILED. Fix your input_path in your config file.")

    input_path = ""
    if not blend_files is None:
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

def submitRenderJob(job:butil.BRender):

    job.render()

    # Display data here. WIP
    while job.getStatus()["state"] == "rendering":
        print("job is still rendering")

    # Print post-job information. WIP
    print(f"Job status: {job.getStatus()["state"]}")
    print(f"Framew has been stored to: {job.outputPath}")


if __name__ == "__main__":

    print(f"brender by kimsseTheWolf: Version {VERSION}")

    # Try to load config file. If config file does not exists, prompt to create a new one!
    if not os.path.exists(CONFIG_DATA_PATH):
        promptCreateConfig()
        sys.exit(0)

    with open(CONFIG_DATA_PATH, "r", encoding="utf-8") as cfg:
        try:
            CONFIG_DATA = json.load(cfg)
        except:
            print("Invalid config file. Check if there is a typo for json structure? Also use `brender config` to edit config file.")
            sys.exit(1)

    # Check passed in parameters, to see what operations the program will proceed?

    if len(sys.argv) == 1:
        # Initiate render job prompt
        try:
            new_job = promptNewRenderJob()
        except Exception:
            sys.exit(1)

        
        submitRenderJob(new_job)
        pass
    elif len(sys.argv) >= 2:
        # Check the sub-command and arguments to performe other actions.WIP
        pass
    else:
        print("Invalid argument. Type `brender help` for help.")
        sys.exit(1)
    pass
