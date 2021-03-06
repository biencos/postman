import os
import logging
from datetime import datetime, timedelta

from dotenv import load_dotenv
from redis import Redis
from flask import Flask, render_template, make_response, request, flash, url_for, session
from flask_session import Session
from bcrypt import hashpw, gensalt, checkpw
import jwt
import requests
from authlib.integrations.flask_client import OAuth
from six.moves.urllib.parse import urlencode


load_dotenv()
REST_API_URL = os.getenv("REST_API_URL")

DB_HOST = os.getenv("DB_HOST")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NUMBER = os.getenv("DB_NUMBER")
db = Redis(host=DB_HOST, password=DB_PASSWORD, db=DB_NUMBER)

SESSION_REDIS = db
SESSION_TYPE = 'redis'

app = Flask(__name__)
app.config.from_object(__name__)
ses = Session(app)
logging.basicConfig(level=logging.INFO)

oauth = OAuth(app)

auth0 = oauth.register(
    'auth0',
    client_id=os.getenv("AUTH0_CLIENT_ID"),
    client_secret=os.getenv("AUTH0_CLIENT_SECRET"),
    api_base_url='https://' + os.getenv("AUTH0_DOMAIN"),
    access_token_url='https://' + os.getenv("AUTH0_DOMAIN") + '/oauth/token',
    authorize_url='https://' + os.getenv("AUTH0_DOMAIN") + '/authorize',
    client_kwargs={
        'scope': 'openid profile email',
    },
)


# AUTH0
@app.route('/auth/login')
def load_auth0():
    return auth0.authorize_redirect(redirect_uri=os.getenv("AUTH0_CALLBACK_URL"), audience=os.getenv("AUTH0_AUDIENCE"))


@app.route('/callback')
def handle_callback():
    auth0.authorize_access_token()
    userinfo = auth0.get('userinfo').json()
    username = userinfo['name']

    flash(f"Witaj z powrotem {username}")
    session["username"] = username
    session["login-method"] = "auth0"
    session["logged-at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")

    token = generate_jwt_token(username)
    logging.info(f"Token (Auth0): {token}")

    response = make_response('', 302)
    response.headers['Location'] = url_for('load_dashboard')
    return response


# HOME
@app.route('/')
def load_home():
    return render_template("home.html")


# REGISTER
@app.route('/sender/register')
def load_register():
    return render_template("register.html")


@app.route('/sender/register', methods=['POST'])
def register():
    if not request.form.get('firstname') or not request.form.get('lastname') or not request.form.get('username') or not request.form.get('email') or not request.form.get('password') or not request.form.get('password1') or not request.form.get('address'):
        flash("Aby zarejestrować się, musisz wypełnić wszystkie pola!")

    firstname = request.form.get('firstname')
    lastname = request.form.get('lastname')
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    password1 = request.form.get('password1')
    address = request.form.get('address')

    if len(username) < 3 or len(username) > 12:
        flash("Nazwa użytkownika może mieć od 3 do 12 znaków")
    if len(password) < 8:
        flash("Hasło musi mieć conajmniej 8 znaków")
    if password != password1:
        flash("Podane hasła nie pasują do siebie!")
        response = make_response('', 302)
        response.headers['Location'] = url_for('load_register')
        return response

    if firstname and lastname and username and email and password and password1 and address:
        if db.hexists(f"user:{username}", "password"):
            flash(f"Nazwa użytkownika: {username} jest zajęta")
            response = make_response('', 302)
            response.headers['Location'] = url_for('load_register')
            return response

        password = password.encode()
        salt = gensalt(6)
        hashed = hashpw(password, salt)

        db.hset(f"user:{username}", "firstname", firstname)
        db.hset(f"user:{username}", "lastname", lastname)
        db.hset(f"user:{username}", "email", email)
        db.hset(f"user:{username}", "password", hashed)
        db.hset(f"user:{username}", "address", address)

        response = make_response('', 302)
        response.headers['Location'] = url_for('load_login')
        return response


# LOGIN
@app.route('/sender/login')
def load_login():
    return render_template("login.html")


@app.route('/sender/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')

    if not username:
        flash("Pole nazwa użytkownika jest puste!")
        response = make_response('', 302)
        response.headers['Location'] = url_for('load_login')
        return response
    if not password:
        flash("Pole hasło jest puste!")
        response = make_response('', 302)
        response.headers['Location'] = url_for('load_login')
        return response

    if verify(username, password):
        flash(f"Witaj z powrotem {username}")
        session["username"] = username
        session["login-method"] = "standard"
        session["logged-at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")

        token = generate_jwt_token(username)
        logging.info(f"Token: {token}")

        response = make_response('', 302)
        response.headers['Location'] = url_for('load_dashboard')
        return response
    else:
        flash("Nieprawidłowe dane logowania!")
        response = make_response('', 302)
        response.headers['Location'] = url_for('load_login')
        return response


