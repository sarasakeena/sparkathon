import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import load_model  # type: ignore
import streamlit as st
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os

# -------- LOAD ENV & MODEL --------
load_dotenv()
sender_email = os.getenv("SENDER_EMAIL")
app_password = os.getenv("APP_PASSWORD")
model = load_model("lstm_milk_model.h5", compile=False)

# -------- STREAMLIT CONFIG --------
st.set_page_config(page_title="ShadowStock", layout="wide")
st.sidebar.title("📊 Navigation")
page = st.sidebar.radio("Go to", ["📈 Forecast Plot", "🚨 Alerts Dashboard"])

# -------- LOAD DATA --------
sales_df = pd.read_csv("walmart_sales_simulated.csv")
inventory_df = pd.read_csv("walmart_inventory_sample.csv")

# -------- FILTER PRODUCT & STORE --------
product_id = 'MILK001'
store_id = 'STORE101'

filtered_sales = sales_df[
    (sales_df['Product_ID'] == product_id) &
    (sales_df['Store_ID'] == store_id)
].copy()

filtered_sales['Timestamp'] = pd.to_datetime(filtered_sales['Timestamp'])
filtered_sales.sort_values('Timestamp', inplace=True)
filtered_sales.set_index('Timestamp', inplace=True)

resampled_sales = filtered_sales['Units_Sold'].resample('h').sum().fillna(0)
scaler = MinMaxScaler()
scaled_sales = scaler.fit_transform(resampled_sales.values.reshape(-1, 1))

# -------- CREATE SEQUENCES --------
def create_sequences(data, seq_length):
    X, y = [], []
    for i in range(len(data) - seq_length):
        X.append(data[i:i+seq_length])
        y.append(data[i+seq_length])
    return np.array(X), np.array(y)

sequence_length = 24
X, y = create_sequences(scaled_sales, sequence_length)
split = int(len(X) * 0.8)
X_train, X_test = X[:split], X[split:]
y_train, y_test = y[:split], y[split:]

# -------- PREDICT --------
y_pred = model.predict(X_test)
y_pred_inv = scaler.inverse_transform(y_pred)
y_test_inv = scaler.inverse_transform(y_test)

# -------- PHANTOM STOCKOUT DETECTION --------
try:
    backroom_stock = inventory_df[inventory_df['Product_ID'] == product_id]['Backroom_Stock'].values[0]
except IndexError:
    backroom_stock = 0

threshold = 1
phantom_alerts = []

for i in range(len(y_test_inv)):
    predicted = y_pred_inv[i][0]
    actual = y_test_inv[i][0]
    timestamp = resampled_sales.index[split + i + sequence_length]
    if predicted - actual > threshold and backroom_stock > 0:
        phantom_alerts.append({
            'Timestamp': timestamp,
            'Store': store_id,
            'Product': product_id,
            'Predicted Sales': round(predicted, 2),
            'Actual Sales': round(actual, 2),
            'Backroom Stock': backroom_stock
        })

if phantom_alerts:
    alerts_df = pd.DataFrame(phantom_alerts)
    alerts_df.to_csv("phantom_stockout_alerts.csv", index=False)
else:
    alerts_df = pd.DataFrame()

# -------- EMAIL FUNCTION --------
def send_email_alert(alerts_df, recipient_email):
    if alerts_df.empty:
        st.warning("No alerts to email.")
        return

    if sender_email is None or app_password is None:
        st.error("Missing email credentials in .env")
        return

    subject = "🚨 Phantom Stockout Alert"
    body = "The following phantom stockouts have been detected:\n\n"
    body += alerts_df.to_string(index=False)

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = recipient_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, app_password)
            server.sendmail(sender_email, recipient_email, message.as_string())
        st.success("✅ Email sent successfully!")
    except Exception as e:
        st.error(f"❌ Failed to send email: {e}")

# ===============================
# PAGE 1: Forecast Plot
# ===============================
if page == "📈 Forecast Plot":
    st.subheader("📈 LSTM Sales Forecast")

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(y_test_inv, label='Actual Sales', color='blue')
    ax.plot(y_pred_inv, label='Predicted Sales', color='orange')
    ax.set_title(f"LSTM Forecast for {product_id} in {store_id}")
    ax.set_xlabel("Time Step")
    ax.set_ylabel("Units Sold")
    ax.legend()
    ax.grid(True)

    st.pyplot(fig)

# ===============================
# PAGE 2: Alert Dashboard
# ===============================
elif page == "🚨 Alerts Dashboard":
    st.subheader("🚨 Phantom Stockout Alerts")

    try:
        if alerts_df.empty:
            st.info("✅ No Phantom Stockouts Detected.")
        else:
            st.success(f"{len(alerts_df)} Phantom Stockouts Detected.")
            # Optional filters
            store_filter = st.selectbox("Filter by Store", ["All"] + sorted(alerts_df['Store'].unique()))
            product_filter = st.selectbox("Filter by Product", ["All"] + sorted(alerts_df['Product'].unique()))

            filtered = alerts_df.copy()
            if store_filter != "All":
                filtered = filtered[filtered['Store'] == store_filter]
            if product_filter != "All":
                filtered = filtered[filtered['Product'] == product_filter]

            st.dataframe(filtered, use_container_width=True)
            st.download_button("📥 Download CSV", data=filtered.to_csv(index=False), file_name="phantom_stockout_alerts.csv")

            if st.button("📧 Send Alert Email"):
                send_email_alert(filtered, recipient_email="sarasakeena@gmail.com")

    except FileNotFoundError:
        st.error("⚠️ phantom_stockout_alerts.csv not found.")
