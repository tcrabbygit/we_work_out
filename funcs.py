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


def write_to_sheet(df, spreadsheet_id, range_):
    value_input_option = "USER_ENTERED"
    data = [df.columns.values.tolist()]
    data.extend(df.values.tolist())
    value_range_body = {"values": data}
    request = service.spreadsheets().values().update(spreadsheetId=spreadsheet_id, range=range_, valueInputOption=value_input_option, body=value_range_body)
    return request


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
