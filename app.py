from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
import sqlite3
import joblib
import pandas as pd

app = Flask(__name__)
app.secret_key = "smart_soil_project_123"
latest_farm_data = {}
# ---------------- AI MODEL ----------------

model = joblib.load("ai_model/fertilizer_model.pkl")

crop_encoder = joblib.load("ai_model/crop_encoder.pkl")
soil_encoder = joblib.load("ai_model/soil_encoder.pkl")
fert_encoder = joblib.load("ai_model/fertilizer_encoder.pkl")


def get_fertilizer_prediction(
    crop,
    soil,
    ph,
    moisture,
    nitrogen,
    phosphorus,
    potassium,
    temperature,
    humidity
):

    crop_encoded = crop_encoder.transform([crop])[0]
    soil_encoded = soil_encoder.transform([soil])[0]

    input_df = pd.DataFrame({
        'Soil_Type': [soil_encoded],
        'Soil_pH': [ph],
        'Soil_Moisture': [moisture],
        'Nitrogen_Level': [nitrogen],
        'Phosphorus_Level': [phosphorus],
        'Potassium_Level': [potassium],
        'Temperature': [temperature],
        'Humidity': [humidity],
        'Crop_Type': [crop_encoded]
    })

    prediction = model.predict(input_df)

    fertilizer = fert_encoder.inverse_transform(prediction)

    return fertilizer[0]
# ---------------- DB INIT ----------------
def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS qa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT,
            answer TEXT
        )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        crop TEXT,
        temperature REAL,
        humidity REAL,
        fertilizer TEXT
    )
""")
    cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT
)
""")
    conn.commit()
    conn.close()

init_db()

# ---------------- MODEL ----------------
def predict(question):
    return f"Answer for: {question}"

# ---------------- SAVE ----------------
def save_to_db(question, answer):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO qa (question, answer) VALUES (?, ?)",
        (question, answer)
    )
    conn.commit()
    conn.close()

# ---------------- GET LAST ENTRY ----------------
def get_latest():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT question, answer FROM qa ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return row

def save_history(crop, temperature, humidity, fertilizer):

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO history
        (date, crop, temperature, humidity, fertilizer)
        VALUES (
            datetime('now'),
            ?, ?, ?, ?
        )
    """, (
        crop,
        temperature,
        humidity,
        fertilizer
    ))

    conn.commit()
    conn.close()

def get_history():

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT date,
               crop,
               temperature,
               humidity,
               fertilizer
        FROM history
        ORDER BY id DESC
    """)

    data = cursor.fetchall()

    conn.close()

    return data


# ---------------- ROUTES ----------------

@app.route("/")
def home():
    return redirect(url_for("login"))

@app.route("/home")
def home_page():

    if "user" not in session:
        return redirect(url_for("login"))

    return render_template("index.html")

@app.route("/digitaltwin")
def digitaltwin():

    if "user" not in session:
        return redirect(url_for("login"))

    return render_template("digitaltwin.html", farm=latest_farm_data)

@app.route("/fertilizer")
def fertilizer():

    if "user" not in session:
        return redirect(url_for("login"))

    return render_template("fertilizer.html")

@app.route("/history")
def history():

    if "user" not in session:
        return redirect(url_for("login"))

    records = get_history()

    return render_template(
        "history.html",
        records=records
    )

@app.route("/queries")
def queries():

    if "user" not in session:
        return redirect(url_for("login"))

    return render_template("queries.html")

@app.route("/submit_query", methods=["POST"])
def submit_query():

    question = request.form["question"]

    answer = (
        "Agriculture chatbot is temporarily unavailable. "
        "Please contact administrator."
    )

    return render_template(
        "queries.html",
        question=question,
        answer=answer
    )
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        )

        user = cursor.fetchone()

        conn.close()

        if user:
            session["user"] = username
            return redirect(url_for("home_page"))

        return "Invalid Username or Password!"

    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]
        confirm = request.form["confirm_password"]

        if password != confirm:
            return "Passwords do not match!"

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO users(username, password) VALUES (?, ?)",
                (username, password)
            )

            conn.commit()

        except sqlite3.IntegrityError:
            conn.close()
            return "Username already exists!"

        conn.close()

        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/predict", methods=["POST"])
def predict_fertilizer():

    if "user" not in session:
        return redirect(url_for("login"))

    crop = request.form["crop"]
    soil = request.form["soil"]
    ph = float(request.form["ph"])
    moisture = float(request.form["moisture"])
    nitrogen = float(request.form["nitrogen"])
    phosphorus = float(request.form["phosphorus"])
    potassium = float(request.form["potassium"])
    temperature = float(request.form["temperature"])
    humidity = float(request.form["humidity"])

    fertilizer = get_fertilizer_prediction(
        crop,
        soil,
        ph,
        moisture,
        nitrogen,
        phosphorus,
        potassium,
        temperature,
        humidity
    )

    save_history(
    crop,
    temperature,
    humidity,
    fertilizer
)

    global latest_farm_data

    latest_farm_data = {
        "crop": crop,
        "soil": soil,
        "ph": ph,
        "moisture": moisture,
        "nitrogen": nitrogen,
        "phosphorus": phosphorus,
        "potassium": potassium,
        "temperature": temperature,
        "humidity": humidity,
        "fertilizer": fertilizer
    }

    return render_template(
    "fertilizer.html",
    fertilizer=fertilizer,
    farm=latest_farm_data
)
@app.route("/submit", methods=["POST"])
def submit():
    question = request.form["question"]

    answer = predict(question)

    save_to_db(question, answer)

    # redirect safely
    return redirect(url_for("result"))

@app.route("/result")
def result():
    data = get_latest()
    return render_template("result.html", data=data)

@app.route("/logout")
def logout():

    session.pop("user", None)

    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)