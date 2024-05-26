from google.oauth2 import service_account
from googleapiclient import discovery
from datetime import timedelta
import streamlit as st
import pandas as pd

# SA Creds
creds = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
    ],
)
service = discovery.build('sheets', 'v4', credentials=creds)


def get_data(spreadsheet_id, range_name):
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=range_name).execute()
    rows = result.get('values', {})
    return rows


def get_sheets(spreadsheet_id):
    sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheets = sheet_metadata.get('sheets', '')
    titles = []
    ids = []
    for i, v in enumerate(sheets):
        titles.append(sheets[i].get("properties", {}).get("title", "Sheet1"))
        ids.append(sheets[i].get("properties", {}).get("sheetId", 0))
    return sheets, titles, ids


def historic_and_new_data(range_name, spreadsheet_id):
    rows = get_data(spreadsheet_id, range_name)
    df = pd.DataFrame(rows[1:], columns=rows[0])

    row_updates = get_data(spreadsheet_id, "new_data!A:H")
    if len(row_updates) > 0:
        new_rows = pd.DataFrame(row_updates[1:], columns=row_updates[0])
        df = pd.concat([df, new_rows])
        df = df.drop_duplicates().sort_values(by="Day").reset_index(drop=True)

    df["Minutes"] = df["Minutes"].astype(int)
    df["Distance"] = df["Distance"].astype(float)
    df["Week"] = df["Week"].astype(int)

    return df


def write_to_sheet(df, spreadsheet_id, range_):
    value_input_option = "USER_ENTERED"
    data = [df.columns.values.tolist()]
    data.extend(df.values.tolist())
    value_range_body = {"values": data}
    request = service.spreadsheets().values().update(spreadsheetId=spreadsheet_id, range=range_, valueInputOption=value_input_option, body=value_range_body)
    return request


def prep_by_name(df, name):
    named_df = df[df["Name"] == name]
    named_grp = named_df.groupby(["Week", "Week Date"])[["Minutes", "Distance"]].sum().reset_index()
    named_grp_wo = named_df[named_df["Minutes"] > 0].groupby(["Week", "Week Date"])["Minutes"].size().rename("Workouts").reset_index()
    named_grp = named_grp.merge(named_grp_wo, on=["Week", "Week Date"], how="left").fillna(0)
    named_grp["Workouts"] = named_grp["Workouts"].astype(int)
    named_grp["Points"] = (named_grp["Minutes"] * named_grp["Workouts"]).astype(int)
    named_grp["Points"] = named_grp["Points"].fillna(0)
    named_grp["Week Date"] = pd.to_datetime(named_grp["Week Date"])
    return named_grp


def week_dates(start_date, end_date):
    weeks = []
    tally_week = start_date
    while tally_week <= pd.to_datetime(end_date):
        weeks.append(tally_week)
        tally_week = tally_week + timedelta(days=7)
    weeks = pd.DataFrame(weeks, columns=["Week Date"])
    weeks["Week"] = weeks["Week Date"].apply(lambda x: x.isocalendar().week)
    weeks = weeks[["Week", "Week Date"]]
    return weeks


def combine_indiviual_dfs(lauren, tara, weeks):
    combined = weeks.merge(lauren, on=["Week", "Week Date"], how="left")
    combined = combined.merge(tara, on=["Week", "Week Date"], how="left", suffixes=["_l", "_t"]).rename(columns={"Minutes_l": "Minutes (Lauren)", "Minutes_t": "Minutes (Tara)", "Workouts_l": "Workouts (Lauren)", "Workouts_t": "Workouts (Tara)", "Distance_l": "Distance (Lauren)", "Distance_t": "Distance (Tara)", "Points_l": "Points (Lauren)", "Points_t": "Points (Tara)"})
    
    nullable = [col for col in combined.columns.tolist() if "(" in col]
    for col in nullable:
        combined[col] = combined[col].fillna(0)
    combined["Winner"] = combined.apply(lambda row: "None :(" if (row["Minutes (Lauren)"] < 90 and row["Minutes (Tara)"] < 90) or (row["Workouts (Lauren)"] < 3 and row["Workouts (Tara)"] < 3) else ("Lauren" if (row["Minutes (Lauren)"] * row["Workouts (Lauren)"]) > (row["Minutes (Tara)"] * row["Workouts (Tara)"]) else ("Tara" if (row["Minutes (Lauren)"] * row["Workouts (Lauren)"]) < (row["Minutes (Tara)"] * row["Workouts (Tara)"]) else "Tie")), axis=1)
    combined = combined.sort_values(by="Week Date").reset_index(drop=True)
    return combined


def weekly_minutes_workouts_points(named_df, week):
    # Minutes
    try:
        minutes = int(named_df[named_df["Week Date"] == week]["Minutes"].sum())
    except TypeError:
        minutes = 0
    
    # Workouts
    try:
        workouts = int(named_df[named_df["Week Date"] == week]["Workouts"].sum())
    except TypeError:
        workouts = 0

    # Points
    try:
        points = int(named_df[named_df["Week Date"] == week]["Points"].sum())
    except TypeError:
        points = 0
    
    return minutes, workouts, points


def weekly_aggs(named_df):
    avg_min = round(named_df["Minutes"].mean(), 1)
    med_min = named_df["Minutes"].median()
    avg_wo = round(named_df["Workouts"].mean(), 1)
    med_wo = named_df["Workouts"].median()
    avg_pts = round(named_df["Points"].mean(), 1)

    return avg_min, med_min, avg_wo, med_wo, avg_pts


# @st.experimental_memo
# @st.cache(allow_output_mutation=True)
def get_and_melt_raw_data(spreadsheet_id, range_name):
    rows = get_data(spreadsheet_id, range_name)
    raw = pd.DataFrame(rows[1:], columns=rows[0])
    raw["Day"] = pd.to_datetime(raw["Day"])
    raw = raw.sort_values("Day").drop_duplicates()
    melted_l = raw[["Day", "Lauren", "l_activity"]].rename(columns={"l_activity": "Activity"}).melt(id_vars=["Day", "Activity"], value_vars=["Lauren"], var_name="Name", value_name="Minutes")
    melted_t = raw[["Day", "Tara", "t_activity"]].rename(columns={"t_activity": "Activity"}).melt(id_vars=["Day", "Activity"], value_vars=["Tara"], var_name="Name", value_name="Minutes")
    melted = pd.concat([melted_l, melted_t])
    melted["Day"] = pd.to_datetime(melted["Day"])
    melted["Week"] = melted["Day"].apply(lambda x: x.isocalendar()[1])
    melted["Week Date"] = melted["Day"].apply(lambda x: x - timedelta(days=x.weekday() % 7))
    melted["Day"] = melted["Day"].astype(str)
    melted["Week Date"] = melted["Week Date"].astype(str)
    melted = melted[["Day", "Week", "Week Date", "Name", "Activity", "Minutes"]]
    return melted


def check_input(log_name, log_minutes):
    if len(log_name) < 1:
        st.sidebar.error("Name field is required")
    elif log_minutes < 1:
        st.sidebar.error("Minutes must be more than 0")


def write_new_rows(values, cols, df, spreadsheet_id, range):
    rows = pd.DataFrame([values], columns=cols)
    new_data = pd.concat([df, rows])
    new_data = new_data.drop_duplicates()
    request = write_to_sheet(new_data, spreadsheet_id, range)
    response = request.execute()
    return response


def add_whitespace(line_count):
    for i in range(0, line_count):
        st.write("")
