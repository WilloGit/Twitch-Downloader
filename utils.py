def is_valid_time(time_str):
    return len(time_str) == 6 and time_str.isdigit()

def format_time(time_str):
    return f"{time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}"
