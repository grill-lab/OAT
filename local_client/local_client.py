import os
from flask import Flask, render_template, request
import requests
from waitress import serve
from utils import logger

app = Flask(__name__)
CONFIG = {}


@app.route('/')
def app_interface():
    return render_template("chat.html")


@app.route('/getresponse', methods=['POST', 'GET'])
def introducer():

    session = request.values.to_dict()
    response = requests.post(os.environ['DISTRIBUTOR_URL']+'/run', json=session)
    json_response = response.json()
    screen = json_response.get('screen')
    if screen:
        screen_format = screen.get('format')
        if screen_format:
            screen_format = screen_format.lower()
            template = render_template(f'{screen_format}.html')
            json_response['template'] = template
    return json_response


if __name__ == "__main__":
    logger.info("Local Client will run on port 8000")
    serve(app, host='0.0.0.0', port=8000)
    # app.run(host='0.0.0.0', port=8000, debug=True)
