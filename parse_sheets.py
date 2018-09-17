#!/home/ec2-user/daily-tracker-v1/bin/python3
import configparser
import os
import re

# Use non-tkinter backend b/c EC2 doesn't support tkinter
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
import numpy as np
from google.oauth2 import service_account
from googleapiclient.discovery import build

import date_utils
import email_utils

config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.properties'))
print("CONFIG_PATH: ", os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.properties'))
config = dict(config.items('Setup'))

SCOPES = [config['scope1'], config['scope2']]
SERVICE_ACCOUNT_FILE = config['service_account_file']
SPREADSHEET_ID = config['spreadsheet_id']
TEMPLATE_ID = config['template_id']

CELL_RANGES = {
    config['name_1']: config['cell_range_1'],
    config['name_2']: config['cell_range_2']
}
TO_EMAILS = {
    config['name_1']: config['to_email_1'],
    config['name_2']: config['to_email_2'],
}

# Using service account to bypass user Oauth2 flow
credentials = service_account.Credentials.from_service_account_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), SERVICE_ACCOUNT_FILE), scopes=SCOPES)
service = build('sheets', 'v4', credentials=credentials)

# Given daily breakdown data, returns a dict containing data for top 2 time-spent categories and sleep.
def extract_metrics(person_name, cell_range):
    metrics = {
        "time_sleep_hr": -1,
        "time_sleep_min": -1,
        "top_1_category": "",
        "top_1_hr": -1,
        "top_1_min": -1,

        "top_2_category": "",
        "top_2_hr": -1,
        "top_2_min": -1,

        "person_name": person_name
    }
    sheet_values = read_sheet_values(person_name, cell_range)
    categories, data = clean_data(sheet_values[0], sheet_values[1])

    # Zip up each category with the time in minutes for each one.
    cat_data_list = list(zip(categories, data))
    print(cat_data_list)

    # Remove sleep first and populate metric.
    sleep_item_list = [item for item in cat_data_list if item[0].lower() == "sleep"]
    if len(sleep_item_list) == 0:
        raise Exception("No sleep item!")
    sleep_item = sleep_item_list[0]
    metrics["time_sleep_hr"] = int(sleep_item[1] / 60)
    metrics["time_sleep_min"] = sleep_item[1] % 60
    cat_data_list = [item for item in cat_data_list if item[0].lower() != "sleep"]

    # Sort by the time spent
    print("CATE_DATA_LIST: ", cat_data_list)
    sorted_data_list = sorted(cat_data_list, key=lambda tup: tup[1], reverse=True)
    print("SORTED: ", sorted_data_list)

    # Get top 2 non-sleep categories.
    if len(sorted_data_list) >= 2:
        for i in range(0, 2):
            metric_item = sorted_data_list[i]
            category_key = "top_{}_category".format(i + 1)
            hr_key = "top_{}_hr".format(i + 1)
            min_key = "top_{}_min".format(i + 1)

            metrics[category_key] = metric_item[0]
            metrics[hr_key] = int(metric_item[1] / 60)
            metrics[min_key] = metric_item[1] % 60

            cat_data_list = [item for item in cat_data_list if item[0].lower() != "sleep"]
    else:
        raise Exception("<2 work-related categories for: ", person_name)

    print("FINAL_METRICS: ", metrics)
    return metrics, categories, data

# Given date formatted as a string, generate the range.
# Ref: https://stackoverflow.com/questions/38245714/get-list-of-sheets-and-latest-sheet-in-google-spreadsheet-api-v4-in-python
def create_range_with_date(date_str):

    # First, validate that sheet exists for this date.
    print("DATE_STR: ", date_str)
    try:
        sheet_metadata = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        print(sheet_metadata.get('sheets'))
        sheets_data = sheet_metadata.get('sheets')

        # Find a sheet with the same name as the date string
        matching_sheets = [sheet_data for sheet_data in sheets_data if sheet_data['properties']['title'] == date_str]
        if len(matching_sheets) == 0:
            # Sometimes, the first digit of a sheet is a 0.
            date_str = date_str[1:]
            print("NEW_DATE_STR: ", date_str)
            matching_sheets = [sheet_data for sheet_data in sheets_data if
                               sheet_data['properties']['title'] == date_str]
            if len(matching_sheets) == 0:
                raise Exception("No sheets with name: ", date_str)
        print("DATA: ", matching_sheets[0]['properties'])

        # Populate ranges
        PERSON_RANGES = {}
        for name in CELL_RANGES:
            PERSON_RANGES[name] = date_str + "!" + CELL_RANGES[name]
        return PERSON_RANGES

    except Exception as e:
        print(e)
        return {}

