import pandas as pd
import streamlit as st
from datetime import timedelta, datetime, date
import plotly.graph_objects as go
import plotly.express as px
from funcs import get_data, write_to_sheet, check_input, add_whitespace, write_new_rows

# Settings
st.set_page_config(page_title="Fitness Tracker!", page_icon=None, layout="wide", initial_sidebar_state="auto", menu_items=None)

# Sidebar
spreadsheet_id = "1BAWUiSI8jV0hSmaD9b_68CaRgSca9J_Odb1TpWRYuZU"
range_name = "data!A:G"

st.sidebar.markdown("### Log :muscle: Minutes")
form = st.sidebar.form("log_time")
log_name = form.multiselect("Name", ["Lauren", "Tara"], default=["Lauren", "Tara"])
log_date = form.date_input("Date")
log_activity = form.selectbox("Activity", ["Bike", "Climb", "Eliptical", "Hike", "Stretching", "Yoga", "Walk", "Weights", "Other"])
log_minutes = form.number_input("Minutes", 0, 100, 30, 5)
log_distance = form.number_input("Distance (in miles)", step=0.01)
log_notes = form.text_area("Workout Notes", value="")

new_data = get_data(spreadsheet_id, "new_data!A:H")
new_data = pd.DataFrame(new_data[1:], columns=new_data[0])
cols = ["Day", "Week", "Week Date", "Name", "Activity", "Minutes", "Distance", "Notes"]

submit_log = form.form_submit_button("Log Minutes", on_click=check_input(log_name, log_minutes))
if submit_log:
    week_date = log_date - timedelta(days=log_date.weekday() % 7)
    week = log_date.isocalendar()[1]
    if len(log_name) > 0 and log_minutes > 0:
        for name in ["Tara", "Lauren"]:
            recorded_weeks = new_data[new_data["Name"] == name]["Week Date"].unique()
            if str(week_date) not in recorded_weeks:
                dummy_vals = [log_date.strftime("%Y-%m-%d"), str(week), week_date.strftime("%Y-%m-%d"), name, "", str(0), str(0), "placeholder for aggregation"]
                write_new_rows(dummy_vals, cols, new_data, spreadsheet_id, "new_data!A:H")
        for name in log_name:
            form_vals = [log_date.strftime("%Y-%m-%d"), str(week), week_date.strftime("%Y-%m-%d"), name, log_activity.lower(), str(log_minutes), log_distance, log_notes]
            form_rows = pd.DataFrame([form_vals], columns=cols)
            new_data = pd.concat([new_data, form_rows])
            new_data = new_data.drop_duplicates()
            write_new_rows(form_vals, cols, new_data, spreadsheet_id, "new_data!A:H")

# # Uncomment below to read from tracker data and write to data sheet
# from funcs import get_and_melt_raw_data
# melted = get_and_melt_raw_data(spreadsheet_id, "tracker!A:E")
# request = write_to_sheet(melted, spreadsheet_id, "data!A:G")
# response = request.execute()

# Data
rows = get_data(spreadsheet_id, range_name)
df = pd.DataFrame(rows[1:], columns=rows[0])
row_updates = get_data(spreadsheet_id, "new_data!A:H")
if len(row_updates) > 0:
    new_rows = pd.DataFrame(row_updates[1:], columns=row_updates[0])
    df = pd.concat([df, new_rows])
    df = df.drop_duplicates().sort_values(by="Day").reset_index(drop=True)

df["Day"] = pd.to_datetime(df["Day"])
df["Week Date"] = pd.to_datetime(df["Week Date"])
df["Minutes"] = df["Minutes"].astype(int)
df["Distance"] = df["Distance"].astype(float)
df["Week"] = df["Week"].astype(int)
df["Week Date"].unique()

lauren_df = df[df["Name"] == "Lauren"]
lauren = lauren_df.groupby(["Week", "Week Date"]).sum().reset_index()
lauren_wo = lauren_df[lauren_df["Minutes"] > 0].groupby(["Week", "Week Date"])["Minutes"].size().rename("Workouts").reset_index()
lauren = lauren.merge(lauren_wo, on=["Week", "Week Date"])

tara_df = df[df["Name"] == "Tara"]
tara = tara_df.groupby(["Week", "Week Date"]).sum().reset_index()
tara_wo = tara_df[tara_df["Minutes"] > 0].groupby(["Week", "Week Date"])["Minutes"].size().rename("Workouts").reset_index()
tara = tara.merge(tara_wo, on=["Week", "Week Date"])

combined = lauren.merge(tara, on=["Week", "Week Date"], suffixes=["_l", "_t"]).rename(columns={"Minutes_l": "Minutes (Lauren)", "Minutes_t": "Minutes (Tara)", "Workouts_l": "Workouts (Lauren)", "Workouts_t": "Workouts (Tara)", "Distance_l": "Distance (Lauren)", "Distance_t": "Distance (Tara)"})
combined["Winner"] = combined.apply(lambda row: "None" if row["Minutes (Lauren)"] < 100 and row["Minutes (Tara)"] < 100 and row["Workouts (Lauren)"] < 3 and row["Workouts (Tara)"] < 3 else ("Lauren" if (row["Minutes (Lauren)"] * row["Workouts (Lauren)"]) > (row["Minutes (Tara)"] * row["Workouts (Tara)"]) else ("Tara" if (row["Minutes (Lauren)"] * row["Workouts (Lauren)"]) < (row["Minutes (Tara)"] * row["Workouts (Tara)"]) else "Tie")), axis=1)
combined = combined.sort_values(by="Week Date").reset_index(drop=True)