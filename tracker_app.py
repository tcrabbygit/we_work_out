import pandas as pd
import streamlit as st
from datetime import timedelta
import plotly.graph_objects as go
import plotly.express as px
from funcs import get_data, write_to_sheet, check_input, add_whitespace

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
log_notes = form.text_area("Workout Notes", value="")

new_data = get_data(spreadsheet_id, "new_data!A:G")
new_data = pd.DataFrame(new_data[1:], columns=new_data[0])
cols = ["Day", "Week", "Week Date", "Name", "Activity", "Minutes", "Notes"]

submit_log = form.form_submit_button("Log Minutes", on_click=check_input(log_name, log_minutes))
if submit_log:
    week_date = log_date - timedelta(days=log_date.weekday() % 7)
    week = log_date.isocalendar()[1]
    if len(log_name) > 0 and log_minutes > 0:
        for name in ["Tara", "Lauren"]:
            recorded_weeks = new_data[new_data["Name"] == name]["Week Date"].unique()
            if str(week_date) not in recorded_weeks:
                dummy_vals = [log_date.strftime("%Y-%m-%d"), str(week), week_date.strftime("%Y-%m-%d"), name, "", str(0), "placeholder for aggregation"]
                dummy_rows = pd.DataFrame([dummy_vals], columns=cols)
                new_data = pd.concat([new_data, dummy_rows])
                new_data = new_data.drop_duplicates()
                request = write_to_sheet(new_data, spreadsheet_id, "new_data!A:G")
                response = request.execute()
            else:
                pass
        for name in log_name:
            form_vals = [log_date.strftime("%Y-%m-%d"), str(week), week_date.strftime("%Y-%m-%d"), name, log_activity.lower(), str(log_minutes), log_notes]
            form_rows = pd.DataFrame([form_vals], columns=cols)
            new_data = pd.concat([new_data, form_rows])
            new_data = new_data.drop_duplicates()
            request = write_to_sheet(new_data, spreadsheet_id, "new_data!A:G")
            response = request.execute()

# # Uncomment below to read from tracker data and write to data sheet
# from funcs import get_and_melt_raw_data
# melted = get_and_melt_raw_data(spreadsheet_id, "tracker!A:E")
# request = write_to_sheet(melted, spreadsheet_id, "data!A:G")
# response = request.execute()

# Data
rows = get_data(spreadsheet_id, range_name)
df = pd.DataFrame(rows[1:], columns=rows[0])
row_updates = get_data(spreadsheet_id, "new_data!A:G")
if len(row_updates) > 0:
    new_rows = pd.DataFrame(row_updates[1:], columns=row_updates[0])
    df = pd.concat([df, new_rows])
    df = df.drop_duplicates().sort_values(by="Day").reset_index(drop=True)

df["Day"] = pd.to_datetime(df["Day"])
df["Week Date"] = pd.to_datetime(df["Week Date"])
df["Minutes"] = df["Minutes"].astype(int)
df["Week"] = df["Week"].astype(int)

lauren = df[df["Name"] == "Lauren"]
lauren = lauren.groupby(["Week", "Week Date"])["Minutes"].sum().reset_index()
tara = df[df["Name"] == "Tara"]
tara = tara.groupby(["Week", "Week Date"])["Minutes"].sum().reset_index()

combined = lauren.merge(tara, on=["Week", "Week Date"], suffixes=["_l", "_t"]).rename(columns={"Minutes_l": "Lauren", "Minutes_t": "Tara"})
combined["Winner"] = combined.apply(lambda row: "None" if row["Lauren"] < 100 and row["Tara"] < 100 else ("Lauren" if row["Lauren"] > row["Tara"] else ("Tara" if row["Lauren"] < row["Tara"] else "Tie")), axis=1)
combined = combined.sort_values(by="Week Date").reset_index(drop=True)

# Body
st.markdown("# Exercise Competition! :woman-running: :woman-biking: :woman-lifting-weights: :woman_climbing: :woman_in_lotus_position: :muscle:")
st.markdown("Here's how it works. You need at least 100 minutes each week to be considered for a win.  Winner is the person with the most minutes over 100.  Ties are possible!  If no one gets over 100 minutes, there are two losers.")
add_whitespace(2)
this_week = combined["Week Date"].max()
last_week = this_week - timedelta(days=7)
winner_last_week = combined.loc[combined["Week Date"] == last_week, "Winner"].values[0]
st.markdown(f"##### :trophy: Last Week's Winner: {winner_last_week} :trophy:")
add_whitespace(2)

st.markdown("## Stats")
min_tw_l = int(lauren[lauren["Week Date"] == this_week]["Minutes"].sum())
min_lw_l = int(lauren[lauren["Week Date"] == last_week]["Minutes"].sum())
min_tw_t = int(tara[tara["Week Date"] == this_week]["Minutes"].sum())
min_lw_t = int(tara[tara["Week Date"] == last_week]["Minutes"].sum())
avg_min_l = round(combined["Lauren"].mean(), 1)
avg_min_t = round(combined["Tara"].mean(), 1)

col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
col1.metric("Minutes This Week (Lauren)", min_tw_l, min_tw_l - min_lw_l)
col1.subheader("")
col1.subheader("")
col1.metric("Minutes This Week (Tara)", min_tw_t, min_tw_t - min_lw_t)

col2.metric("Average Minutes (Lauren)", avg_min_l)
col2.subheader("")
col2.subheader("")
col2.metric("Average Minutes (Tara)", avg_min_t)

col3.metric("Total Minutes (Lauren)", int(lauren['Minutes'].sum()))
col3.subheader("")
col3.subheader("")
col3.metric("Total Minutes (Tara)", int(tara['Minutes'].sum()))

fig = px.pie(combined["Winner"].value_counts().reset_index(),
             values="Winner",
             names="index",
             color="index",
             color_discrete_map={"None": "#EDF2F4",
                                 "Tie": "#8D99AE",
                                 "Lauren": "#D80032",
                                 "Tara": "#2B2D42"})
fig.update_layout(height=300,
                  width=400,
                  margin=dict(l=0, r=80, t=0, b=80, pad=0)
                  )
col4.write("Total Wins")
col4.plotly_chart(fig, use_container_widte=True)

st.markdown("## Data")
fig = go.Figure()
fig.add_trace(go.Scatter(x=combined["Week Date"], y=combined["Lauren"], mode="lines+markers", name="Lauren", line=dict(color="#d90429")))
fig.add_trace(go.Scatter(x=combined["Week Date"], y=combined["Tara"], mode="lines+markers", name="Tara", line=dict(color="#2b2d42")))
fig.update_layout(plot_bgcolor="#FCFDFD", xaxis_title="Week", yaxis_title="Minutes", margin=dict(l=0, r=0, t=0, b=0, pad=0), height=500)
fig.update_xaxes(showline=True, linewidth=2, linecolor='#8D99AE')
fig.update_yaxes(showline=True, linewidth=2, linecolor='#8D99AE', showgrid=True, gridwidth=1, gridcolor="#D7DBE2")

col1, col2 = st.columns([2, 1])
col1.markdown("### Minutes by Week")
col1.plotly_chart(fig, use_container_width=True)
col2.markdown("### Raw")
col2.dataframe(combined, height=600)
st.markdown("Tracker sheet located [here](https://docs.google.com/spreadsheets/d/1BAWUiSI8jV0hSmaD9b_68CaRgSca9J_Odb1TpWRYuZU/edit?usp=sharing)")
