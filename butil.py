import re
import os
import subprocess
import threading
from collections import deque

class TargetNotExistsError(Exception):
    pass

class RenderNotStartedError(Exception):
    pass

class BRender:

    def __init__(self,
                 blenderPath:str,
                 inputPath:str,
                 outputPath:str,
                 startFrame:int,
                 endFrame:int,
                 fileType:str):
        self.blenderPath = blenderPath
        self.inputPath = inputPath
        self.outputPath = outputPath
        self.startFrame = startFrame
        self.endFrame = endFrame
        self.fileType = fileType

        self.__isStarted = False
        self.__isError = False

        self.__renderProcess:subprocess.Popen | None = None
        self.__readerThread: threading.Thread | None = None

        # Stored last few lines, for debug purposes
        self.__output = deque(maxlen=100)

        # In-render status
        self.__currentFrame: int | None = None
        self.__currentSamples: int | None = None
        self.__totalSamples: int | None = None
        pass

    def __parseLine(self, line:str):

        # Current frame
        frameMatch = re.search(
            r"Fra:\s*(\d+)",
            line
        )

        if frameMatch:
            self.__currentFrame = int(frameMatch.group(1))

        # Current sample
        currSampleMatch = re.search(
            r"Rendering\s+(\d+)\s*/\s*(\d+)",
            line
        )

        if currSampleMatch:
            self.__currentSamples = int(currSampleMatch.group(1))
            self.__totalSamples = int(currSampleMatch.group(2))

    def __readOutput(self):

        if self.__renderProcess is None:
            return

        if self.__renderProcess.stdout is None:
            return

        for line in self.__renderProcess.stdout:
            line = line.rstrip()
            self.__output.append(line)
            self.__parseLine(line)

        
    
    def render(self):

        """
        Render the target file with most basic information. This only handles the render
        job and does not care other tasks
        """

        # Validate files

        presult = (
            os.path.exists(self.blenderPath),
            os.path.exists(self.inputPath),
        )

        if presult != (True, True):
            raise TargetNotExistsError("Blender executable or target blend file missing!")

        if not os.path.exists(self.outputPath):
            os.makedirs(self.outputPath, exist_ok=True)

        # Construct cmd
        output_pattern = os.path.join(self.outputPath, "####")
        cmd = [
            self.blenderPath, "--background",
            self.inputPath,
            "-o", output_pattern,
            "-F", self.fileType,
            "-s", str(self.startFrame),
            "-e", str(self.endFrame),
            "-a"
        ]

        self.__renderProcess = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        self.__isStarted = True
        self.__isError = False

        # Start parsing output
        self.__readerThread = threading.Thread(
            target=self.__readOutput,
            daemon=True
        )

        self.__readerThread.start()
        pass

    def getRecentOutput(self):
        return list(self.__output)

    def getStatus(self):

        """
        Return the current render progress of the render
        """

        if not self.__isStarted:
            raise RenderNotStartedError(
                "Render has not been started"
            )

        returnCode = self.__renderProcess.poll()

        if returnCode is None:
            state = "rendering"

        elif returnCode == 0:
            state = "finished"

        else:
            state = "failed"
            self.__isError = True

        progress = self.__calculateProgress()

        return {
            "state": state,
            "frame": self.__currentFrame,
            "startFrame": self.startFrame,
            "endFrame": self.endFrame,
            "sample": self.__currentSamples,
            "totalSamples": self.__totalSamples,
            "progress": progress
        }


    def __calculateProgress(self):

        if self.__currentFrame is None:
            return 0.0

        totalFrames = (
            self.endFrame
            - self.startFrame
            + 1
        )

        completedFrames = (
            self.__currentFrame
            - self.startFrame
        )

        sampleProgress = 0.0

        if (
            self.__currentSamples is not None
            and self.__totalSamples
        ):
            sampleProgress = (
                self.__currentSamples
                / self.__totalSamples
            )

        progress = (
            completedFrames + sampleProgress
        ) / totalFrames

        return max(
            0.0,
            min(progress, 1.0)
        )

