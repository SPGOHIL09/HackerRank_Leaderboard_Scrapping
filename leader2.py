import requests
import getpass
import sys
import math
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
import pandas as pd
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'some_random_secret_key'  # Required for flashing messages

HEADERS = {
    'User-Agent': 'Mozilla/5.0'
}

def get_contests(email, password):
    url = "https://www.hackerrank.com/rest/administration/contests"
    params = {"offset": 0, "limit": 100}
    response = requests.get(url, params=params, auth=(email, password), headers=HEADERS)

    if response.status_code != 200 or not response.json().get("status", False):
        return None  # Return None if credentials are invalid or error

    return response.json().get("models", [])

def get_full_leaderboard(email, password, slug):
    all_entries = []
    offset = 0
    limit = 100

    while True:
        url = f"https://www.hackerrank.com/rest/contests/{slug}/leaderboard"
        params = {"offset": offset, "limit": limit}
        response = requests.get(url, params=params, auth=(email, password), headers=HEADERS)

        if response.status_code != 200:
            break

        data = response.json().get("models", [])
        if not data:
            break

        all_entries.extend(data)
        offset += limit

    return all_entries

def save_to_excel(leaderboard, path):
    df = pd.DataFrame(leaderboard)
    df = df[['rank', 'hacker', 'score']]
    df.columns = ['Rank', 'Username', 'Score']
    df.to_excel(path, index=False)

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        contests = get_contests(email, password)
        if contests is None:
            flash("Invalid email or password. Please try again.")
            return redirect(url_for('login'))
        return render_template("contests.html", contests=contests, email=email, password=password)
    return render_template("login.html")

@app.route('/download', methods=['POST'])
def download():
    slug = request.form['slug']
    email = request.form['email']
    password = request.form['password']

    contests = get_contests(email, password)
    contest = next((c for c in contests if c['slug'] == slug), None)
    if not contest:
        return redirect(url_for('login'))

    contest_name = secure_filename(contest['name'])
    leaderboard = get_full_leaderboard(email, password, slug)

    os.makedirs('static/downloads', exist_ok=True)
    file_name = f"{contest_name}.xlsx"
    file_path = os.path.join('static/downloads', file_name)
    save_to_excel(leaderboard, file_path)

    top3 = sorted(leaderboard, key=lambda x: x['rank'])[:3]
    return render_template("top3.html", contest_name=contest_name, top3=top3, file_name=file_name)

@app.route('/download_file/<filename>')
def download_file(filename):
    file_path = os.path.join('static/downloads', filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    flash("File not found.")
    return redirect(url_for('login'))


if __name__ == "__main__":
    app.run(debug=True)