def clean_data(categories, data):

    print("CLEANING_DATA!!!")

    print("RAW_CATEGORIES: ", categories)
    print("RAW_DATA: ", data)

    # Remove headers from each list of data
    cleaned_categories = np.array(categories[1:])
    cleaned_data = np.array(data[1:])

    print("CLEANED_CATEGORIES: ", cleaned_categories)
    print("CLEANED_DATA: ", cleaned_data)

    data_in_min = [convert_time_to_min_float(raw_time_interval) for raw_time_interval in cleaned_data]
    print("DATA_IN_MIN: ", data_in_min)

    # Remove all categories with values of 0
    indices_to_remove = []
    for i in range(0, len(data_in_min)):
        if data_in_min[i] == 0:
            indices_to_remove.append(i)
    cleaned_categories = np.delete(cleaned_categories, indices_to_remove)
    cleaned_data_in_min = np.delete(data_in_min, indices_to_remove)

    print("FINAL_CLEANED: ", cleaned_categories, cleaned_data)
    return cleaned_categories, cleaned_data_in_min

def read_sheet_values(person_name, cell_range):
    # Get range of cells from specific sheet from spreadsheet
    result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID,
                                                 range=cell_range,
                                                 majorDimension="COLUMNS").execute()
    values = result.get('values', [])

    if not values:
        print('No data found.')
        return None
    else:
        print('Data found!')
        print(values)
        return values


