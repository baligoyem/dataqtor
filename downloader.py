import pandas as pd
from io import BytesIO
import base64


def to_excel(df):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index = False)
    writer.save()
    processed_data = output.getvalue()
    return processed_data


def get_table_download_link(df):
    """Generates a link allowing the data in a given panda dataframe to be downloaded
        in:  dataframe
        out: href string
        """
    val = to_excel(df)
    return val
