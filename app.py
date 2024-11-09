from flask import Flask, jsonify, request
import requests
import pandas as pd
import numpy as np
import clicksend_client
from clicksend_client import SmsMessage
from apscheduler.schedulers.background import BackgroundScheduler
import time
from datetime import datetime, timedelta

# Initialize the Flask app
app = Flask(__name__)

# Define a basic route
@app.route('/')
def home():
    return "Hello, World!"

@app.route("/api/pricedata",methods = ["GET"])
def get_price_data():
    """
    API Endpoint to fetch AEMO 5-minutely price data and return the list of data in json form
    """
    url = "https://api.opennem.org.au/stats/price/NEM/SA1"

    params = {"forecasts": False}

    response = requests.get(url = url, params = params).json()

    price_series = response["data"][0]["history"]["data"]

    return jsonify(price_series)

@app.route("/sendtext", methods = ["POST"])
def send_text():
    # Read Data from Post
    data = request.get_json()

    # Data validation
    if not data or "To" not in data or "Body" not in data:
        return "Missing data within request", 400

    # Configure HTTP basic authorization: BasicAuth
    configuration = clicksend_client.Configuration()
    configuration.username = 'jBurg0909'
    configuration.password = '299F68B3-B217-4AD2-8A06-6CC7CDE97DD4'

    # create an instance of the API class
    api_instance = clicksend_client.SMSApi(clicksend_client.ApiClient(configuration))

    # If you want to explictly set from, add the key _from to the message.
    sms_message = SmsMessage(source="php",
                            body=data["Body"],
                            to=data["To"],
                            _from=data["From"],
                            schedule=1436874701)

    sms_messages = clicksend_client.SmsMessageCollection(messages=[sms_message])

    # Send sms message(s)
    api_response = api_instance.sms_send_post(sms_messages)
    
    return "Text Sent"

def standard_operations():

    # Fetch AEMO Data
    url = "http://127.0.0.1:5000/api/pricedata"
    response = requests.get(url)
    price_series = response.json()

    # Instantiate Message Data
    text_url = "http://localhost:5000/sendtext"
    current_time_str = datetime.now().strftime("%d/%m/%y %I:%M %p")
    sms_data = {
        "To": "+61437505940",
        "From": "+61437505940",
        "Body": ""
    }

    # Set Limit
    price_limit = 100.0

    # Message Logic
    if (price_series[-1] >= price_limit) and (price_series[-2] < price_limit):
        sms_data["Body"] = f"SPOT MARKET PRICE ALERT - {current_time_str}\n\nPrice is trading ABOVE the prescribed operating limit of ${price_limit}/MWh, currently trading at: ${price_series[-1]}/MWh. You will be notified once the price returns below the limit."
        response = requests.post(text_url, json=sms_data)

    if (price_series[-1] < price_limit) and (price_series[-2] >= price_limit):
        sms_data["Body"] = f"SPOT MARKET PRICE ALERT - {current_time_str}\n\nPrice has returned BELOW the prescribed operating limit of ${price_limit}/MWh, current trading at: ${price_series[-1]}/MWh."
        response = requests.post(text_url, json=sms_data)

scheduler = BackgroundScheduler()
scheduler.add_job(standard_operations,"interval",minutes=5)
scheduler.start()

# Run the app
if __name__ == '__main__':
    try:
        app.run(debug=True,use_reloader=False)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown(wait=False)
    