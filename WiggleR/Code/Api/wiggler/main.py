from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from crontab import CronTab
from datetime import datetime, timedelta
import os

IMG_FOLDER = './Pictures'
VID_FOLDER = './Videos'

app = FastAPI()

app.mount("/image", StaticFiles(directory=IMG_FOLDER), name="image")
app.mount("/video", StaticFiles(directory=VID_FOLDER), name="video")


def list_files(folder, path, extension):
    out = []
    for fileName in sorted(os.listdir(folder)):
        name, ext = os.path.splitext(fileName)
        if ext == extension:
            out.append({
                "name": name,
                "path": path + fileName
            })
    return out


@app.get("/")
def read_root():
    return {"Hello": "Worm"}


@app.get("/images")
def images():
    return list_files(IMG_FOLDER, '/image/', '.jpg')


@app.get("/take_picture")
def take_picture():
    now = datetime.now()
    fileName = now.strftime("%Y-%m-%d-%H-%M")
    filePath = f"{IMG_FOLDER}/{fileName}.jpg"
    os.system(
        f"libcamera-jpeg --width 1024 --height 768 --nopreview -t 1 -o {filePath}")
    return {"picture": f"image/{fileName}.jpg"}


@app.get("/schedule_picture/{minutes}")
def schedule_picture(minutes: int = 1):
    cron = CronTab(user=os.getlogin())
    cron.remove_all(comment='take picture')
    job = cron.new(command='curl localhost:8000/take_picture',
                   comment='take picture')
    job.minute.every(minutes)
    cron.write()
    return {"minutes": minutes}


@app.get("/videos")
def videos():
    return list_files(VID_FOLDER, '/video/', '.mp4')


@app.get("/timelapse/date/{date}")
def timelapse(date: str):
    os.system(
        f'ffmpeg -framerate 30 -pattern_type glob -i "./Pictures/{date}*.jpg" -s:v 1440x1080 -c:v libx264 -crf 17 -pix_fmt yuv420p ./Videos/{date}.mp4')
    return {
        "name": date,
        "path": f'/video/{date}.mp4'
    }


@app.get("/timelapse/yesterday")
def timelapse():
    yesterday = (datetime.now() - timedelta(1)).strftime('%Y-%m-%d')
    os.system(
        f'ffmpeg -framerate 30 -pattern_type glob -i "./Pictures/{yesterday}*.jpg" -s:v 1440x1080 -c:v libx264 -crf 17 -pix_fmt yuv420p ./Videos/{yesterday}.mp4')
    return {
        "name": yesterday,
        "path": f'/video/{yesterday}.mp4'
    }


@app.get("/timelapse/schedule")
def schedule_timelapse():
    cron = CronTab(user=os.getlogin())
    cron.remove_all(comment='take timelapse')
    job = cron.new(
        command='curl localhost:8000/timelapse/yesterday', comment='take timelapse')
    job.every().day()
    cron.write()
    return {"result": "yesterdays activity will be available every day"}


@app.get("/timelapse/stream/{date}")
async def video(date: str):
    def iterfile():
        with open(f'./Videos/{date}.mp4', mode="rb") as file_like:
            yield from file_like

    return StreamingResponse(iterfile(), media_type="video/mp4")
