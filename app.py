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
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        crop TEXT,
        temperature REAL,
        humidity REAL,
        fertilizer TEXT
    )
""")
    
    conn.commit()
    conn.close()

init_db()


# ---------------- GET LAST ENTRY ----------------


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

    cursor.execute("SELECT * FROM history")

    data = cursor.fetchall()

    print("HISTORY DATA:", data)

    conn.close()

    return data


# ---------------- ROUTES ----------------


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/home")
def home_page():
    return render_template("index.html")

@app.route("/fertilizer")
def fertilizer():

    return render_template("fertilizer.html")

@app.route("/digitaltwin")
def digitaltwin():

    return render_template("digitaltwin.html", farm=latest_farm_data)


@app.route("/history")
def history():

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM history")
    conn.commit()

    records = []

    conn.close()

    return render_template(
        "history.html",
        records=records
    )

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/predict", methods=["POST"])
def predict_fertilizer():

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

@app.route("/result")
def result():
    data = get_latest()

    return render_template("result.html", data=data)

if __name__ == "__main__":
    app.run(debug=True)