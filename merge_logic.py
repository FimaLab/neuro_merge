import pandas as pd
import re

def extract_well_letter(well_id):
    """Извлекает букву из well_id (A3 -> A)"""
    try:
        if isinstance(well_id, str):
            match = re.match(r"^([A-Za-z])", well_id.strip())
            if match:
                return match.group(1).upper()
    except:
        pass
    return ""

def safe_float(value):
    try:
        if pd.isna(value) or value == '':
            return None
        value_str = str(value).strip()
        if value_str == "-":
            return "-"  # 👈 сохраняем дефис как есть
        value_str = value_str.replace(",", ".")
        return float(value_str)
    except:
        return value  # 👈 вернём как есть, даже если это текст

def parse_time_interval(time_str):
    """Парсит временной интервал и возвращает среднее время в минутах"""
    try:
        if isinstance(time_str, str):
            times = re.findall(r'(\d+):(\d+):(\d+)', time_str)
            if len(times) >= 2:
                start_h, start_m, start_s = map(int, times[0])
                end_h, end_m, end_s = map(int, times[1])
                start_total_minutes = start_h * 60 + start_m + start_s / 60
                end_total_minutes = end_h * 60 + end_m + end_s / 60
                return (start_total_minutes + end_total_minutes) / 2
        return 0
    except:
        return 0

def calculate_light_status(time_minutes):
    """Определяет статус света - каждые 10 минут переключение, начинается с Off"""
    cycle_position = time_minutes % 20
    return "Off" if cycle_position < 10 else "on"

def get_test_control(well_id):
    well_letter = extract_well_letter(well_id)
    return "Control" if well_letter == 'A' else "Test"

def get_concentration_for_well(well_id, concentrations):
    well_letter = extract_well_letter(well_id)
    return "" if well_letter == 'A' else concentrations.get(well_letter, "")

def find_data_rows(df):
    data_rows = []
    for idx, row in df.iterrows():
        try:
            col1 = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""
            if re.match(r'^[A-Ha-h]\d+', col1):
                data_rows.append(idx)
        except:
            continue
    return data_rows

def extract_data_with_index(df, table_type, experiment_id_label):
    data = []
    indices = find_data_rows(df)
    for idx in indices:
        row = df.iloc[idx]
        try:
            experiment_id = experiment_id_label
            well_id = str(row.iloc[1]).strip()
            time_str = str(row.iloc[2]).strip() if len(row) > 2 else ""
            if not experiment_id or not well_id:
                continue
            merge_key = f"{experiment_id}_{well_id}_{idx}"
            if table_type == 1:
                record = {
                    'merge_key': merge_key,
                    'experiment_id': experiment_id,
                    'well_id': well_id,
                    'time': time_str,
                    'distance_moved': safe_float(row.iloc[3]),
                    'velocity': safe_float(row.iloc[4]),
                    'movement1': safe_float(row.iloc[5]),
                    'movement2': safe_float(row.iloc[6])
                }
            elif table_type == 2:
                record = {
                    'merge_key': merge_key,
                    'experiment_id': experiment_id,
                    'well_id': well_id,
                    'heading': safe_float(row.iloc[3]),
                    'turn_angle': safe_float(row.iloc[4]),
                    'angular_velocity': safe_float(row.iloc[5]),
                    'meander1': safe_float(row.iloc[6]),
                    'meander2': safe_float(row.iloc[7])
                }
            else:
                record = {
                    'merge_key': merge_key,
                    'experiment_id': experiment_id,
                    'well_id': well_id,
                    'cw_rotation': safe_float(row.iloc[3]),
                    'ccw_rotation': safe_float(row.iloc[4])
                }
            data.append(record)
        except:
            continue
    return pd.DataFrame(data)

import pandas as pd
import re

# ... (предыдущие функции без изменений)

def merge_tables_corrected(df1, df2, df3, exposure_time, compound, concentrations, experiment_id_label):
    d1 = extract_data_with_index(df1, 1,experiment_id_label)
    d2 = extract_data_with_index(df2, 2,experiment_id_label)
    d3 = extract_data_with_index(df3, 3,experiment_id_label)
    if d1.empty or d2.empty or d3.empty:
        return pd.DataFrame()
    try:
        merged = d1.merge(d2, on='merge_key').merge(d3, on='merge_key')
    except:
        return pd.DataFrame()
    result_data = []
    for _, row in merged.iterrows():
        time_minutes = parse_time_interval(row['time'])
        light_status = calculate_light_status(time_minutes)
        test_control = get_test_control(row['well_id'])
        concentration = get_concentration_for_well(row['well_id'], concentrations)
        result_data.append({
            'experiment_id': row['experiment_id'],
            'exposure_time': exposure_time,
            'well_id': row['well_id'],
            'Test/control': test_control,
            'Compound': compound if test_control == "Test" else "",
            'Concentration': concentration,
            'Time': row['time'],
            'Light': light_status,
            'Distance moved': row['distance_moved'],
            'Velocity': row['velocity'],
            'Movement': row['movement1'],
            'Movement (alt)': row['movement2'],
            'Heading': row['heading'],
            'Turn angle': row['turn_angle'],
            'Angular velocity': row['angular_velocity'],
            'Meander': row['meander1'],
            'Meander (alt)': row['meander2'],
            'CW Rotation': row['cw_rotation'],
            'CCW Rotation': row['ccw_rotation']
        })
    return pd.DataFrame(result_data)

def add_column_headers(df):
    columns = [
        'experiment_id', 'exposure_time', 'well_id', 'Test/control', 'Compound',
        'Concentration', 'Time', 'Light', 'Distance moved', 'Velocity',
        'Movement', 'Movement (alt)', 'Heading', 'Turn angle', 'Angular velocity',
        'Meander', 'Meander (alt)', 'CW Rotation', 'CCW Rotation'
    ]
    h1 = {col: "" for col in columns}
    h2 = h1.copy()
    h3 = h1.copy()

    h1.update({
        'Distance moved': "Center-point",
        'Velocity': "Center-point",
        'Movement': "Moving / Center-point",
        'Movement (alt)': "Not Moving / Center-point",
        'Heading': "Center-point",
        'Turn angle': "Center-point / relative",
        'Angular velocity': "Center-point / relative",
        'Meander': "Center-point / relative",
        'Meander (alt)': "Center-point / relative",
        'CW Rotation': "Center-point / Clockwise",
        'CCW Rotation': "Center-point / Counter clockwise",
    })
    h2.update({
        'Distance moved': "Total",
        'Velocity': "Mean",
        'Movement': "Cumulative Duration",
        'Movement (alt)': "Cumulative Duration",
        'Heading': "Mean",
        'Turn angle': "Mean",
        'Angular velocity': "Mean",
        'Meander': "Mean",
        'Meander (alt)': "Total",
        'CW Rotation': "Frequency",
        'CCW Rotation': "Frequency",
    })
    h3.update({
        'Distance moved': "mm",
        'Velocity': "mm/s",
        'Movement': "s",
        'Movement (alt)': "s",
        'Heading': "deg",
        'Turn angle': "deg",
        'Angular velocity': "deg/s",
        'Meander': "deg/mm",
        'Meander (alt)': "deg/mm"
    })
    return pd.concat([pd.DataFrame([columns], columns=columns),
                      pd.DataFrame([h1, h2, h3]),
                      df], ignore_index=True)

