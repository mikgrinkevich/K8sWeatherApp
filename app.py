import json
import os
import sqlite3
import urllib

from flask import Flask, redirect, request, url_for, render_template
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)

from oauthlib.oauth2 import WebApplicationClient
import requests

from db import init_db_command
from user import User

from datetime import date

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", None)
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", None)
GOOGLE_DISCOVERY_URL = ("https://accounts.google.com/.well-known/openid-configuration")

API=os.environ.get("API",None)
API_DATE=os.environ.get("API_DATE",None)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)

login_manager = LoginManager()
login_manager.init_app(app)

try:
    init_db_command()
except sqlite3.OperationalError:
    pass  # Assume it's already been created

client = WebApplicationClient(GOOGLE_CLIENT_ID)


@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)


@app.route("/about")
def about():
    if current_user.is_authenticated:
        return (
            "<p>Hello, {}! You're logged in! Email: {}</p>"
            "<div><p>Google Profile Picture:</p>"
            '<img src="{}" alt="Google profile pic"></img></div>'.format(
                current_user.name, current_user.email, current_user.profile_pic
            )
        )
    else:
        return '<a class="button" href="/login">Google Login</a>'


@app.route("/")
def index():
    if current_user.is_authenticated:
        return """
    <a class="button" href="/logout">Logout</a><br>
    <a class="button" href="/list/weather/days">Weather forecast 5 days</a><br>
    <a class="button" href="/list/weather/particular">Weather on a particular date</a><br>
    <a class="button" href="/about">about</a><br>
    <a class="button" href="/useragent">useragent</a>
    """
    else:
        return '<a class="button" href="/login">Google Login</a>'


def get_google_provider_cfg():
    return requests.get(GOOGLE_DISCOVERY_URL).json()


@app.route("/login")
def login():
    google_provider_cfg = get_google_provider_cfg()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]

    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=request.base_url + "/callback",
        scope=["openid", "email", "profile"],
    )
    return redirect(request_uri)


@app.route("/login/callback")
def callback():
    code = request.args.get("code")

    google_provider_cfg = get_google_provider_cfg()
    token_endpoint = google_provider_cfg["token_endpoint"]

    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=request.base_url,
        code=code,
    )

    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
    )

    client.parse_request_body_response(json.dumps(token_response.json()))

    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)

    if userinfo_response.json().get("email_verified"):
        unique_id = userinfo_response.json()["sub"]
        users_email = userinfo_response.json()["email"]
        picture = userinfo_response.json()["picture"]
        users_name = userinfo_response.json()["given_name"]
    else:
        return "User email not available or not verified by Google.", 400

    user = User(
        id_=unique_id, name=users_name, email=users_email, profile_pic=picture
    )

    if not User.get(unique_id):
        User.create(unique_id, users_name, users_email, picture)

    login_user(user)

    return redirect(url_for("index"))


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/list/weather/days", methods=['POST', 'GET'])
def city_weather():
    if current_user.is_authenticated:
        if request.method == 'POST':
            city = request.form['city']
        else:
            city = 'minsk'
        API = os.environ.get("API")
        source = urllib.request.urlopen(
            'https://api.openweathermap.org/data/2.5/forecast?q=' + city + '&appid=' + API).read()
        list_of_data = json.loads(source)
        data = [
            {
                "date": str(list_of_data['list'][0]['dt_txt']),
                "temp": str(list_of_data['list'][0]['main']['temp'] - 273),
                "city": str(list_of_data['city']['name']),
                "country": str(list_of_data['city']['country'])
            },
            {
                "date": str(list_of_data['list'][7]['dt_txt']),
                "temp": str(list_of_data['list'][7]['main']['temp'] - 273),
                "city": str(list_of_data['city']['name']),
                "country": str(list_of_data['city']['country'])
            },
            {
                "date": str(list_of_data['list'][15]['dt_txt']),
                "temp": str(list_of_data['list'][15]['main']['temp'] - 273),
                "city": str(list_of_data['city']['name']),
                "country": str(list_of_data['city']['country'])
            },
            {
                "date": str(list_of_data['list'][23]['dt_txt']),
                "temp": str(list_of_data['list'][23]['main']['temp'] - 273),
                "city": str(list_of_data['city']['name']),
                "country": str(list_of_data['city']['country'])
            },
            {
                "date": str(list_of_data['list'][31]['dt_txt']),
                "temp": str(list_of_data['list'][31]['main']['temp'] - 273),
                "city": str(list_of_data['city']['name']),
                "country": str(list_of_data['city']['country'])
            },
            {
                "date": str(list_of_data['list'][39]['dt_txt']),
                "temp": str(list_of_data['list'][39]['main']['temp'] - 273),
                "city": str(list_of_data['city']['name']),
                "country": str(list_of_data['city']['country'])
            }
        ]
        print(data)
        return render_template('weather.html', data=data)
    else:
        return '<a class="button" href="/login">Google Login</a>'

@app.route("/list/weather/particular", methods=['POST', 'GET'])
def weather_particular_date():
    if request.method == 'POST':
        date_for_api = request.form['date']
    else:
        date_for_api = str(date.today().strftime("%Y-%m-%d"))
    API_DATE = os.environ.get("API_DATE")
    weather_json = urllib.request.urlopen(
        'https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/minsk,bel/' + date_for_api + '?key=' + API_DATE).read()
    list_data = json.loads(weather_json)
    data = {
        "address": str(list_data['resolvedAddress']),
        "timezone": str(list_data['timezone']),
        "datetime": str(list_data['days'][0]['datetime']),
        "temperature": str(list_data['days'][0]['temp'] - 32) + 'C',
        "conditions": str(list_data['days'][0]['conditions']),
        "description": str(list_data['days'][0]['description']),
    }
    print(data)
    return render_template('particular_date.html', data=data)


@app.route("/useragent")
def useragent():
    user_agent = request.user_agent
    return (
        '<p>your platform is: {}</p>'
        '<p>your browser is: {}</p>'.format(user_agent.platform, user_agent.browser)
    )


if __name__ == "__main__":
    app.run(ssl_context="adhoc", debug=True,port=5000,host="0.0.0.0")