def create_chart(person_name, categories, data, graph_name):

    print("CREATING_GRAPH!!!")
    print("RAW_CATEGORIES: ", categories)
    print("RAW_DATA: ", data)

    # Remove headers from each list of data
    cleaned_categories = np.array(categories[1:])
    cleaned_data = np.array(data[1:])

    print("CLEANED_CATEGORIES: ", cleaned_categories, " of len: ", len(cleaned_categories))
    print("CLEANED_DATA: ", cleaned_data, " of len: ", len(cleaned_data))

    # data_in_min = [convert_time_to_min_float(raw_time_interval) for raw_time_interval in cleaned_data]
    data_in_min = cleaned_data
    # print("DATA_IN_MIN: ", data_in_min)

    # Remove all categories with values of 0
    indices_to_remove = []
    for i in range(0, len(data_in_min)):
        if data_in_min[i] == 0:
            indices_to_remove.append(i)
    cleaned_categories = np.delete(cleaned_categories, indices_to_remove)
    cleaned_data_in_min = np.delete(data_in_min, indices_to_remove)

    cleaned_categories = [x for _, x in sorted(zip(cleaned_data_in_min, cleaned_categories), key=lambda tup: tup[0], reverse=True)]
    cleaned_data_in_min = sorted(cleaned_data_in_min, reverse=True)

    # Calculate some total time metrics
    total_time_logged = sum(cleaned_data_in_min)

    # Begin graphing
    fig, ax1 = plt.subplots(figsize=(8, 10))
    rects = ax1.bar(cleaned_categories, cleaned_data_in_min)
    ax1.set_title("Daily Breakdown: " + person_name.upper())
    ax1.set_xlabel('Categories')
    ax1.set_ylabel('Minutes Spent')
    ax1.set_ylim(0, max(cleaned_data_in_min) * 1.1)

    raw_label_data = [cleaned_data_in_min[i] for i in range(0, len(cleaned_data_in_min))]
    for rect, raw_label in zip(rects, raw_label_data):
        print(rect, raw_label)
        print("LABELING")

        # Calculate time %age
        category_hrs = int(raw_label / 60)
        category_min = raw_label % 60
        category_percentage = "{0:.2f}".format(raw_label / total_time_logged * 100)
        final_label = "{} hr, \n{} min \n({}%)".format(category_hrs, category_min, category_percentage)

        x_val = rect.get_x() + rect.get_width() / 2
        y_val = rect.get_height()

        space_above = 1 # How much above the bar
        va = 'bottom'   # Vertical alignment
        ha = 'center'

        # ax1.annotate(raw_label, (x_val, y_val), (0, space_above), textcoords="offset points", ha='center', va=va)
        ax1.text(x_val, y_val + space_above, final_label, ha=ha, va=va, rotation='horizontal')

    # plt.title("Daily Breakdown: " + person_name.upper())
    plt.annotate('*Note: %ages consider only non-sleep categories.', (0, 0), (0, -40), xycoords='axes fraction', textcoords='offset points', va='top')
    # plt.show()

    ### START PIE CHART LOGIC
    # Sort wedges from smallest to largest
    # cleaned_categories = [x for _, x in sorted(zip(cleaned_data_in_min, cleaned_categories), key=lambda tup: tup[0])]
    # cleaned_data_in_min = sorted(cleaned_data_in_min)

    # fig1, ax1 = plt.subplots(1, 1, figsize=(8, 8))
    # fig1, ax1 = plt.subplots(1, 1, figsize=(10.05, 8))
    # # autopct = '%1.1f%%',
    # wedges, texts = ax1.pie(cleaned_data_in_min, labels=None, autopct=None,
    #                                      startangle=90, labeldistance=0.75, pctdistance=0.5)
    # # Add center circle to convert to donut chart
    # # Ref: https://medium.com/@krishnakummar/donut-chart-with-python-matplotlib-d411033c960b
    # center_circle = plt.Circle(xy=(0, 0), radius=0.6, color='white', fc='white', linewidth=1)
    # ax1.add_artist(center_circle)
    #
    # # for text in texts:
    # #     text.set_color('grey')
    # #
    # # for auto_text in auto_texts:
    # #     auto_text.set_color('grey')
    # ax1.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    #
    # # bbox_props = dict(boxstyle="square,pad=0.3", fc="w", ec="k", lw=0.72)
    # kw = dict(xycoords='data', textcoords='data', arrowprops=dict(arrowstyle="-"),
    #           zorder=0, va="center")
    # for i, p in enumerate(wedges):
    #     ang = (p.theta2 - p.theta1) / 2. + p.theta1
    #     y = np.sin(np.deg2rad(ang))
    #     x = np.cos(np.deg2rad(ang))
    #     horizontalalignment = {-1: "right", 1: "left"}[int(np.sign(x))]
    #     connectionstyle = "angle,angleA=0,angleB={}".format(ang)
    #     kw["arrowprops"].update({"connectionstyle": connectionstyle})
    #
    #
    #     num_hr = int(cleaned_data_in_min[i] / 60)
    #     num_min = cleaned_data_in_min[i] % 60
    #     ax1.annotate(" ".join([str(cleaned_categories[i]), ": ", str(num_hr), "hr, ", str(num_min), " min"]),
    #                  xy=(x, y), xytext=(1.2 * np.sign(x), 1.3 * np.power(y, 1.05)),
    #                  horizontalalignment=horizontalalignment, **kw)
    #     # ax1.annotate(" ".join([str(cleaned_categories[i]), ": ", str(cleaned_data_in_min[i]), " min", "(X%)"]),
    #     #                         xy=(x, y), xytext=(1 * np.sign(x), (1 + 0.1 * y) * y),
    #     #             horizontalalignment=horizontalalignment, **kw)
    #     # (1 + random.uniform(0.05, 0.1)) * y),
    ### END PIE CHART LOGIC


    plt.title("Daily Breakdown: " + person_name.upper())
    # plt.tight_layout()
    # ax1.title("Daily Breakdown: " + person_name)
    # ax1.get_title().set_position((-1, 0))
    graph_file_name = re.sub(r'/', '-', graph_name)
    graph_file_name = graph_file_name + ".png"
    print(graph_file_name)
    plt.savefig(os.path.join(os.path.dirname(os.path.abspath(__file__)), graph_file_name))

    # plt.show()
    # plt.close()
    return graph_file_name

