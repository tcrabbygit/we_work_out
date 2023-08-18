import pandas as pd
import streamlit as st
from datetime import timedelta, datetime, date
import plotly.graph_objects as go
import plotly.express as px
from funcs import get_data, historic_and_new_data, write_to_sheet, check_input, add_whitespace, write_new_rows, prep_by_name, weekly_minutes_workouts_points, weekly_aggs

# Settings
st.set_page_config(page_title="Fitness Tracker!", page_icon=None, layout="wide", initial_sidebar_state="auto", menu_items=None)

# Sidebar
st.sidebar.markdown("### Log Workout :muscle:")
form = st.sidebar.form("log_time")
log_name = form.multiselect("Name", ["Lauren", "Tara"], default=["Lauren", "Tara"])
log_date = form.date_input("Date")
log_activity = form.selectbox("Activity", ["Bike", "Climb", "Eliptical", "Hike", "Stretching", "Yoga", "Walk", "Weights", "Other"])
log_minutes = form.number_input("Minutes", 0, 100, 30, 5)
log_distance = form.number_input("Distance (in miles)", step=0.1)
log_notes = form.text_area("Workout Notes", value="")

spreadsheet_id = "1BAWUiSI8jV0hSmaD9b_68CaRgSca9J_Odb1TpWRYuZU"
new_data = get_data(spreadsheet_id, "new_data!A:H")
new_data = pd.DataFrame(new_data[1:], columns=new_data[0])
cols = ["Day", "Week", "Week Date", "Name", "Activity", "Minutes", "Distance", "Notes"]

submit_log = form.form_submit_button("Log Workout", on_click=check_input(log_name, log_minutes))
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
range_name = "data!A:G"
df = historic_and_new_data(range_name, spreadsheet_id)

lauren = prep_by_name(df, "Lauren")
tara = prep_by_name(df, "Tara")

df["Day"] = pd.to_datetime(df["Day"])
df["Week Date"] = pd.to_datetime(df["Week Date"])

combined = lauren.merge(tara, on=["Week", "Week Date"], suffixes=["_l", "_t"]).rename(columns={"Minutes_l": "Minutes (Lauren)", "Minutes_t": "Minutes (Tara)", "Workouts_l": "Workouts (Lauren)", "Workouts_t": "Workouts (Tara)", "Distance_l": "Distance (Lauren)", "Distance_t": "Distance (Tara)", "Points_l": "Points (Lauren)", "Points_t": "Points (Tara)"})
combined["Winner"] = combined.apply(lambda row: "None :(" if (row["Minutes (Lauren)"] < 90 and row["Minutes (Tara)"] < 90) or (row["Workouts (Lauren)"] < 3 and row["Workouts (Tara)"] < 3) else ("Lauren" if (row["Minutes (Lauren)"] * row["Workouts (Lauren)"]) > (row["Minutes (Tara)"] * row["Workouts (Tara)"]) else ("Tara" if (row["Minutes (Lauren)"] * row["Workouts (Lauren)"]) < (row["Minutes (Tara)"] * row["Workouts (Tara)"]) else "Tie")), axis=1)
combined = combined.sort_values(by="Week Date").reset_index(drop=True)

# Weekly metrics
now = datetime.combine(date.today(), datetime.min.time())
this_week = now - timedelta(days=now.weekday())
last_week = this_week - timedelta(days=7)
winner_last_week = combined.loc[combined["Week Date"] == last_week, "Winner"].values[0]

min_tw_l, wo_tw_l, pts_tw_l = weekly_minutes_workouts_points(lauren, this_week)
min_lw_l, wo_lw_l, pts_lw_l = weekly_minutes_workouts_points(lauren, last_week)
avg_min_l, med_min_l, avg_wo_l, med_wo_l, avg_pts_l = weekly_aggs(lauren)

min_tw_t, wo_tw_t, pts_tw_t = weekly_minutes_workouts_points(tara, this_week)
min_lw_t, wo_lw_t, pts_lw_t = weekly_minutes_workouts_points(tara, last_week)
avg_min_t, med_min_t, avg_wo_t, med_wo_t, avg_pts_t = weekly_aggs(tara)

# Body
"# Exercise Competition! :woman-running: :woman-biking: :woman-lifting-weights: :woman_climbing: :woman_in_lotus_position: :muscle:"
"Here's how it works. You need at least 90 minutes and 3 workouts each week (Monday - Sunday) to be considered for a win.  Points are calculated as `Minutes` * `Workouts`.  The winner is the person with the highest points.  Ties are possible!  If no one gets over the required thresholds, there are two losers."
st.markdown(
    "Tracker sheet located [here](https://docs.google.com/spreadsheets/d/1BAWUiSI8jV0hSmaD9b_68CaRgSca9J_Odb1TpWRYuZU/edit?usp=sharing)")
add_whitespace(2)

col1, col2 = st.columns(2)
col1.markdown(f"##### :trophy: Last Week's Winner: {winner_last_week} :trophy:")
col1.markdown(f"###### Points Breakdown {last_week.date()}")

pts_lw = pd.concat([lauren[lauren["Week Date"] == last_week], tara[tara["Week Date"] == last_week]], ignore_index=True)
pts_lw = pts_lw[["Minutes", "Workouts", "Points"]]
pts_lw = pd.concat([pd.DataFrame(["Lauren", "Tara"], columns=["Name"]), pts_lw], axis=1)
col1.dataframe(pts_lw)

col2.markdown("##### :trophy: Weekly Winners :trophy:")
fig = px.pie(combined["Winner"].value_counts().reset_index(),
             values="count",
             names="Winner",
             color="Winner",
             color_discrete_map={"None :(": "#EDF2F4",
                                 "Tie": "#8D99AE",
                                 "Lauren": "#D80032",
                                 "Tara": "#2B2D42"})
