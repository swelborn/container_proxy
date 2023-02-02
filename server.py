#!/global/common/shared/das/python3/bin/python

from sanic import Blueprint

from sanic import Sanic
from sanic.response import json
from runner import Runner
from queue import Empty
import time
import os
import uuid
import socket
import signal, os

socket_file = os.environ.get("PROXY_SOCKET")

bp = Blueprint('my_blueprint')

@bp.listener('after_server_stop')
async def close_connection(app, loop):
    os.unlink(socket_file)


app = Sanic("App Name", configure_logging=False)
app.blueprint(bp)

runner = Runner()

procs = dict()

def run(cmd):
    job_id = str(uuid.uuid1())
    # Strip off a path to avoid a looop
    cmd[0] = cmd[0].split('/')[-1]
    procs[job_id] = runner.run(cmd)
    return job_id

def read_output(job_id):
    in_q = procs[job_id].q
    msgs = []
    try:
        # Flush the queue
        while True:
            msg = in_q.get(block=False)
            msgs.append(msg)
    except Empty:
        pass
    return {'msgs': msgs}

  


@app.route("/",)
async def test(request):
    return json({"hello": "world"})

@app.route("/submit", methods=["POST"])
def post_json(request):
  data = request.json
  jid = run(data['cmd'])
  return json({ "received": True, "jid": jid})

@app.route("/output/<jid>")
async def output(request, jid):
  msgs = read_output(jid)
  return json(msgs)

def remove_path():
    script = os.path.realpath(__file__)
    sdir = os.path.dirname(script)
    path = os.environ.get("PATH")
    if sdir in path:
        items = path.split(":")
        for item in items:
            if sdir in item:
               items.remove(item)
        newpath = ':'.join(items)
        os.environ["PATH"] = newpath

if __name__ == "__main__":
    # Set the signal handler and a 5-second alarm
    remove_path()
    sock = socket.socket(socket.AF_UNIX)
    sock.bind(socket_file)
    app.run(sock=sock, access_log=False)
