from datetime import datetime, timedelta, timezone
import random

import pandas as pd

FILE_PATH = "C:\code\postgres_sql\dir_data1.xlsx"


def generate_custom_metadata(num_records):
    data = []
    base_time = datetime.now(tz=timezone.utc)
    host_names = ["pc 1", "pc 2", "pc 3", "pc 4", "pc 5", "pc 6", "pc 7", "pc 8", "pc 9", "pc 10"]
    for host_name in host_names:
        for i in range(num_records):
            if host_names.index(host_name) >= len(host_names) / 2:
                path = fr"c:\users\user!\folder_{i // 100}#\file_{i}.txt"
            else:
                path = f"/home/user/documents!/folder_{i // 100}#/file_{i}"
            creation_time = base_time - timedelta(days=random.randint(0, 100), seconds=random.randint(0, 1000))
            last_updated = creation_time + timedelta(minutes=random.randint(0, 500))
            state_timestamp = last_updated + timedelta(days=random.randint(0, 100))

            data.append([
                host_name,
                path,
                state_timestamp.strftime('%Y-%m-%d %H:%M:%S %z'),
                creation_time.strftime('%Y-%m-%d %H:%M:%S %z'),
                last_updated.strftime('%Y-%m-%d %H:%M:%S %z')
            ])

    df = pd.DataFrame(data, columns=["host_name", "path", "state_timestamp", "creation_time", "last_updated"])
    return df


dir_records_data = generate_custom_metadata(1000)
dir_records_data.to_excel(FILE_PATH, index=False)
