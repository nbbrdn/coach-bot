import os

import psycopg2
from flask import Flask, render_template

app = Flask(__name__)


def get_db_connection():
    return psycopg2.connect(
        host="db",
        database=os.environ.get("POSTGRES_DB"),
        user=os.environ.get("POSTGRES_USER"),
        password=os.environ.get("POSTGRES_PASSWORD"),
    )


@app.route("/")
def index():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM dialogs;")
    dialogs = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("index.html", dialogs=dialogs)


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
