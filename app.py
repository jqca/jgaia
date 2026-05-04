import os
from flask import Flask, send_file, send_from_directory

app = Flask(__name__, static_folder="static")

@app.route("/")
def index():
    return send_file("index.html")

@app.route("/static/<path:path>")
def static_files(path):
    return send_from_directory("static", path)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