# Takes a time of form "HH:MM" and converts it into <hr>.<min> form. (ex. 7:50 -> 7.5)
def convert_time_to_min_float(time_str):
    print("TIME_STR: ", time_str)
    hr, min = re.split(r':', time_str)
    hr_int = int(hr)
    min_int = int(min)
    total_min = hr_int * 60 + min_int
    return total_min

def create_graph_name(person_name, graph_prefix):
    return "-".join([graph_prefix, person_name])


def main_runner():

    # Create a new timesheet for today
    create_new_sheet_for_today()

    # Get yesterday's time sheet
    curr_date_str = date_utils.get_curr_date_minus_days(3)
    range_dict = create_range_with_date(curr_date_str)

    # Main loop for each person
    for name in range_dict:

        try:
            print("CURR_NAME: ", name)
            # Extract metrics for yesterday
            metrics_dict, categories, data = extract_metrics(name, range_dict[name])
            metrics_dict['date'] = curr_date_str

            # Create graph
            graph_name = create_graph_name(name, curr_date_str)
            graph_file_name = create_chart(name, categories, data, graph_name)

            # Create email with metrics and graph
            # Send email
            email_result = email_utils.send_email_with_config(metrics_dict, graph_file_name, curr_date_str, TO_EMAILS[name])
            print("EMAIL_RESULT: ", email_result)
        except Exception as e:
            print(e)

    # Log success/failure


# Duplicates the Template spreadsheet and names it today's date.
def create_new_sheet_for_today():

    new_sheet_title = date_utils.get_curr_date_minus_days(0)
    if does_sheet_exist(new_sheet_title):
        print("SHEET titled {} already exists!".format(new_sheet_title))
        return

    # Create a new sheet for today
    copy_sheet_request = {
        'destination_spreadsheet_id': SPREADSHEET_ID  # Copy to same spreadsheet
    }
    copy_sheet_result = service.spreadsheets().sheets().copyTo(
        spreadsheetId=SPREADSHEET_ID,
        sheetId=TEMPLATE_ID,
        body=copy_sheet_request
    ).execute()
    print("COPY_SHEET_RESULT: ", copy_sheet_result)

    new_sheet_id = copy_sheet_result['sheetId']

    # Change new sheet name to date
    requests = []
    requests.append({
        'updateSheetProperties': {
            'properties': {
                'sheetId': new_sheet_id,
                'title': new_sheet_title
            },
            'fields': 'title'
        }
    })
    req_body = {
        'requests': requests
    }
    sheet_update_result = service.spreadsheets().batchUpdate(
        spreadsheetId=SPREADSHEET_ID, body=req_body
    ).execute()
    print("SHEET_UPDATE_RESULT: ", sheet_update_result)

def does_sheet_exist(sheet_title):
    sheet_metadata = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    print(sheet_metadata.get('sheets'))
    sheets_data = sheet_metadata.get('sheets')
    print("SHEET_EXIST_METADATA: ", sheets_data)

    # Find a sheet with the same name as the date string
    matching_sheets = [sheet_data for sheet_data in sheets_data if sheet_data['properties']['title'] == sheet_title]
    print("MATCHING_SHEETS: ", matching_sheets)
    if len(matching_sheets) == 0:
        return False
    return True

if __name__ == '__main__':
    main_runner()
    # create_chart("bob", [None, 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i'], [None, 30, 2, 60,30, 2, 60, 30, 2, 60], "GRAPH TEST")







# import matplotlib.pyplot as plt
#
# # Pie chart, where the slices will be ordered and plotted counter-clockwise:
# labels = 'Frogs', 'Hogs', 'Dogs', 'Logs'
# sizes = [15, 30, 45, 10]
# # explode = (0, 0.1, 0, 0)  # only "explode" the 2nd slice (i.e. 'Hogs')
# explode = (0, 0, 0, 0)  # only "explode" the 2nd slice (i.e. 'Hogs')
#
# fig1, ax1 = plt.subplots()
# ax1.pie(sizes, explode=explode, labels=labels, autopct='%1.1f%%',
#         shadow=True, startangle=90)
# ax1.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
#
# plt.savefig('test_img.png')
# # plt.show()
# plt.close()