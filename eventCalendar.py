import calendar

def get_calendar_data(year, month):
    month_name = calendar.month_name[month]
    calendar.setfirstweekday(6)
    weeks = calendar.monthcalendar(year, month)

    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)

    return dict(
        year=year, month=month, month_name=month_name,
        weeks=weeks,
        prev_year=prev_year, prev_month=prev_month,
        next_year=next_year, next_month=next_month
    )
