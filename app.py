from flask import Flask, render_template, request, jsonify, redirect
import sqlite3
import joblib
import pandas as pd
import matplotlib.pyplot as plt
import requests
import os

app = Flask(__name__)
app.secret_key = "smart_soil_project_123"

# =====================================================
# GLOBAL VARIABLE
# =====================================================
latest_farm_data = {

    "crop": "-",
    "soil": "-",

    "temperature": 0,
    "humidity": 0,

    "moisture": 0,
    "ph": 7,

    "nitrogen": 0,
    "phosphorus": 0,
    "potassium": 0,

    "fertilizer": "-",

    "ai_reason": "Run fertilizer prediction to view AI analysis."

}

# =====================================================
# LOAD AI MODEL
# =====================================================

model = joblib.load("ai_model/fertilizer_model.pkl")

crop_encoder = joblib.load("ai_model/crop_encoder.pkl")
soil_encoder = joblib.load("ai_model/soil_encoder.pkl")
fert_encoder = joblib.load("ai_model/fertilizer_encoder.pkl")


# =====================================================
# AI PREDICTION
# =====================================================

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


# =====================================================
# DATABASE
# =====================================================

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


# =====================================================
# SAVE HISTORY
# =====================================================

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


# =====================================================
# GET HISTORY
# =====================================================

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


# =====================================================
# FIREBASE SENSOR DATA
# =====================================================

def get_sensor_data():

    firebase_url = "https://fertilizer-recommendatio-76e97-default-rtdb.asia-southeast1.firebasedatabase.app/.json"

    response = requests.get(firebase_url)

    sensor = response.json()

    if sensor is None:
        sensor = {}

    sensor.setdefault("temperature", 0)
    sensor.setdefault("humidity", 0)
    sensor.setdefault("soil", 0)
    sensor.setdefault("rain", 0)
    sensor.setdefault("ph", 7)
    sensor.setdefault("nitrogen", 0)
    sensor.setdefault("phosphorus", 0)
    sensor.setdefault("potassium", 0)

    return sensor


# =====================================================
# SOIL HEALTH
# =====================================================

def get_ph_status(ph):

    if ph < 5.5:
        return "🔴 Highly Acidic"

    elif ph < 6.5:
        return "🟡 Slightly Acidic"

    elif ph <= 7.5:
        return "🟢 Neutral"

    else:
        return "🟠 Alkaline"


# =====================================================
# SMART ALERTS
# =====================================================

def get_alerts(sensor):

    alerts = []

    if sensor["ph"] < 5.5:
        alerts.append("⚠ Soil is Highly Acidic")

    if sensor["soil"] > 3000:
        alerts.append("💧 Irrigation Required")

    if sensor["temperature"] > 35:
        alerts.append("🔥 High Temperature")

    if sensor["rain"] > 3000:
        alerts.append("🌧 No Rain Detected")

    if len(alerts) == 0:
        alerts.append("✅ Farm Conditions are Normal")

    return alerts


# =====================================================
# HOME ROUTE
# =====================================================# =====================================================
# HOME PAGE
# =====================================================

