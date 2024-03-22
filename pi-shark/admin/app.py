#!/pi-shark/admin/.venv/bin/python

import subprocess
from flask import Flask

venv_path = '/pi-shark/admin/.venv/'
app = Flask(__name__)

@app.route("/")

def activate_virtualenv(venv_path):
    activate_script = 'bin/activate'
    activate_cmd = f'source {venv_path}/{activate_script}'
    subprocess.run(activate_cmd, shell=True)

def hello_world():
    return "<p>Hello, World!</p>"

if __name__ == '__main__':
    activate_virtualenv(venv_path)
    app.run(host='0.0.0.0')
    hello_world()