def verify(username, password):
    p = password.encode()
    h = db.hget(f"user:{username}", "password")

    if h:
        return checkpw(p, h)
    else:
        return False


# DASHBOARD
@app.route('/sender/dashboard')
def load_dashboard():
    username = session.get("username")
    if username:
        return render_template('dashboard.html')
    else:
        flash("Ta akcja wymaga zalogowania!")
        response = make_response('', 302)
        response.headers['Location'] = url_for('load_login')
        return response


# LOGOUT
@app.route('/sender/logout')
def load_logout():
    is_logged_with_auth0 = False
    if session["login-method"] == "auth0":
        is_logged_with_auth0 = True

    session.clear()
    response = make_response('', 302)
    if is_logged_with_auth0:
        params = urlencode({'returnTo': url_for(
            'load_login', _external=True), 'client_id': auth0.client_id})
        url = auth0.api_base_url + '/v2/logout?' + params
    else:
        url = url_for('load_login')

    response.headers['Location'] = url
    return response


# LABELS
@app.route('/labels')
def load_labels():
    username = session.get("username")

    if not username:
        make_response(
            {"message": "First you need to log in", "status": "error"}, 401)

    h = generate_headers(generate_jwt_token(username))
    response = requests.get(f"{REST_API_URL}/sender/labels", headers=h)

    body = response.json()
    status = response.status_code
    return body, status


@app.route('/labels', methods=["POST"])
def add_label():
    username = session.get("username")

    if not username:
        make_response(
            {"message": "First you need to log in", "status": "error"}, 401)

    h = generate_headers(generate_jwt_token(username))
    d = request.form
    response = requests.post(
        f"{REST_API_URL}/sender/labels", headers=h, data=d)

    body = response.text
    status = response.status_code
    return body, status


@app.route('/labels/<label_id>', methods=["DELETE"])
def delete_label(label_id):
    username = session.get("username")

    if not username:
        make_response(
            {"message": "First you need to log in", "status": "error"}, 401)

    h = generate_headers(generate_jwt_token(username))
    response = requests.delete(
        f"{REST_API_URL}/sender/labels/{label_id}", headers=h)

    body = response.text
    status = response.status_code
    return body, status

    """ if not db.sismember(f"user:{username}:labels", label_id):
        make_response(
            {"message": f"This label for user {username} doesn't exist", "status": "error"}, 403)

    db.delete(f"label:{label_id}")
    db.srem(f"user:{username}:labels", label_id)
    return "Label deleted", 200 """


@app.route('/labels/<label_id>', methods=["PUT"])
def change_label_sent_status(label_id):
    username = session.get("username")

    if not username:
        make_response(
            {"message": "First you need to log in", "status": "error"}, 401)

    h = generate_headers(generate_jwt_token(username))
    response = requests.put(
        f"{REST_API_URL}/sender/labels/{label_id}", headers=h)

    body = response.text
    status = response.status_code
    return body, status


# NOTIFICATIONS
@app.route('/sender/notifications')
def load_notifications():
    username = session.get("username")
    if username:
        return render_template('notifications.html')
    else:
        flash("Ta akcja wymaga zalogowania!")
        response = make_response('', 302)
        response.headers['Location'] = url_for('load_login')
        return response


@app.route('/notifications')
def get_notifications():
    username = session.get("username")
    if not username:
        make_response(
            {"message": "First you need to log in", "status": "error"}, 401)

    h = generate_headers(generate_jwt_token(username))
    response = requests.get(f"{REST_API_URL}/sender/notifications", headers=h)
    logging.info(response.status_code)
    logging.info(response.text)

    if response.status_code == 200:
        body = response.json()
    else:
        body = response.text
    status = response.status_code
    return body, status


if __name__ == '__main__':
    app.run()


def generate_jwt_token(username):
    USERTYPE = "sender"
    HOW_MANY_MINUTES_VALID = 10
    JWT_KEY = os.getenv("JWT_PRIVATE_KEY")
    if not username or not JWT_KEY:
        return ''

    experience_date = datetime.utcnow() + timedelta(minutes=HOW_MANY_MINUTES_VALID)
    return jwt.encode({'username': username, 'exp': experience_date, 'usertype': USERTYPE}, JWT_KEY, algorithm='HS256')
    # return jwt.encode({'username': username, 'exp': experience_date, 'usertype': USERTYPE}, JWT_KEY, algorithm='HS256').decode()


def generate_headers(token):
    headers = {}
    headers["Authorization"] = f"Bearer {token}"
    return headers
