import pandas as pd

def filter_large_csv_by_stay_ids(input_file, output_file, key_col, chunksize=100_000):

    valid_ids = [2307, 773]

    reader = pd.read_csv(input_file, chunksize=chunksize)
    first_chunk = True

    total_rows_kept = 0
    for i, chunk in enumerate(reader):
        filtered_chunk = chunk[chunk[key_col].isin(valid_ids)]
        total_rows_kept += len(filtered_chunk)

        if first_chunk:
            filtered_chunk.to_csv(output_file, index=False, mode='w')
            first_chunk = False
        else:
            filtered_chunk.to_csv(output_file, index=False, mode='a', header=False)

        print(f"✔ Chunk {i+1} done, {len(filtered_chunk)} rows extracted.")

def process_columns_rename_time(data_file, output_file):

    df = pd.read_csv(data_file)

    df = df[["CaseID", "DataID", "Offset", "Val"]]

    df.rename(columns={'CaseID': 'stay_id'}, inplace=True)
    df.rename(columns={'DataID': 'item'}, inplace=True)
    df.rename(columns={'Offset': 'starttime'}, inplace=True)
    df.rename(columns={'Val': 'rate'}, inplace=True)
    
    mapping = {2307: 'Dobutamine', 773: 'Norepinephrine'}
    df["item"] = df["item"].map(mapping).fillna(df["item"])

    df["rate"] = df["rate"].apply(lambda x: x * 16666.67)

    base_time = pd.Timestamp("2050-01-01 00:00:00")
    df['starttime'] = (
        base_time
        + pd.to_timedelta(pd.to_numeric(df['starttime'], errors="coerce"),
                          unit="second")
    ).dt.strftime("%Y-%m-%d %H:%M:%S")

    df.sort_values(by=['stay_id', 'starttime'], inplace=True)

    df["starttime"] = pd.to_datetime(
        df["starttime"],
        format="%Y-%m-%d %H:%M:%S",
        errors="coerce",
    )

    # endtime = starttime + 1 hour
    df["endtime"] = df["starttime"] + pd.Timedelta(hours=1)

    # remove isolated events (< 1 hour)
    endpoints = pd.concat(
        [
            df[["stay_id", "item", "starttime"]].rename(
                columns={"starttime": "time"}
            ),
            df[["stay_id", "item", "endtime"]].rename(
                columns={"endtime": "time"}
            ),
        ],
        ignore_index=True,
    )

    shared = endpoints.duplicated(
        subset=["stay_id", "item", "time"],
        keep=False,
    ).to_numpy()

    connected = shared[:len(df)] | shared[len(df):]
    df = df.loc[connected].copy()

    for col in ["starttime", "endtime"]:
        df[col] = df[col].dt.strftime("%Y-%m-%d %H:%M:%S")

    df = df.reset_index(drop=True)

    # Move endtime column
    cols = df.columns.tolist()
    cols.remove("endtime")
    cols.insert(3, "endtime")
    df = df[cols]

    df.to_csv(output_file, index=False)
    print(f"Results saved to: {output_file}")

if __name__ == "__main__":

    filter_large_csv_by_stay_ids('../../sic/data_float_h_noraw.csv', './adrenal.csv', 'DataID')
    process_columns_rename_time('./adrenal.csv', './adrenal.csv')