@app.route("/")
@app.route("/home")
def home():

    sensor = get_sensor_data()

    records = get_history()

    # ==============================
    # Analytics Summary
    # ==============================

    total_predictions = len(records)

    # Most Used Fertilizer
    fert_count = {}

    crop_count = {}

    temp_sum = 0

    for row in records:

        fert = row[4]

        crop = row[1]

        temp = row[2]

        fert_count[fert] = fert_count.get(fert, 0) + 1

        crop_count[crop] = crop_count.get(crop, 0) + 1

        temp_sum += temp

    if len(fert_count) > 0:

        top_fertilizer = max(fert_count, key=fert_count.get)

    else:

        top_fertilizer = "-"

    if len(crop_count) > 0:

        top_crop = max(crop_count, key=crop_count.get)

    else:

        top_crop = "-"

    if len(records) > 0:

        avg_temp = round(temp_sum / len(records), 1)

    else:

        avg_temp = 0

    ph_status = get_ph_status(sensor["ph"])

    alerts = get_alerts(sensor)
    # Analytics Summary
    total_predictions = len(records)

    top_fertilizer = "-"
    top_crop = "-"
    avg_temp = round(sensor["temperature"], 1)

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT fertilizer, COUNT(*)
    FROM history
    GROUP BY fertilizer
    ORDER BY COUNT(*) DESC
    LIMIT 1
    """)
    row = cursor.fetchone()
    if row:
        top_fertilizer = row[0]

    cursor.execute("""
    SELECT crop, COUNT(*)
    FROM history
    GROUP BY crop
    ORDER BY COUNT(*) DESC
    LIMIT 1
    """)
    row = cursor.fetchone()
    if row:
        top_crop = row[0]

    conn.close()

    return render_template(

    "index.html",

    farm=latest_farm_data,

    fertilizer=None,

    records=records,

    sensor=sensor,

    ph_status=ph_status,

    alerts=alerts,

    total_predictions=total_predictions,

    top_fertilizer=top_fertilizer,

    top_crop=top_crop,

    avg_temp=avg_temp

)


# =====================================================
# PREDICT FERTILIZER
# =====================================================

@app.route("/predict", methods=["POST"])
def predict():

    global latest_farm_data

    sensor = get_sensor_data()

    temperature = sensor["temperature"]
    humidity = sensor["humidity"]

    moisture = sensor["soil"]
    ph = sensor["ph"]

    crop = request.form["crop"]
    soil = request.form["soil"]

    nitrogen = int(request.form["nitrogen"])
    phosphorus = int(request.form["phosphorus"])
    potassium = int(request.form["potassium"])

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
# ==========================================
# AI REASON
# ==========================================

    if fertilizer == "Urea":

        ai_reason = (
        f"AI analysis indicates that the Nitrogen level ({nitrogen} kg/ha) is comparatively low. "
        f"Urea is recommended because it contains a high percentage of Nitrogen (46%) which promotes healthy leaf growth, improves chlorophyll formation, and increases crop yield."
    )

    elif fertilizer == "DAP":

        ai_reason = (
        f"The soil requires additional Nitrogen ({nitrogen} kg/ha) and Phosphorus ({phosphorus} kg/ha). "
        f"DAP supplies both nutrients, encouraging strong root development, better flowering, and early plant establishment."
    )

    elif fertilizer == "MOP":

        ai_reason = (
        f"The Potassium level ({potassium} kg/ha) is below the desired range. "
        f"MOP provides Potassium, which improves water regulation, strengthens stems, enhances disease resistance, and increases crop quality."
    )

    elif fertilizer == "Compost":

        ai_reason = (
        "The AI detected that the soil can benefit from organic nutrient enrichment. "
        "Compost improves soil fertility, increases organic matter, enhances microbial activity, improves water retention, and gradually supplies essential nutrients for sustainable crop growth."
    )

    else:

        ai_reason = (
        "The AI analyzed crop type, soil type, sensor values, soil pH, soil moisture, temperature, humidity, and NPK levels before recommending the most suitable fertilizer."
    )
  

    latest_farm_data = {

        "crop": crop,
        "soil": soil,

        "temperature": temperature,
        "humidity": humidity,

        "moisture": moisture,
        "ph": ph,

        "nitrogen": nitrogen,
        "phosphorus": phosphorus,
        "potassium": potassium,

        "fertilizer": fertilizer,
        "ai_reason": ai_reason

    }

    save_history(

        crop,
        temperature,
        humidity,
        fertilizer

    )
    generate_analytics()

    records = get_history()

    ph_status = get_ph_status(ph)

    alerts = get_alerts(sensor)

    analytics = generate_analytics()

    return render_template(

    "index.html",

    farm=latest_farm_data,

    fertilizer=fertilizer,

    records=records,

    sensor=sensor,

    ph_status=ph_status,

    alerts=alerts,

    total_predictions=analytics["total_predictions"],

    top_fertilizer=analytics["top_fertilizer"],

    top_crop=analytics["top_crop"],

    avg_temp=analytics["avg_temp"]

)

# =====================================================
# SENSOR API
# =====================================================

@app.route("/sensor")
def sensor():

    sensor = get_sensor_data()

    return jsonify(sensor)
# =====================================================
# HISTORY PAGE
# =====================================================

@app.route("/history")
def history():

    records = get_history()

    sensor = get_sensor_data()

    ph_status = get_ph_status(sensor["ph"])

    alerts = get_alerts(sensor)

    return render_template(

        "index.html",

        farm=latest_farm_data,

        fertilizer=None,

        records=records,

        sensor=sensor,

        ph_status=ph_status,

        alerts=alerts

    )


# =====================================================
# CLEAR HISTORY
# =====================================================

@app.route("/clear_history", methods=["POST"])
def clear_history():

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM history")

    conn.commit()
    conn.close()

    return redirect("/")


# =====================================================
# GENERATE ANALYTICS
# =====================================================

def generate_analytics():

    records = get_history()

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT fertilizer, COUNT(*)
        FROM history
        GROUP BY fertilizer
    """)
    fertilizer_data = cursor.fetchall()

    cursor.execute("""
        SELECT crop, COUNT(*)
        FROM history
        GROUP BY crop
    """)
    crop_data = cursor.fetchall()

    conn.close()

    fertilizers = [x[0] for x in fertilizer_data]
    fert_counts = [x[1] for x in fertilizer_data]

    crops = [x[0] for x in crop_data]
    crop_counts = [x[1] for x in crop_data]

    os.makedirs("static", exist_ok=True)

    # Pie Chart
    if fert_counts:

        plt.figure(figsize=(5,5))

        plt.pie(
            fert_counts,
            labels=fertilizers,
            autopct="%1.1f%%",
            startangle=90,
            shadow=True,
            explode=[0.08]*len(fert_counts)
        )

        plt.title("Fertilizer Distribution")
        plt.tight_layout()
        plt.savefig("static/fertilizer_pie.png")
        plt.close()

    # Crop Graph
    if crop_counts:

        plt.figure(figsize=(6,4))

        colors = [
            "#4CAF50",
            "#2196F3",
            "#FFC107",
            "#9C27B0",
            "#FF5722",
            "#009688"
        ]

        bars = plt.bar(
            crops,
            crop_counts,
            color=colors[:len(crops)]
        )

        plt.title("Crop Prediction Count")
        plt.xlabel("Crop")
        plt.ylabel("Predictions")

        for bar in bars:

            plt.text(
                bar.get_x()+bar.get_width()/2,
                bar.get_height()+0.05,
                int(bar.get_height()),
                ha="center"
            )

        plt.tight_layout()
        plt.savefig("static/crop_bar.png")
        plt.close()

    sensor = get_sensor_data()

    total_predictions = len(records)

    top_fertilizer = "-"

    top_crop = "-"

    if fert_counts:
        top_fertilizer = fertilizers[fert_counts.index(max(fert_counts))]

    if crop_counts:
        top_crop = crops[crop_counts.index(max(crop_counts))]

    avg_temp = round(sensor["temperature"], 1)

    return {

    "records": records,

    "total_predictions": total_predictions,

    "top_fertilizer": top_fertilizer,

    "top_crop": top_crop,

    "avg_temp": avg_temp

}

@app.route("/analytics")
def analytics():

    records, fertilizers, fert_counts, crops, crop_counts = generate_analytics()

    sensor = get_sensor_data()

    total_predictions = len(records)

    top_fertilizer = "-"
    top_crop = "-"

    if fert_counts:
        top_fertilizer = fertilizers[fert_counts.index(max(fert_counts))]

    if crop_counts:
        top_crop = crops[crop_counts.index(max(crop_counts))]

    avg_temp = round(sensor["temperature"],1)

    ph_status = get_ph_status(sensor["ph"])
    alerts = get_alerts(sensor)

    return render_template(

        "index.html",

        farm=latest_farm_data,

        fertilizer=None,

        records=records,

        sensor=sensor,

        ph_status=ph_status,

        alerts=alerts,

        total_predictions=total_predictions,

        top_fertilizer=top_fertilizer,

        top_crop=top_crop,

        avg_temp=avg_temp

    )

# =====================================================
# RUN APP
# =====================================================

if __name__ == "__main__":

    app.run(debug=True)