fig.update_layout(height=300,
                  width=400,
                  margin=dict(l=0, r=80, t=0, b=80, pad=0)
                  )
col2.plotly_chart(fig, use_container_widte=True)

"## Stats"
"### Lauren"
col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("Minutes This Week", min_tw_l, min_tw_l - min_lw_l)
col2.metric("Avg Minutes per Week", avg_min_l)
# col2.metric("Median Minutes per Week", med_min_l)
col3.metric("Workouts This Week", wo_tw_l, wo_tw_l - wo_lw_l)
col4.metric("Avg Workouts per Week", avg_wo_l)
# col4.metric("Median Workouts per Week", med_wo_l)
col5.metric("Points This Week", pts_tw_l, pts_tw_l - pts_lw_l)
col6.metric("Avg Points per Week", avg_pts_l)
add_whitespace(3)

"### Tara"
col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("Minutes This Week (Tara)", min_tw_t, min_tw_t - min_lw_t)
col2.metric("Avg Minutes per Week", avg_min_t)
# col2.metric("Median Minutes per Week", med_min_t)
col3.metric("Workouts This Week", wo_tw_t, wo_tw_t - wo_lw_t)
col4.metric("Avg Workouts per Week", avg_wo_t)
# col4.metric("Median Workouts per Week", med_wo_t)
col5.metric("Points This Week", pts_tw_t, pts_tw_t - pts_lw_t)
col6.metric("Avg Points per Week", avg_pts_t)
add_whitespace(3)

"## Charts & Data"
"### Points"
fig = go.Figure()
fig.add_trace(go.Bar(x=combined["Week Date"], y=combined["Points (Lauren)"], name="Lauren", marker_color="#d90429"))
fig.add_trace(go.Bar(x=combined["Week Date"], y=combined["Points (Tara)"], name="Tara", marker_color="#2b2d42"))
fig.update_layout(plot_bgcolor="#FCFDFD", xaxis_title="Week", yaxis_title="Count", margin=dict(l=0, r=0, t=0, b=0, pad=0), height=400, legend_yanchor="middle", legend_y=0.5)
fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="#D7DBE2")
st.plotly_chart(fig, use_container_width=True)
add_whitespace(2)

"### Minutes"
fig = go.Figure()
fig.add_trace(go.Scatter(x=combined["Week Date"], y=combined["Minutes (Lauren)"], mode="lines+markers", name="Lauren", line=dict(color="#d90429")))
fig.add_trace(go.Scatter(x=combined["Week Date"], y=combined["Minutes (Tara)"], mode="lines+markers", name="Tara", line=dict(color="#2b2d42")))
fig.update_layout(plot_bgcolor="#FCFDFD", xaxis_title="Week", yaxis_title="Minutes", margin=dict(l=0, r=0, t=0, b=0, pad=0), height=400, legend_yanchor="middle", legend_y=0.5)
fig.update_xaxes(showline=True, linewidth=2, linecolor='#8D99AE')
fig.update_yaxes(showline=True, linewidth=2, linecolor='#8D99AE', showgrid=True, gridwidth=1, gridcolor="#D7DBE2")
st.plotly_chart(fig, use_container_width=True)
add_whitespace(2)

"### Workouts"
fig = go.Figure()
fig.add_trace(go.Bar(x=combined["Week Date"], y=combined["Workouts (Lauren)"], name="Lauren", marker_color="#d90429"))
fig.add_trace(go.Bar(x=combined["Week Date"], y=combined["Workouts (Tara)"], name="Tara", marker_color="#2b2d42"))
fig.update_layout(plot_bgcolor="#FCFDFD", xaxis_title="Week", yaxis_title="Count", margin=dict(l=0, r=0, t=0, b=0, pad=0), height=400, legend_yanchor="middle", legend_y=0.5)
fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="#D7DBE2")
st.plotly_chart(fig, use_container_width=True)
add_whitespace(2)

"### Miles"
mi = combined[combined["Week Date"] >= "2022-05-30"]
fig = go.Figure()
fig.add_trace(go.Scatter(x=mi["Week Date"], y=mi["Distance (Lauren)"], mode="lines+markers", name="Lauren", line=dict(color="#d90429")))
fig.add_trace(go.Scatter(x=mi["Week Date"], y=mi["Distance (Tara)"], mode="lines+markers", name="Tara", line=dict(color="#2b2d42")))
fig.update_layout(plot_bgcolor="#FCFDFD", xaxis_title="Week", yaxis_title="Miles", margin=dict(l=0, r=0, t=0, b=0, pad=0), height=400, legend_yanchor="middle", legend_y=0.5)
fig.update_xaxes(showline=True, linewidth=2, linecolor='#8D99AE')
fig.update_yaxes(showline=True, linewidth=2, linecolor='#8D99AE', showgrid=True, gridwidth=1, gridcolor="#D7DBE2")
st.plotly_chart(fig, use_container_width=True)
add_whitespace(3)

"### Log"
combined = combined.sort_values(by="Week Date", ascending=False)
st.dataframe(combined.style.format({"Week Date": lambda t: t.strftime("%y-%m-%d")}), width=1500)
add_whitespace(2)

"### Raw"
df = df.sort_values(by=["Week Date", "Day"], ascending=[False, False])
st.dataframe(df.style.format({"Week Date": lambda t: t.strftime("%y-%m-%d"), "Day": lambda t: t.strftime("%y-%m-%d")}), width=1500)
add_whitespace(2)

st.markdown("Tracker sheet located [here](https://docs.google.com/spreadsheets/d/1BAWUiSI8jV0hSmaD9b_68CaRgSca9J_Odb1TpWRYuZU/edit?usp=sharing)")
