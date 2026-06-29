from flask import Flask, render_template, request, jsonify, redirect
import sqlite3
import joblib
import pandas as pd
import matplotlib.pyplot as plt

app = Flask(__name__)
app.secret_key = "smart_soil_project_123"

# -----------------------------
# GLOBAL VARIABLE
# -----------------------------

latest_farm_data = {}

# -----------------------------
# LOAD AI MODEL
# -----------------------------

model = joblib.load("ai_model/fertilizer_model.pkl")

crop_encoder = joblib.load("ai_model/crop_encoder.pkl")
soil_encoder = joblib.load("ai_model/soil_encoder.pkl")
fert_encoder = joblib.load("ai_model/fertilizer_encoder.pkl")


# -----------------------------
# PREDICTION FUNCTION
# -----------------------------

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

        "Soil_Type":[soil_encoded],

        "Soil_pH":[ph],

        "Soil_Moisture":[moisture],

        "Nitrogen_Level":[nitrogen],

        "Phosphorus_Level":[phosphorus],

        "Potassium_Level":[potassium],

        "Temperature":[temperature],

        "Humidity":[humidity],

        "Crop_Type":[crop_encoded]

    })

    prediction = model.predict(input_df)

    fertilizer = fert_encoder.inverse_transform(prediction)

    return fertilizer[0]


# -----------------------------
# DATABASE
# -----------------------------

def init_db():

    conn = sqlite3.connect("database.db")

    cursor = conn.cursor()

    cursor.execute("""

    CREATE TABLE IF NOT EXISTS history(

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


# -----------------------------
# SAVE HISTORY
# -----------------------------

def save_history(
    crop,
    temperature,
    humidity,
    fertilizer
):

    conn = sqlite3.connect("database.db")

    cursor = conn.cursor()

    cursor.execute("""

    INSERT INTO history

    (

    date,

    crop,

    temperature,

    humidity,

    fertilizer

    )

    VALUES

    (

    datetime('now'),

    ?,?,?,?

    )

    """,

    (

        crop,

        temperature,

        humidity,

        fertilizer

    ))

    conn.commit()

    conn.close()


# -----------------------------
# GET HISTORY
# -----------------------------

def get_history():

    conn = sqlite3.connect("database.db")

    cursor = conn.cursor()

    cursor.execute("""

    SELECT

    date,

    crop,

    temperature,

    humidity,

    fertilizer

    FROM history

    ORDER BY id DESC

    """)

    records = cursor.fetchall()

    conn.close()

    return records

# -----------------------------
# HOME PAGE (ONE PAGE WEBSITE)
# -----------------------------

@app.route("/")
@app.route("/home")
def home():

    records = get_history()

    return render_template(
        "index.html",
        farm=latest_farm_data,
        fertilizer=None,
        records=records
    )


# -----------------------------
# PREDICT FERTILIZER
# -----------------------------

# -----------------------------
# PREDICT FERTILIZER
# -----------------------------

@app.route("/predict", methods=["POST"])
def predict():

    global latest_farm_data

    crop = request.form["crop"]
    soil = request.form["soil"]

    import json

    with open("database/sensor_data.json", "r") as f:
        sensor = json.load(f)

    temperature = sensor["temperature"]
    humidity = sensor["humidity"]

    moisture = sensor["soil"]
    ph = sensor["ph"]

    nitrogen = sensor["nitrogen"]
    phosphorus = sensor["phosphorus"]
    potassium = sensor["potassium"]

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

    save_history(
        crop,
        temperature,
        humidity,
        fertilizer
    )

    records = get_history()

    return render_template(
        "fertilizer.html",
        fertilizer=fertilizer,
        farm=latest_farm_data,
        records=records,
        sensor=sensor
    )


# -----------------------------
# SENSOR API
# -----------------------------

@app.route("/sensor")
def sensor():

    import json

    with open("database/sensor_data.json", "r") as f:
        data = json.load(f)

    return jsonify(data)


# -----------------------------
# FERTILIZER PAGE
# -----------------------------

@app.route("/fertilizer")
def fertilizer_page():

    import json

    with open("database/sensor_data.json", "r") as f:
        sensor = json.load(f)

    return render_template(
        "fertilizer.html",
        sensor=sensor,
        farm=latest_farm_data,
        fertilizer=None
    )

@app.route("/digitaltwin")
def digital_twin():

    import json

    with open("database/sensor_data.json", "r") as f:
        sensor = json.load(f)

    return render_template(
        "digitaltwin.html",
        sensor=sensor,
        farm=latest_farm_data
    )

@app.route("/history")
def history():

    records = get_history()

    return render_template(
        "history.html",
        records=records
    )

@app.route("/clear_history", methods=["POST"])
def clear_history():

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM history")

    conn.commit()
    conn.close()

    return redirect("/history")

@app.route("/analytics")
def analytics():

    import sqlite3
    import matplotlib.pyplot as plt
    import os

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT fertilizer, COUNT(*)
        FROM history
        GROUP BY fertilizer
    """)

    data = cursor.fetchall()
    conn.close()

    fertilizers = []
    counts = []

    for row in data:
        fertilizers.append(row[0])
        counts.append(row[1])

    plt.figure(figsize=(6,4))
    plt.bar(fertilizers, counts)
    plt.title("Fertilizer Recommendation Analytics")
    plt.xlabel("Fertilizer")
    plt.ylabel("Count")

    os.makedirs("static", exist_ok=True)
    plt.savefig("static/analytics.png")
    plt.close()

    return render_template("analytics.html")
# -----------------------------
# RUN APP
# -----------------------------

if __name__ == "__main__":
    app.run(debug=True)