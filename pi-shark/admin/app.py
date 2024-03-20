#!/pi-shark/admin/.venv/bin/python

from flask import Flask

app = Flask(__name__)

if __name__ == '__main__':
    app.run(host='0.0.0.0')

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"