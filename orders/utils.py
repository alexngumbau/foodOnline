import datetime

import pytz


def generate_order_number(pk):
    print("PRIMARY KEY", pk)

    nairobi_tz = pytz.timezone('Africa/Nairobi')

    current_datetime = datetime.datetime.now(nairobi_tz).strftime('%Y%m%d%H%M%S')
    print("THIS IS THE CURRENT TIME", current_datetime)
    order_number = current_datetime + str(pk)
    return order_number