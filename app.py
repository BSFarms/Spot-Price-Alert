from flask import Flask, jsonify, request
import requests
import pandas as pd
import numpy as np
import clicksend_client
from clicksend_client import SmsMessage
from apscheduler.schedulers.background import BackgroundScheduler
import time
from datetime import datetime, timedelta
import os
import pytz

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
    configuration.password = os.environ["API_KEY"]

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

    utc_time = datetime.now(pytz.utc)
    local_time = utc_time.astimezone(pytz.timezone('Australia/Adelaide'))
    local_time_formatted = local_time.strftime("%d/%m/%y %I:%M %p")
    current_hour = local_time.hour
        
    # Fetch AEMO Data
    url = "https://sa-spot-market-electricity-price-alerter.onrender.com/api/pricedata"
    response = requests.get(url)
    price_series = response.json()
    
    # Time-limiting the Operation
    if 7 <= current_hour <= 19:
    
        # Instantiate Message Data
        text_url = "https://sa-spot-market-electricity-price-alerter.onrender.com/sendtext"
        sms_data = {
            "To": "+61419833448",
            "From": "+61437505940",
            "Body": ""
        }
    
        # Set Limit
        price_limit = 100.0
    
        # Message Logic
        if (price_series[-1] >= price_limit) and (price_series[-2] < price_limit):
            sms_data["Body"] = f"SPOT MARKET PRICE ALERT - {local_time_formatted}\n\nPrice is trading ABOVE the prescribed operating limit of ${price_limit}/MWh, currently trading at: ${price_series[-1]}/MWh. You will be notified once the price returns below the limit."
            response = requests.post(text_url, json=sms_data)
    
        if (price_series[-1] < price_limit) and (price_series[-2] >= price_limit):
            sms_data["Body"] = f"SPOT MARKET PRICE ALERT - {local_time_formatted}\n\nPrice has returned BELOW the prescribed operating limit of ${price_limit}/MWh, current trading at: ${price_series[-1]}/MWh."
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
