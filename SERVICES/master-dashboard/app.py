from flask import Flask, render_template
import os

app = Flask(__name__)

@app.route('/')
def dashboard():
    return render_template('index.html')

if __name__ == '__main__':
    # Listen on 0.0.0.0:3000 (Nginx will proxy /dashboards to this)
    app.run(host='0.0.0.0', port=3000)

