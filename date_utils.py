import pytz
import datetime

def get_current_date():
    date_format = '%m/%d/%Y'
    date = datetime.datetime.now(tz=pytz.utc)
    pacific_date = date.astimezone(pytz.timezone('US/Pacific'))
    print("CURR_DATE: ", pacific_date.strftime(date_format))

    return pacific_date.strftime(date_format)

def get_curr_date_minus_days(num_days):
    date_format = '%m/%d/%Y'
    date = datetime.datetime.now(tz=pytz.utc)
    pacific_date = date.astimezone(pytz.timezone('US/Pacific'))
    new_date = pacific_date - datetime.timedelta(days=num_days)
    print("AFTER_CHANGE: ", new_date.strftime(date_format))
    return new_date.strftime(date_format)

if __name__ == "__main__":
    get_current_date()

