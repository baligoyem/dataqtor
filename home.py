import streamlit as st
from streamlit import caching
import SessionState
import pandas as pd
from pandas_profiling import ProfileReport
from streamlit_pandas_profiling import st_profile_report
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from gaugeChart import gauge
import numpy as np
import datetime
from dateutil.relativedelta import relativedelta
from string_grouper import match_strings
import re
from TRnoChecker import isValidTCID, taxnum_checker
import TR_name_gender
from downloader import get_table_download_link
from utils import download_button

st.set_option('deprecation.showPyplotGlobalUse', False)
st.set_page_config(page_title="Your Data Quality Detector", page_icon="🔍", layout="wide")
hide_streamlit_style = """
            <style>
            footer {
	        visibility: hidden;
	            }
            footer:after {
	            content:'developed by Beytullah Ali Göyem'; 
	            visibility: visible;
	            display: block;
	            position: relative;
	            #background-color: red;
	            padding: 5px;
	            top: 2px;
                    }
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)


@st.cache(allow_output_mutation=True, persist = True)
def beforeSTable():
    global before
    before = pd.DataFrame(columns=["Column", "Null Records", "Out of Format Records", "Proper Format Records", "Column DQ Score(%)"])
    return before


@st.cache(allow_output_mutation=True, persist = True)
def afterSTable():
    global after
    after = pd.DataFrame(columns=["Column", "Null Records", "Out of Format Records", "Proper Format Records", "Column DQ Score(%)"])
    return after


@st.cache(allow_output_mutation=True, persist=True)
def reading_dataset():
    global dataset
    try:
        dataset = pd.read_excel(uploaded_file)
    except ValueError:
        dataset = pd.read_csv(uploaded_file)
    return dataset


st.image('DataQtor.png', width=250)
with st.sidebar.subheader('Upload your file'):
    uploaded_file = st.sidebar.file_uploader("Please upload a file of type: xlsx, csv", type=["xlsx", "csv"])
st.sidebar.subheader("Notepad")
st.sidebar.text_area(label="Enter your note here!", value="You don't have any notes", height=30)
st.sidebar.subheader("")
st.sidebar.write("&nbsp[![Buy me a coffee](https://img.shields.io/badge/Buy_Me_A_Coffee-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://www.buymeacoffee.com/baligoyem)&nbsp[![Connect](https://img.shields.io/badge/Beytullah-0077B5?style=for-the-badge&logo=linkedin&logoColor=white&link=https://tr.linkedin.com/in/beytullah-ali-g%C3%B6yem-461749152)](https://tr.linkedin.com/in/beytullah-ali-g%C3%B6yem-461749152)")
st.sidebar.subheader("")
if st.sidebar.button("Clear Cache"):
	caching.clear_memo_cache()
	st.sidebar.success("Cache is cleared!")
if uploaded_file is not None:
    before = beforeSTable()
    after = afterSTable()
    dataset = reading_dataset()
    task = st.selectbox("Menu", ["Data Profiler", "Data Quality Detector",
                                 "Data Corrector", "Review Summary Report and Download Adjusted Data", "Contact Me"])
    st.session_state.beforeSS = before
    st.session_state.afterSS = after
    if task == "Data Profiler":
        pr = ProfileReport(dataset, explorative=True, orange_mode=True)
        st_profile_report(pr)
    elif task == "Data Quality Detector":
        numerical = dataset.select_dtypes(include=['number', 'bool', 'datetime64[ns]', 'timedelta64'])
        st.table(pd.DataFrame([[dataset.shape[0], dataset.shape[1],
                                (dataset.shape[1] - numerical.shape[1]), numerical.shape[1]]],
                              columns=["Row Count", "Column Count", "Nominal Column Count",
                                       "Numeric Column Count"], index=[""]))
        columns = dataset.columns.to_numpy().tolist()
        useless = dataset[dataset.isnull().sum(axis=1) > (dataset.shape[1] / 2)]
        uselessRows_count = useless.shape[0]
        if uselessRows_count > 0:
            st.write(str(uselessRows_count), "rows may be useless:", useless)
            st.write("")

        duplicated = dataset[dataset.duplicated()]
        idx_dup = dataset[dataset.duplicated()].index
        duplicatedRows_count = duplicated.shape[0]
        if duplicatedRows_count == 0:
            st.success("There is no duplicated rows in the dataset.")
        else:
            st.write("There are", str(duplicatedRows_count), "duplicated rows in the dataset:",
                     dataset[dataset.duplicated()])
            if st.button("Drop Duplicated Rows"):
                dataset.drop(index=idx_dup, inplace=True)
                st.success("Duplicated rows were deleted.")
        st.write("---")

        if st.checkbox("Run Column Detector", key="run_col_detector"):
            cols = st.beta_columns(2)
            with cols[0]:
                selected_column = st.selectbox("Column", columns, key="col_select")
            with cols[1]:
                label = st.selectbox("Define the DQ Rule",
                                     ["Select", "Define the DQ Rule Yourself", "E-mail Address", "Şehir (TR)",
                                      "T.C. Kimlik No", "Telefon No", "Vergi Kimlik No"], key="define_dq_rule")

            cols = st.beta_columns((7, 1.4, 1.6))
            with cols[0]:
                st.write("Type:", dataset[selected_column].dtype)
            if (dataset[selected_column].dtype == np.int16 or dataset[selected_column].dtype == np.int32 or
                        dataset[selected_column].dtype == np.int64 or dataset[selected_column].dtype == np.float16 or dataset[
                    selected_column].dtype == np.float32 or dataset[selected_column].dtype == np.float64):
                with cols[1]:
                    if st.checkbox("Show Total"):
                        total = dataset[selected_column].sum()
                        with cols[2]:
                            st.write(": ", '{:,.2f}'.format(total))
            elif dataset[selected_column].dtype == 'object':
                    strMinLength = dataset[selected_column].str.len().min()
                    strMaxLength = dataset[selected_column].str.len().max()
                    valueStrMin = dataset.reset_index(drop=True).loc[dataset[selected_column].str.len().argmin(), selected_column]
                    valueStrMax = dataset.reset_index(drop=True).loc[dataset[selected_column].str.len().argmax(), selected_column]
                    valueMin = dataset[selected_column].dropna().astype(str).sort_values().min()
                    valueMax = dataset[selected_column].dropna().astype(str).sort_values().max()
                    strCA = pd.DataFrame(
                        [[strMinLength, valueStrMin, strMaxLength, valueStrMax, valueMin, valueMax]],
                        columns=["Min Length", "Value (minLen)", "Max Length", "Value (maxLen)",
                                 "Min (Alphabetic)", "Max (Alphabetic)"], index=["info"])
                    st.write(strCA)

            filledCount = dataset[selected_column].count()
            nanCount = int(dataset[selected_column].isna().sum())
            nonNullValues_per = (dataset[selected_column].count() / len(dataset) * 100).round(1)
            nullValues_per = (dataset[selected_column].isna().sum() / len(dataset) * 100).round(1)
            nanDF = pd.DataFrame([[filledCount, nonNullValues_per],
                                  [nanCount, nullValues_per]], columns=["count", "percentage(%)"],
                                 index=["non-NaN", "isNaN"])

            def color_survived(val):
                if val == nanDF["percentage(%)"]["isNaN"] and val >= 50:
                    color = '#FA8072'
                    return f'background-color: {color}'
                else:
                    color = 'white'
                    return f'background-color: {color}'

            cols = st.beta_columns((3, 7))
            with cols[0]:
                st.write(
                    nanDF.style.format({'count': '{:,}', 'percentage(%)': '{:.1f}'}).applymap(color_survived, subset=['percentage(%)']))
            with cols[1]:
                describe = dataset[selected_column].describe().to_frame().T
                st.write(describe.style.format(
                    {"count": '{:,.0f}', "mean": '{:,.1f}', "std": '{:,.1f}', "min": '{:,.2f}',
                     "25%": '{:,.2f}', "50%": '{:,.2f}', "75%": '{:,.2f}', "max": '{:,.2f}'}))

            freqCount = dataset[selected_column].value_counts().to_frame(name="count")
            per = (dataset[selected_column].value_counts(normalize=True).round(3) * 100).to_frame(
                name="percentage(%)")
            general = pd.concat([freqCount, per], axis=1)
            if general.shape[0] > 10:
                cols = st.beta_columns(3)
                with cols[0]:
                    st.write("5 most frequent values in this column:",
                             general.iloc[np.r_[0:5]].style.format(
                                 {"count": '{:,}', 'percentage(%)': '{:.1f}'}))
                with cols[1]:
                    st.write("5 least frequent values in this column:",
                             general.iloc[np.r_[-5:0]].style.format(
                                 {'count': '{:,}', 'percentage(%)': '{:.1f}'}))
                with cols[2]:
                    if st.checkbox("Frequency Table", key="freq_table"):
                        st.write(general.style.format({'count': '{:,}', 'percentage(%)': '{:.1f}'}))

            else:
                st.write("Frequency Table:", general.style.format({'count': '{:,}', 'percentage(%)': '{:.1f}'}))

            if dataset[selected_column].value_counts().count() > 10:
                unexpected = general[general["percentage(%)"] < 0.1]
                if not unexpected.empty:
                    unexpected['value'] = unexpected.index.astype('str')
                    if (unexpected["value"].value_counts().count() <= 25):
                        fig = plt.figure(figsize=(20, 6))
                        ax = fig.add_axes([0, 0, 1, 1])
                        plt.title("Unexpected Value Graph\n ", size=20, loc="left")
                        ax.bar(unexpected.value, unexpected["count"], color="#262730")
                        ax = plt.gca()
                        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
                        ax.tick_params(axis='both', which='major', labelsize=14)
                        plt.xticks(rotation=45)
                        plt.xlabel("value", fontsize=15)
                        plt.ylabel("count", fontsize=15)
                        plt.show()
                        st.pyplot(fig)

            if (dataset[selected_column].dtype == np.int16 or dataset[selected_column].dtype == np.int32 or
                        dataset[selected_column].dtype == np.int64 or dataset[selected_column].dtype == np.float16 or dataset[
                    selected_column].dtype == np.float32 or dataset[selected_column].dtype == np.float64):
                cols = st.beta_columns(2)
                with cols[0]:
                    if st.checkbox("Show p-0-n"):
                        countp = dataset[dataset[selected_column] > 0][selected_column].count()
                        count0 = dataset[dataset[selected_column] == 0][selected_column].count()
                        countn = dataset[dataset[selected_column] < 0][selected_column].count()
                        countp_per = (countp / len(dataset) * 100).round(1)
                        count0_per = (count0 / len(dataset) * 100).round(1)
                        countn_per = (countn / len(dataset) * 100).round(1)
                        dfp0n = pd.DataFrame([[countp, countp_per],
                                              [count0, count0_per],
                                              [countn, countn_per]], columns=["count", "percentage(%)"],
                                             index=["positive value", "0-value", "negative value"])
                        st.write(dfp0n.style.format({'count': '{:,}', 'percentage(%)': '{:.1f}'}))

            dataset.pattern = dataset[selected_column].astype(str).replace('nan', np.NaN).str.replace(
                '[A-Za-zÖÇĞİŞÜöçğışü]', 'A').dropna()
            dataset.pattern = dataset.pattern.astype(str).str.replace('[0-9]', "9")
            countpattern = dataset.pattern.value_counts().to_frame(name="count")
            perforPattern = (dataset.pattern.value_counts(normalize=True).round(3) * 100).to_frame(
                name="percentage(%)")
            generalPattern = pd.concat([countpattern, perforPattern], axis=1)
            if generalPattern.shape[0] > 10:
                cols = st.beta_columns(3)
                with cols[0]:
                    st.write("5 most frequent patterns in this column:",
                             generalPattern.iloc[np.r_[0:5]].style.format(
                                 {"count": '{:,}', 'percentage(%)': '{:.1f}'}))
                with cols[1]:
                    st.write("5 least frequent patterns in this column:",
                             generalPattern.iloc[np.r_[-5:0]].style.format(
                                 {'count': '{:,}', 'percentage(%)': '{:.1f}'}))
                with cols[2]:
                    if st.checkbox("Pattern Table", key="pattern_table"):
                        st.write(generalPattern.style.format({'count': '{:,}', 'percentage(%)': '{:.1f}'}))
            else:
                st.write("Pattern Table:",
                             generalPattern.style.format({'count': '{:,}', 'percentage(%)': '{:.1f}'}))

            st.warning(
                "Duplicated Data Detector works well especially while checking Customer-related datasets. If you're going to run 'DDD', make sure the column is fit for purpose!")
            if st.checkbox("Run Duplicated Data Detector"):
                try:
                    st.write("Records that may be duplicate:",
                             pd.concat(g for _, g in dataset.groupby(selected_column) if len(g) > 1))
                except ValueError:
                    if dataset[selected_column].isnull().sum() == dataset.shape[0]:
                        st.info("All values in this column are NaN.")
                    else:
                        st.info("All values in this column are unique.")

            if st.checkbox("Run Similarity Detector"):
                matches = match_strings(dataset[selected_column].apply(str), min_similarity=0.52)
                # Look at only the non-exact matches:
                st.write(matches[matches['left_{0}'.format(selected_column)] != matches[
                    'right_{0}'.format(selected_column)]].sort_values(['similarity'],
                                                                      ascending=False).head(50))

            NOFR = 0
            if label == "Define the DQ Rule Yourself":
                st.write("---")
                st.subheader("Define the DQ Rule")
                st.write("")
                if (dataset[selected_column].dtype == np.int16 or dataset[selected_column].dtype == np.int32 or
                        dataset[selected_column].dtype == np.int64):
                    editlen = st.selectbox("Select Qualification",
                                           ["Equals", "Greater than or equal to", "Less than", "Between"])
                    if editlen == "Equals":
                        length = st.number_input("Value", format="%i", value=0, min_value=-5000000000,
                                                 max_value=5000000000, step=1)
                        f1 = dataset[selected_column][~(dataset[selected_column] == length)]

                    elif editlen == "Greater than or equal to":
                        length = st.number_input("Value", format="%i", value=0, min_value=-5000000000,
                                                 max_value=5000000000, step=1)
                        f1 = dataset[selected_column][~(dataset[selected_column] >= length)]

                    elif editlen == "Less than":
                        length = st.number_input("Value", format="%i", value=0, min_value=-5000000000,
                                                 max_value=5000000000, step=1)
                        f1 = dataset[selected_column][~(dataset[selected_column] < length)]

                    elif editlen == "Between":
                        cols = st.beta_columns((2, 1, 1, 1, 2))
                        with cols[0]:
                            length1 = st.number_input("Value1", format="%i", value=0, min_value=-5000000000,
                                                      max_value=5000000000, step=1)
                        with cols[2]:
                            st.write("AND")
                        with cols[4]:
                            length2 = st.number_input("Value2", format="%i", value=0, min_value=-5000000000,
                                                      max_value=5000000000, step=1)
                        cols = st.beta_columns((1, 1, 1))
                        with cols[1]:
                            f1 = dataset[selected_column][~((dataset[selected_column] >= length1) & (
                                    dataset[selected_column] <= length2))]

                    notuseful = f1.drop_duplicates(keep='first').dropna()
                    st.write(str(
                        "Values that do not match with the quality rules defined for " + selected_column + ":"),
                        notuseful)
                    NOFR = f1.shape[0]

                elif (dataset[selected_column].dtype == np.float16 or dataset[
                    selected_column].dtype == np.float32 or dataset[selected_column].dtype == np.float64):
                    editlen = st.selectbox("Select Qualification",
                                           ["Equals", "Greater than or equal to", "Less than", "Between"])
                    if editlen == "Equals":
                        length = st.number_input("Value", format="%f", value=0.0, min_value=-5000000000.0,
                                                 max_value=5000000000.0, step=0.01)
                        f1 = dataset[selected_column][~(dataset[selected_column] == length)]

                    elif editlen == "Greater than or equal to":
                        length = st.number_input("Value", format="%f", value=0.0, min_value=-5000000000.0,
                                                 max_value=5000000000.0, step=0.01)
                        f1 = dataset[selected_column][~(dataset[selected_column] >= length)]

                    elif editlen == "Less than":
                        length = st.number_input("Value", format="%f", value=0.0, min_value=-5000000000.0,
                                                 max_value=5000000000.0, step=0.01)
                        f1 = dataset[selected_column][~(dataset[selected_column] < length)]

                    elif editlen == "Between":
                        cols = st.beta_columns((2, 1, 1, 1, 2))
                        with cols[0]:
                            length1 = st.number_input("Value1", format="%f", value=0.0, min_value=-5000000000.0,
                                                      max_value=5000000000.0, step=0.01)
                        with cols[2]:
                            st.write("AND")
                        with cols[4]:
                            length2 = st.number_input("Value2", format="%f", value=0.0, min_value=-5000000000.0,
                                                      max_value=5000000000.0, step=0.01)
                        cols = st.beta_columns((1, 1, 1))
                        with cols[1]:
                            f1 = dataset[selected_column][~((dataset[selected_column] >= length1) & (
                                    dataset[selected_column] <= length2))]

                    notuseful = f1.drop_duplicates(keep='first').dropna()
                    st.write(str(
                        "Values that do not match with the quality rules defined for " + selected_column + ":"),
                        notuseful)
                    NOFR = f1.shape[0]

                elif dataset[selected_column].dtype.name == 'datetime64[ns]':
                    editlen = st.selectbox("Select Qualification",
                                           ["Equals", "Greater than or equal to", "Less than", "Between"])
                    if editlen == "Equals":
                        date = st.date_input("Value", value=datetime.date.today(), min_value=datetime.date.today()-relativedelta(years=125), max_value=datetime.date.today()+relativedelta(years=35))
                        f1 = dataset[selected_column][~(dataset[selected_column] == pd.to_datetime(date))]

                    elif editlen == "Greater than or equal to":
                        date = st.date_input("Value", value=datetime.date.today(), min_value=datetime.date.today()-relativedelta(years=125), max_value=datetime.date.today()+relativedelta(years=35))
                        f1 = dataset[selected_column][~(dataset[selected_column] >= pd.to_datetime(date))]

                    elif editlen == "Less than":
                        date = st.date_input("Value", value=datetime.date.today(), min_value=datetime.date.today()-relativedelta(years=125), max_value=datetime.date.today()+relativedelta(years=35))
                        f1 = dataset[selected_column][~(dataset[selected_column] < pd.to_datetime(date))]

                    elif editlen == "Between":
                        cols = st.beta_columns((2, 1, 1, 1, 2))
                        with cols[0]:
                            date1 = st.date_input("Value1", value=datetime.date.today(), min_value=datetime.date.today()-relativedelta(years=125), max_value=datetime.date.today()+relativedelta(years=35))
                        with cols[2]:
                            st.write("AND")
                        with cols[4]:
                            date2 = st.date_input("Value2", value=datetime.date.today(), min_value=datetime.date.today()-relativedelta(years=125), max_value=datetime.date.today()+relativedelta(years=35))
                        cols = st.beta_columns((1, 1, 1))
                        with cols[1]:
                            f1 = dataset[selected_column][~((dataset[selected_column] >= pd.to_datetime(date1)) & (
                                    dataset[selected_column] <= pd.to_datetime(date2)))]

                    notuseful = f1.drop_duplicates(keep='first').dropna()
                    st.write(str(
                        "Values that do not match with the quality rules defined for " + selected_column + ":"),
                        notuseful)
                    NOFR = f1.shape[0]

                else:
                    dataset[selected_column] = dataset[selected_column].astype(str).replace('nan', np.NaN)
                    f1 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 9999)]
                    if st.checkbox("Set Qualification by Length"):
                        editlen = st.selectbox("Select Qualification",
                                               ["Equals", "Greater than or equal to", "Less than", "Between"])
                        if editlen == "Equals":
                            length = st.number_input("Value", format="%i", value=0, min_value=0, max_value=1000,
                                                     step=1)
                            f1 = dataset[selected_column][
                                ~(dataset[selected_column].astype(str).map(len) == length)]

                        elif editlen == "Greater than or equal to":
                            length = st.number_input("Value", format="%i", value=0, min_value=0, max_value=1000,
                                                     step=1)
                            f1 = dataset[selected_column][
                                ~(dataset[selected_column].astype(str).map(len) >= length)]

                        elif editlen == "Less than":
                            length = st.number_input("Value", format="%i", value=0, min_value=0, max_value=1000,
                                                     step=1)
                            f1 = dataset[selected_column][
                                ~(dataset[selected_column].astype(str).map(len) < length)]

                        elif editlen == "Between":
                            cols = st.beta_columns((2, 1, 1, 1, 2))
                            with cols[0]:
                                length1 = st.number_input("Value1", format="%i", value=0, min_value=0,
                                                          max_value=1000, step=1)
                            with cols[2]:
                                st.write("AND")
                            with cols[4]:
                                length2 = st.number_input("Value2", format="%i", value=0, min_value=0,
                                                          max_value=1000, step=1)
                            cols = st.beta_columns((1, 1, 1))
                            with cols[1]:
                                f1 = dataset[selected_column][~(
                                        (dataset[selected_column].astype(str).map(len) >= length1) & (
                                        dataset[selected_column].astype(str).map(len) <= length2))]

                    f2 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 9999)]
                    rule2 = st.checkbox("Cannot contain special characters")
                    if rule2:
                        SPEC_CHARS = ["@", "-", "_", ".", ",", "~", "`", "!", "#", "$", "%", "^", "&", "*", "(",
                                      ")", "+", "=", "{", "}", "[", "]", "|", "/", ":", ";", '"', "'", "<", ">",
                                      "?"]
                        pat = '|'.join(['({})'.format(re.escape(c)) for c in SPEC_CHARS])
                        f2 = dataset[selected_column][dataset[selected_column].str.contains(pat, na=False)]
                        rule2in = st.multiselect("exclusive", SPEC_CHARS)
                        if rule2in:
                            pat = '|'.join(['({})'.format(re.escape(c)) for c in rule2in])
                            f2 = dataset[selected_column][
                                (~dataset[selected_column].str.contains(pat, na=False)) & (
                                    dataset[selected_column].str.contains(
                                        '|'.join(['({})'.format(re.escape(c)) for c in SPEC_CHARS]), na=False))]

                    f3 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 9999)]
                    rule3 = st.checkbox("Cannot contain numbers")
                    if rule3:
                        NUM_CHARS = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
                        pat = '|'.join(['({})'.format(re.escape(c)) for c in NUM_CHARS])
                        f3 = dataset[selected_column][dataset[selected_column].str.contains(pat, na=False)]

                    f4 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 9999)]
                    rule4 = st.checkbox("Cannot contain spaces")
                    if rule4:
                        f4 = dataset[selected_column][dataset[selected_column].str.contains(' ', na=False)]

                    f5 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 9999)]
                    rule5 = st.checkbox("Specified values cannot be entered")
                    if rule5:
                        canContain = st.text_input(
                            "Please separate the values with commas, for example 'bilinmiyor,yok,xxxxx' (Do not put a space after comma)")
                        canContain = canContain.split(',')
                        f5 = dataset[selected_column][dataset[selected_column].isin(canContain)]

                    notuseful = (pd.concat([f1, f2, f3, f4, f5], ignore_index=False, sort=False)).replace('nan', np.NaN).drop_duplicates(keep='first').dropna()
                    st.write(str(
                        "Values that do not match with the quality rules defined for " + selected_column + ":"),
                        notuseful)
                    notuseful = pd.concat([f1, f2, f3, f4, f5], ignore_index=False, sort=False).replace('nan',
                                                                                                        np.NaN).dropna()
                    notuseful = notuseful.groupby(notuseful.index).first()
                    NOFR = notuseful.shape[0]

            if label == "E-mail Address":
                f1 = dataset[selected_column][dataset[selected_column].str.contains("~", na=False) | dataset[
                    selected_column].str.contains("`", na=False) | dataset[selected_column].str.contains("!",
                                                                                                         na=False) |
                                              dataset[selected_column].str.contains("#", na=False) | dataset[
                                                  selected_column].str.contains("%", na=False) | dataset[
                                                  selected_column].str.contains("&", na=False) | dataset[
                                                  selected_column].str.contains("=", na=False) | dataset[
                                                  selected_column].str.contains("{", na=False) | dataset[
                                                  selected_column].str.contains("}", na=False) | dataset[
                                                  selected_column].str.contains("]", na=False) | dataset[
                                                  selected_column].str.contains(":", na=False) | dataset[
                                                  selected_column].str.contains(";", na=False) | dataset[
                                                  selected_column].str.contains("/", na=False) | dataset[
                                                  selected_column].str.contains(">", na=False) | dataset[
                                                  selected_column].str.contains("<", na=False) | dataset[
                                                  selected_column].str.contains("'", na=False) | dataset[
                                                  selected_column].str.contains('"', na=False) | dataset[
                                                  selected_column].str.contains(' ', na=False) | dataset[
                                                  selected_column].str.contains('\(', na=False) | dataset[
                                                  selected_column].str.contains('\\\\', na=False) | dataset[
                                                  selected_column].str.contains(',', na=False) | dataset[
                                                  selected_column].str.contains('\?', na=False) | dataset[
                                                  selected_column].str.contains('\|', na=False) | dataset[
                                                  selected_column].str.contains('\[', na=False) | dataset[
                                                  selected_column].str.contains('\+', na=False) | dataset[
                                                  selected_column].str.contains('\)', na=False) | dataset[
                                                  selected_column].str.contains('\*', na=False) | dataset[
                                                  selected_column].str.contains('\^', na=False) | dataset[
                                                  selected_column].str.contains('\$', na=False)]
                f2 = dataset[selected_column][dataset[selected_column].astype(str).map(len) <= 6]
                f3 = dataset[selected_column][~dataset[selected_column].str.contains("@", na=False) | ~dataset[
                    selected_column].str.contains(".", na=False)]
                f4 = dataset[selected_column][dataset[selected_column].str.count("@") > 1]
                f5 = dataset[selected_column][dataset[selected_column].str.startswith("@", na=False) | dataset[
                    selected_column].str.startswith("yok@", na=False) | dataset[selected_column].str.startswith(
                    "YOK@", na=False) | dataset[selected_column].str.startswith("www", na=False) | dataset[
                                                  selected_column].str.startswith("bbb@", na=False) | dataset[
                                                  selected_column].str.startswith("girilecek@", na=False) |
                                              dataset[selected_column].str.startswith("deneme@", na=False) |
                                              dataset[selected_column].str.startswith("Mailadresi@", na=False) |
                                              dataset[selected_column].str.startswith("dummy@", na=False)]
                searchfor = ["\@\.", "\.\@", "\@-"]
                f6 = dataset[selected_column][
                    dataset[selected_column].str.contains('|'.join(searchfor), na=False)]
                v1 = dataset[selected_column][dataset[selected_column].str.contains("ı", na=False) | dataset[
                    selected_column].str.contains("İ", na=False) | dataset[selected_column].str.contains("ç",
                                                                                                         na=False) |
                                              dataset[selected_column].str.contains("Ç", na=False) | dataset[
                                                  selected_column].str.contains("ş", na=False) | dataset[
                                                  selected_column].str.contains("Ş", na=False) | dataset[
                                                  selected_column].str.contains("ğ", na=False) | dataset[
                                                  selected_column].str.contains("Ğ", na=False) | dataset[
                                                  selected_column].str.contains("ü", na=False) | dataset[
                                                  selected_column].str.contains("Ü", na=False) | dataset[
                                                  selected_column].str.contains("ö", na=False) | dataset[
                                                  selected_column].str.contains("Ö", na=False)]
                v2 = dataset[selected_column][dataset[selected_column].str.contains(r'[A-Z]', na=False)]
                v3 = dataset[selected_column][
                    dataset[selected_column].str.endswith("gmail", na=False) | dataset[
                        selected_column].str.endswith("yahoo", na=False) | dataset[
                        selected_column].str.endswith("hotmail", na=False) | dataset[
                        selected_column].str.endswith("msn", na=False) | dataset[selected_column].str.endswith(
                        "@live", na=False) | dataset[selected_column].str.endswith("yandex", na=False) |
                    dataset[selected_column].str.endswith("outlook", na=False) | dataset[
                        selected_column].str.endswith("windowslive", na=False) | dataset[
                        selected_column].str.endswith(".com.t", na=False) | dataset[
                        selected_column].str.endswith(".o", na=False) | dataset[selected_column].str.endswith(
                        ".cm", na=False) | dataset[selected_column].str.endswith(".co", na=False) | dataset[
                        selected_column].str.endswith(".ocom", na=False) | dataset[
                        selected_column].str.endswith(".ney", na=False) | dataset[selected_column].str.endswith(
                        ".co.", na=False) | dataset[selected_column].str.endswith(".cvom", na=False) | dataset[
                        selected_column].str.endswith(".comtr", na=False) | dataset[
                        selected_column].str.endswith(".com.", na=False) | dataset[
                        selected_column].str.endswith(".comom", na=False) | dataset[
                        selected_column].str.startswith("ingo@", na=False) | dataset[
                        selected_column].str.endswith(".c", na=False) | dataset[selected_column].str.endswith(
                        ".r", na=False) | dataset[selected_column].str.endswith(".com.tr'", na=False) | dataset[
                        selected_column].str.endswith(".com.tr/", na=False)]
                searchfordomain = ["windowlive", "hotmil", "hatmail", "hotmial", "gamil", "gmmail", "outlok",
                                   "yaaho"]
                v4 = dataset[selected_column][
                    dataset[selected_column].str.contains('|'.join(searchfordomain), na=False)]
                notuseful = (pd.concat([f1, f2, f3, f4, f5, f6, v1, v2, v3, v4], ignore_index=False,
                                       sort=False).drop_duplicates(keep='last')).dropna()
                NOFR = notuseful.shape[0]
                st.write("Records that do not match with the quality rules defined for E-mail Address:",
                         notuseful)

            if label == "T.C. Kimlik No":
                notuseful = dataset[selected_column][
                    dataset[selected_column].apply(isValidTCID) == False].dropna()
                NOFR = notuseful.shape[0]
                st.write("Records that do not match with the quality rules defined for T.C. Kimlik No:",
                         notuseful)

            if label == "Vergi Kimlik No":
                notuseful = dataset[selected_column][
                    dataset[selected_column].apply(taxnum_checker) == False].dropna()
                NOFR = notuseful.shape[0]
                st.write("Records that do not match with the quality rules defined for Vergi Kimlik No:",
                         notuseful)

            if label == "Şehir (TR)":
                sehirler = ["Adana", "Adıyaman", "Afyon", "Ağrı", "Amasya", "Ankara", "Antalya",
                            "Artvin", "Aydın",
                            "Balıkesir", "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur", "Bursa", "Çanakkale",
                            "Çankırı",
                            "Çorum", "Denizli", "Diyarbakır", "Edirne", "Elazığ", "Erzincan", "Erzurum",
                            "Eskişehir",
                            "Gaziantep", "Giresun", "Gümüşhane", "Hakkari", "Hatay", "Isparta", "İçel",
                            "İstanbul", "İstanbul-Avrupa", "İstanbul-Anadolu",
                            "İzmir", "Kars", "Kastamonu", "Kayseri", "Kırklareli", "Kırşehir", "Kocaeli",
                            "Konya",
                            "Kütahya", "Malatya", "Manisa", "Kahramanmaraş", "Mardin", "Muğla", "Muş",
                            "Nevşehir", "Niğde",
                            "Ordu", "Rize", "Sakarya", "Samsun", "Siirt", "Sinop", "Sivas", "Tekirdağ", "Tokat",
                            "Trabzon",
                            "Tunceli", "Şanlıurfa", "Uşak", "Van", "Yozgat", "Zonguldak", "Aksaray", "Bayburt",
                            "Karaman",
                            "Kırıkkale", "Batman", "Şırnak", "Bartın", "Ardahan", "Iğdır", "Yalova", "Karabük",
                            "Kilis",
                            "Osmaniye", "Düzce"]
                notuseful = dataset[selected_column][dataset[selected_column].isin(sehirler) == False].dropna()
                NOFR = notuseful.shape[0]
                st.write("Records that do not match with the quality rules defined for Şehir (TR):", notuseful)

            if label == "Telefon No":
                dataset[selected_column] = dataset[selected_column].astype(str)
                dataset[selected_column] = dataset[selected_column].replace('nan', np.NaN)
                d111 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 11) & (
                    dataset[selected_column].str.startswith("0", na=False)) & (
                                                    ~dataset[selected_column].str.contains(" ", na=False))]
                d211 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 11) & (
                    ~dataset[selected_column].str.startswith("0", na=False)) & (
                                                        dataset[selected_column].str[3] == " ")]
                d311 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 11) & (
                    ~dataset[selected_column].str.startswith("0", na=False)) & (
                                                        dataset[selected_column].str[3] == "-")]
                d411 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 11) & (
                    dataset[selected_column].str.startswith("-", na=False)) & (
                                                    ~dataset[selected_column].str.contains(" ", na=False))]

                d112 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 12) & (
                    dataset[selected_column].str.startswith("90", na=False)) & (
                                                    ~dataset[selected_column].str.contains(" ", na=False))]
                d212 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 12) & (
                    dataset[selected_column].str.startswith("0-", na=False)) & (
                                                    ~dataset[selected_column].str.contains(" ", na=False))]
                d312 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 12) & (
                    dataset[selected_column].str.startswith("0", na=False)) & (
                                                        dataset[selected_column].str[4] == " ")]
                d412 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 12) & (
                        dataset[selected_column].str[3] == " ") & (dataset[selected_column].str[7] == " ")]
                d512 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 12) & (
                        dataset[selected_column].str[6] == " ") & (dataset[selected_column].str[9] == " ")]
                d612 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 12) & (
                    dataset[selected_column].str.startswith("0", na=False)) & (
                                                        dataset[selected_column].str[4] == "-") & (
                                                    ~dataset[selected_column].str.contains(" ", na=False))]
                d712 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 12) & (
                    ~dataset[selected_column].str.startswith("0", na=False)) & (
                                                        dataset[selected_column].str[3] == " ") & (
                                                        dataset[selected_column].str[8] == "-")]
                d812 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 12) & (
                    dataset[selected_column].str.startswith("0 ", na=False))]
                d912 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 12) & (
                    dataset[selected_column].str.startswith("0", na=False)) & (
                                                        dataset[selected_column].str[7] == " ")]
                d1012 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 12) & (
                    dataset[selected_column].str.startswith("0", na=False)) & (
                                                         dataset[selected_column].str[4] == "/") & (
                                                     ~dataset[selected_column].str.contains(" ", na=False))]
                d1112 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 12) & (
                    dataset[selected_column].str.startswith("-0", na=False)) & (
                                                     ~dataset[selected_column].str.contains(" ", na=False)) & (
                                                     ~dataset[selected_column].str.contains("/", na=False)) & (
                                                     ~dataset[selected_column].str.contains("\(", na=False)) & (
                                                     ~dataset[selected_column].str.contains("\)", na=False))]
                d1212 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 12) & (
                    dataset[selected_column].str.contains("  ", na=False)) & (
                                                     ~dataset[selected_column].str.contains("-", na=False)) & (
                                                     ~dataset[selected_column].str.contains("/", na=False)) & (
                                                     ~dataset[selected_column].str.contains("\(", na=False)) & (
                                                     ~dataset[selected_column].str.contains("\)", na=False))]
                d1312 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 12) & (
                    dataset[selected_column].str.startswith("(", na=False)) & (
                                                         dataset[selected_column].str[4] == ")") & (
                                                     ~dataset[selected_column].str.contains("-", na=False)) & (
                                                     ~dataset[selected_column].str.contains("/", na=False)) & (
                                                     ~dataset[selected_column].str.contains(" ", na=False))]

                d113 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 13) & (
                        dataset[selected_column].str[3] == " ") & (
                                                        dataset[selected_column].str[7] == " ") & (
                                                        dataset[selected_column].str[9] == " ") & (
                                                    ~dataset[selected_column].str.contains("-", na=False)) & (
                                                    ~dataset[selected_column].str.contains("/", na=False))]
                d213 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 13) & (
                        dataset[selected_column].str[3] == " ") & (
                                                        dataset[selected_column].str[7] == "-") & (
                                                        dataset[selected_column].str[10] == "-")]
                d313 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 13) & (
                    dataset[selected_column].str.startswith("(", na=False)) & (
                                                        dataset[selected_column].str[4:6] == ") ")]
                d413 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 13) & (
                    dataset[selected_column].str.startswith("90", na=False)) & (
                                                        dataset[selected_column].str[3] == " ")]
                d513 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 13) & (
                        dataset[selected_column].str[3] == " ") & (
                                                        dataset[selected_column].str[7:9] == "  ")]
                d613 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 13) & (
                        dataset[selected_column].str[3] == "-") & (
                                                        dataset[selected_column].str[7] == "-") & (
                                                        dataset[selected_column].str[10] == "-") & (
                                                    ~dataset[selected_column].str.contains(" ", na=False))]
                d713 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 13) & (
                    dataset[selected_column].str.startswith("0", na=False)) & (
                                                        dataset[selected_column].str[3] == " ") & (
                                                        dataset[selected_column].str[8] == " ")]
                d813 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 13) & (
                    dataset[selected_column].str.startswith("0", na=False)) & (
                                                        dataset[selected_column].str[4:6] == "  ")]
                d913 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 13) & (
                        dataset[selected_column].str[3] == " ") & (
                                                        dataset[selected_column].str[7] == " ") & (
                                                        dataset[selected_column].str[10] == " ")]
                d1013 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 13) & (
                    dataset[selected_column].str.startswith("0", na=False)) & (
                                                         dataset[selected_column].str[4] == " ") & (
                                                         dataset[selected_column].str[8] == " ")]
                d1113 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 13) & (
                    dataset[selected_column].str.startswith("0", na=False)) & (
                                                         dataset[selected_column].str[7] == " ") & (
                                                         dataset[selected_column].str[10] == " ")]
                d1213 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 13) & (
                    dataset[selected_column].str.startswith("(0", na=False)) & (
                                                         dataset[selected_column].str[5] == ")") & (
                                                     ~dataset[selected_column].str.contains("-", na=False)) & (
                                                     ~dataset[selected_column].str.contains("/", na=False)) & (
                                                     ~dataset[selected_column].str.contains(" ", na=False))]
                d1313 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 13) & (
                        dataset[selected_column].str[3] == "-") & (
                                                         dataset[selected_column].str[7] == " ") & (
                                                         dataset[selected_column].str[10] == " ") & (
                                                     ~dataset[selected_column].str.contains("/", na=False))]
                d1413 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 13) & (
                    dataset[selected_column].str.startswith("0", na=False)) & (
                                                         dataset[selected_column].str[4:6] == "- ") & (
                                                     ~dataset[selected_column].str.contains("/", na=False))]
                d1513 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 13) & (
                        dataset[selected_column].str[3:5] == "- ") & (
                                                         dataset[selected_column].str[8] == " ") & (
                                                     ~dataset[selected_column].str.contains("/", na=False))]
                d1613 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 13) & (
                    dataset[selected_column].str.startswith("0", na=False)) & (
                                                         dataset[selected_column].str[7] == " ") & (
                                                         dataset[selected_column].str[9] == " ") & (
                                                     ~dataset[selected_column].str.contains("/", na=False))]
                d1713 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 13) & (
                    dataset[selected_column].str.startswith("0-", na=False)) & (
                                                         dataset[selected_column].str[5] == "-") & (
                                                     ~dataset[selected_column].str.contains("/", na=False)) & (
                                                     ~dataset[selected_column].str.contains(" ", na=False))]
                d1813 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 13) & (
                    dataset[selected_column].str.startswith("0 ", na=False)) & (
                                                         dataset[selected_column].str[5] == " ") & (
                                                     ~dataset[selected_column].str.contains("/", na=False)) & (
                                                     ~dataset[selected_column].str.contains("-", na=False))]
                d1913 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 13) & (
                    dataset[selected_column].str.startswith("0", na=False)) & (
                                                         dataset[selected_column].str[4:6] == ") ") & (
                                                     ~dataset[selected_column].str.contains("/", na=False)) & (
                                                     ~dataset[selected_column].str.contains("-", na=False))]

                d114 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 14) & (
                    dataset[selected_column].str.startswith("0", na=False)) & (
                                                        dataset[selected_column].str[4] == " ") & (
                                                        dataset[selected_column].str[8] == " ") & (
                                                        dataset[selected_column].str[11] == " ") & (
                                                    ~dataset[selected_column].str.contains("/", na=False)) & (
                                                    ~dataset[selected_column].str.contains("-", na=False))]
                d214 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 14) & (
                        dataset[selected_column].str[3:5] == ") ") & (
                                                        dataset[selected_column].str[8] == " ") & (
                                                        dataset[selected_column].str[11] == " ") & (
                                                    ~dataset[selected_column].str.contains("/", na=False)) & (
                                                    ~dataset[selected_column].str.contains("-", na=False))]
                d314 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 14) & (
                    dataset[selected_column].str.startswith("0 ", na=False)) & (
                                                        dataset[selected_column].str[5] == " ") & (
                                                        dataset[selected_column].str[9] == " ") & (
                                                    ~dataset[selected_column].str.contains("/", na=False)) & (
                                                    ~dataset[selected_column].str.contains("-", na=False))]
                d414 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 14) & (
                        dataset[selected_column].str[3:5] == "  ") & (
                                                        dataset[selected_column].str[8] == " ") & (
                                                        dataset[selected_column].str[11] == " ") & (
                                                    ~dataset[selected_column].str.contains("/", na=False)) & (
                                                    ~dataset[selected_column].str.contains("-", na=False))]
                d514 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 14) & (
                        dataset[selected_column].str[3] == " ") & (
                                                        dataset[selected_column].str[7] == " ") & (
                                                        dataset[selected_column].str[10:12] == "  ") & (
                                                    ~dataset[selected_column].str.contains("/", na=False)) & (
                                                    ~dataset[selected_column].str.contains("-", na=False))]
                d614 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 14) & (
                    dataset[selected_column].str.startswith("(", na=False)) & (
                                                        dataset[selected_column].str[4:6] == ") ") & (
                                                        dataset[selected_column].str[9] == "-") & (
                                                    ~dataset[selected_column].str.contains("/", na=False))]
                d714 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 14) & (
                    dataset[selected_column].str.startswith("(0", na=False)) & (
                                                        dataset[selected_column].str[5:7] == ") ") & (
                                                    ~dataset[selected_column].str.contains("/", na=False)) & (
                                                    ~dataset[selected_column].str.contains("-", na=False))]
                d814 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 14) & (
                    dataset[selected_column].str.startswith("0(", na=False)) & (
                                                        dataset[selected_column].str[5:7] == ") ") & (
                                                    ~dataset[selected_column].str.contains("/", na=False)) & (
                                                    ~dataset[selected_column].str.contains("-", na=False))]
                d914 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 14) & (
                    dataset[selected_column].str.startswith("90(", na=False)) & (
                                                        dataset[selected_column].str[6] == ")") & (
                                                    ~dataset[selected_column].str.contains("/", na=False)) & (
                                                    ~dataset[selected_column].str.contains("-", na=False)) & (
                                                    ~dataset[selected_column].str.contains(" ", na=False))]
                d1014 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 14) & (
                    dataset[selected_column].str.startswith("0", na=False)) & (
                                                         dataset[selected_column].str[4] == " ") & (
                                                     dataset[selected_column].str.endswith(" /", na=False)) & (
                                                     ~dataset[selected_column].str.contains("-", na=False))]
                d1114 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 14) & (
                    dataset[selected_column].str.startswith("0 (", na=False)) & (
                                                         dataset[selected_column].str[6] == ")") & (
                                                     ~dataset[selected_column].str.contains("-", na=False)) & (
                                                     ~dataset[selected_column].str.contains("/", na=False))]
                d1214 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 14) & (
                    dataset[selected_column].str.startswith("(", na=False)) & (
                                                         dataset[selected_column].str[4] == ")") & (
                                                         dataset[selected_column].str[8] == " ") & (
                                                         dataset[selected_column].str[11] == " ") & (
                                                     ~dataset[selected_column].str.contains("-", na=False)) & (
                                                     ~dataset[selected_column].str.contains("/", na=False))]
                d1314 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 14) & (
                    dataset[selected_column].str.startswith("0", na=False)) & (
                                                         dataset[selected_column].str[4] == "-") & (
                                                         dataset[selected_column].str[8] == " ") & (
                                                         dataset[selected_column].str[11] == " ") & (
                                                     ~dataset[selected_column].str.contains("/", na=False))]
                d1414 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 14) & (
                    dataset[selected_column].str.startswith("0", na=False)) & (
                                                         dataset[selected_column].str[4] == "-") & (
                                                         dataset[selected_column].str[8] == "-") & (
                                                         dataset[selected_column].str[11] == "-") & (
                                                     ~dataset[selected_column].str.contains("/", na=False)) & (
                                                     ~dataset[selected_column].str.contains(" ", na=False))]
                d1514 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 14) & (
                    dataset[selected_column].str.startswith("0", na=False)) & (
                                                         dataset[selected_column].str[4] == ")") & (
                                                         dataset[selected_column].str[8] == " ") & (
                                                         dataset[selected_column].str[11] == " ") & (
                                                     ~dataset[selected_column].str.contains("/", na=False)) & (
                                                     ~dataset[selected_column].str.contains("-", na=False))]
                d1614 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 14) & (
                    dataset[selected_column].str.startswith("(", na=False)) & (
                                                         dataset[selected_column].str[4:6] == ") ") & (
                                                         dataset[selected_column].str[9] == " ") & (
                                                     ~dataset[selected_column].str.contains("/", na=False)) & (
                                                     ~dataset[selected_column].str.contains("-", na=False))]
                d1714 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 14) & (
                    dataset[selected_column].str.startswith("0 ", na=False)) & (
                                                         dataset[selected_column].str[8] == " ") & (
                                                         dataset[selected_column].str[11] == " ") & (
                                                     ~dataset[selected_column].str.contains("/", na=False)) & (
                                                     ~dataset[selected_column].str.contains("-", na=False))]
                d1814 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 14) & (
                    dataset[selected_column].str.startswith("0", na=False)) & (
                                                         dataset[selected_column].str[4] == " ") & (
                                                         dataset[selected_column].str[6] == " ") & (
                                                         dataset[selected_column].str[9] == " ") & (
                                                     ~dataset[selected_column].str.contains("/", na=False)) & (
                                                     ~dataset[selected_column].str.contains("-", na=False))]
                d1914 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 14) & (
                    dataset[selected_column].str.startswith("0", na=False)) & (
                                                         dataset[selected_column].str[4] == " ") & (
                                                         dataset[selected_column].str[8] == " ") & (
                                                         dataset[selected_column].str[10] == " ") & (
                                                     ~dataset[selected_column].str.contains("/", na=False)) & (
                                                     ~dataset[selected_column].str.contains("-", na=False))]
                d2014 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 14) & (
                    dataset[selected_column].str.startswith("0", na=False)) & (
                                                         dataset[selected_column].str[4] == " ") & (
                                                         dataset[selected_column].str[8] == "-") & (
                                                         dataset[selected_column].str[11] == "-") & (
                                                     ~dataset[selected_column].str.contains("/", na=False))]

                d115 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 15) & (
                    dataset[selected_column].str.startswith("0", na=False)) & (
                                                        dataset[selected_column].str[1] == " ") & (
                                                        dataset[selected_column].str[5] == " ") & (
                                                        dataset[selected_column].str[10] == " ") & (
                                                        dataset[selected_column].str[13] == " ")]
                d215 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 15) & (
                    dataset[selected_column].str.startswith("0 ", na=False)) & (
                                                        dataset[selected_column].str[5] == " ") & (
                                                        dataset[selected_column].str[9] == " ") & (
                                                        dataset[selected_column].str[12] == " ") & (
                                                    ~dataset[selected_column].str.contains("/", na=False)) & (
                                                    ~dataset[selected_column].str.contains("-", na=False))]
                d315 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 15) & (
                        dataset[selected_column].str[3:5] == "  ") & (
                                                        dataset[selected_column].str[8] == " ") & (
                                                        dataset[selected_column].str[11:13] == "  ") & (
                                                    ~dataset[selected_column].str.contains("/", na=False)) & (
                                                    ~dataset[selected_column].str.contains("-", na=False))]
                d415 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 15) & (
                    dataset[selected_column].str.startswith("0", na=False)) & (
                                                        dataset[selected_column].str[4] == " ") & (
                                                        dataset[selected_column].str[8] == " ") & (
                                                        dataset[selected_column].str[11:13] == "  ") & (
                                                    ~dataset[selected_column].str.contains("/", na=False)) & (
                                                    ~dataset[selected_column].str.contains("-", na=False))]
                d515 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 15) & (
                    dataset[selected_column].str.startswith("0(", na=False)) & (
                                                        dataset[selected_column].str[5:7] == ") ") & (
                                                        dataset[selected_column].str[10] == " ") & (
                                                    ~dataset[selected_column].str.contains("/", na=False)) & (
                                                    ~dataset[selected_column].str.contains("-", na=False))]
                d615 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 15) & (
                        dataset[selected_column].str[3:6] == " / ") & (
                                                        dataset[selected_column].str[9] == " ") & (
                                                        dataset[selected_column].str[12] == " ") & (
                                                    ~dataset[selected_column].str.contains("-", na=False))]
                d715 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 15) & (
                    dataset[selected_column].str.startswith("0 ", na=False)) & (
                                                        dataset[selected_column].str[5] == " ") & (
                                                        dataset[selected_column].str[8] == " ") & (
                                                        dataset[selected_column].str[11] == " ") & (
                                                    ~dataset[selected_column].str.contains("/", na=False)) & (
                                                    ~dataset[selected_column].str.contains("-", na=False))]
                d815 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 15) & (
                    dataset[selected_column].str.startswith("0", na=False)) & (
                                                        dataset[selected_column].str[4:6] == "- ") & (
                                                        dataset[selected_column].str[9] == " ") & (
                                                        dataset[selected_column].str[12] == " ") & (
                                                    ~dataset[selected_column].str.contains("/", na=False))]
                d915 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 15) & (
                    dataset[selected_column].str.startswith("0", na=False)) & (
                                                        dataset[selected_column].str[4:6] == "  ") & (
                                                        dataset[selected_column].str[9] == " ") & (
                                                        dataset[selected_column].str[12] == " ") & (
                                                    ~dataset[selected_column].str.contains("/", na=False)) & (
                                                    ~dataset[selected_column].str.contains("-", na=False))]
                d1015 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 15) & (
                    dataset[selected_column].str.startswith("0 (", na=False)) & (
                                                         dataset[selected_column].str[6:8] == ") ") & (
                                                     ~dataset[selected_column].str.contains("/", na=False)) & (
                                                     ~dataset[selected_column].str.contains("-", na=False))]
                d1115 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 15) & (
                    dataset[selected_column].str.startswith("(0", na=False)) & (
                                                         dataset[selected_column].str[5:7] == ") ") & (
                                                         dataset[selected_column].str[10] == " ") & (
                                                     ~dataset[selected_column].str.contains("/", na=False)) & (
                                                     ~dataset[selected_column].str.contains("-", na=False))]
                d1215 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 15) & (
                    dataset[selected_column].str.startswith("0-", na=False)) & (
                                                         dataset[selected_column].str[5] == "-") & (
                                                         dataset[selected_column].str[9] == "-") & (
                                                         dataset[selected_column].str[12] == "-") & (
                                                     ~dataset[selected_column].str.contains("/", na=False)) & (
                                                     ~dataset[selected_column].str.contains(" ", na=False))]
                d1315 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 15) & (
                    dataset[selected_column].str.startswith("(", na=False)) & (
                                                         dataset[selected_column].str[4:6] == ") ") & (
                                                         dataset[selected_column].str[9] == " ") & (
                                                         dataset[selected_column].str[12] == " ") & (
                                                     ~dataset[selected_column].str.contains("/", na=False)) & (
                                                     ~dataset[selected_column].str.contains("-", na=False))]
                d1415 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 15) & (
                    dataset[selected_column].str.startswith("90 ", na=False)) & (
                                                         dataset[selected_column].str[6] == " ") & (
                                                         dataset[selected_column].str[10] == " ") & (
                                                     ~dataset[selected_column].str.contains("/", na=False)) & (
                                                     ~dataset[selected_column].str.contains("-", na=False))]
                d1515 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 15) & (
                    dataset[selected_column].str.startswith("0", na=False)) & (
                                                         dataset[selected_column].str[4:6] == ") ") & (
                                                         dataset[selected_column].str[9] == " ") & (
                                                         dataset[selected_column].str[12] == " ") & (
                                                     ~dataset[selected_column].str.contains("/", na=False)) & (
                                                     ~dataset[selected_column].str.contains("-", na=False))]
                d1615 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 15) & (
                    dataset[selected_column].str.startswith("0-", na=False)) & (
                                                         dataset[selected_column].str[5] == " ") & (
                                                         dataset[selected_column].str[9] == " ") & (
                                                         dataset[selected_column].str[12] == " ") & (
                                                     ~dataset[selected_column].str.contains("/", na=False))]
                d1715 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 15) & (
                    dataset[selected_column].str.startswith("0", na=False)) & (
                                                         dataset[selected_column].str[4] == " ") & (
                                                         dataset[selected_column].str[8:10] == "  ") & (
                                                         dataset[selected_column].str[12] == " ") & (
                                                     ~dataset[selected_column].str.contains("/", na=False)) & (
                                                     ~dataset[selected_column].str.contains("-", na=False))]
                d1815 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 15) & (
                    dataset[selected_column].str.startswith("0-", na=False)) & (
                                                         dataset[selected_column].str[5] == "-") & (
                                                         dataset[selected_column].str[9] == " ") & (
                                                         dataset[selected_column].str[12] == " ") & (
                                                     ~dataset[selected_column].str.contains("/", na=False))]

                d116 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 16) & (
                    dataset[selected_column].str.startswith("(0", na=False)) & (
                                                        dataset[selected_column].str[5:7] == ") ") & (
                                                        dataset[selected_column].str[10] == " ") & (
                                                        dataset[selected_column].str[13] == " ")]
                d216 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 16) & (
                    dataset[selected_column].str.startswith("+90 ", na=False)) & (
                                                        dataset[selected_column].str[7] == " ") & (
                                                        dataset[selected_column].str[11] == " ")]
                d316 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 16) & (
                    dataset[selected_column].str.startswith("0(", na=False)) & (
                                                        dataset[selected_column].str[5:7] == ") ") & (
                                                        dataset[selected_column].str[10] == " ") & (
                                                        dataset[selected_column].str[13] == " ")]
                d416 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 16) & (
                    dataset[selected_column].str.startswith("0 ", na=False)) & (
                                                        dataset[selected_column].str[5] == " ") & (
                                                        dataset[selected_column].str[9:11] == "  ") & (
                                                        dataset[selected_column].str[13] == " ")]
                d516 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 16) & (
                    dataset[selected_column].str.startswith("0  ", na=False)) & (
                                                        dataset[selected_column].str[6] == " ") & (
                                                        dataset[selected_column].str[10] == " ") & (
                                                        dataset[selected_column].str[13] == " ")]
                d616 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 16) & (
                    dataset[selected_column].str.startswith("90)(", na=False)) & (
                                                        dataset[selected_column].str[7:9] == ") ") & (
                                                    ~dataset[selected_column].str.contains("/", na=False)) & (
                                                    ~dataset[selected_column].str.contains("-", na=False))]
                d716 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 16) & (
                    dataset[selected_column].str.startswith("0090 ", na=False)) & (
                                                        dataset[selected_column].str[8] == " ") & (
                                                    ~dataset[selected_column].str.contains("/", na=False)) & (
                                                    ~dataset[selected_column].str.contains("-", na=False))]
                d816 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 16) & (
                    dataset[selected_column].str.startswith("90 ", na=False)) & (
                                                        dataset[selected_column].str[6] == " ") & (
                                                        dataset[selected_column].str[10] == " ") & (
                                                        dataset[selected_column].str[12] == " ") & (
                                                    ~dataset[selected_column].str.contains("/", na=False)) & (
                                                    ~dataset[selected_column].str.contains("-", na=False))]
                d916 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 16) & (
                    dataset[selected_column].str.startswith("90 ", na=False)) & (
                                                        dataset[selected_column].str[6] == " ") & (
                                                        dataset[selected_column].str[9] == " ") & (
                                                        dataset[selected_column].str[12] == " ") & (
                                                    ~dataset[selected_column].str.contains("/", na=False)) & (
                                                    ~dataset[selected_column].str.contains("-", na=False))]
                d1016 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 16) & (
                    dataset[selected_column].str.startswith("0 (", na=False)) & (
                                                         dataset[selected_column].str[6:8] == ") ") & (
                                                         dataset[selected_column].str[11] == " ") & (
                                                     ~dataset[selected_column].str.contains("/", na=False)) & (
                                                     ~dataset[selected_column].str.contains("-", na=False))]
                d1116 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 16) & (
                    dataset[selected_column].str.startswith("90 ", na=False)) & (
                                                         dataset[selected_column].str[6] == " ") & (
                                                         dataset[selected_column].str[10] == " ") & (
                                                         dataset[selected_column].str[13] == " ") & (
                                                     ~dataset[selected_column].str.contains("/", na=False)) & (
                                                     ~dataset[selected_column].str.contains("-", na=False))]
                d1216 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 16) & (
                    dataset[selected_column].str.startswith("0 ", na=False)) & (
                                                         dataset[selected_column].str[5] == " ") & (
                                                         dataset[selected_column].str[9:11] == "  ") & (
                                                         dataset[selected_column].str[13] == " ") & (
                                                     ~dataset[selected_column].str.contains("/", na=False)) & (
                                                     ~dataset[selected_column].str.contains("-", na=False))]

                d117 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 17) & (
                    dataset[selected_column].str.startswith("0 (", na=False)) & (
                                                        dataset[selected_column].str[6:8] == ") ") & (
                                                        dataset[selected_column].str[11] == " ") & (
                                                        dataset[selected_column].str[14] == " ")]
                d217 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 17) & (
                    dataset[selected_column].str.startswith("(0 ", na=False)) & (
                                                        dataset[selected_column].str[6:8] == ") ") & (
                                                        dataset[selected_column].str[11] == " ") & (
                                                        dataset[selected_column].str[14] == " ")]
                d317 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 17) & (
                    dataset[selected_column].str.startswith("+90 ", na=False)) & (
                                                        dataset[selected_column].str[7] == " ") & (
                                                        dataset[selected_column].str[11] == " ") & (
                                                        dataset[selected_column].str[14] == " ")]

                d118 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 18) & (
                    dataset[selected_column].str.startswith("( 0", na=False)) & (
                                                        dataset[selected_column].str[6:9] == " ) ") & (
                                                        dataset[selected_column].str[12] == " ") & (
                                                        dataset[selected_column].str[15] == " ")]

                d119 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 19) & (
                    dataset[selected_column].str.startswith("+90 (", na=False)) & (
                                                        dataset[selected_column].str[8:10] == ") ") & (
                                                        dataset[selected_column].str[13] == " ") & (
                                                        dataset[selected_column].str[16] == " ")]

                y10 = dataset[selected_column][(dataset[selected_column].astype(str).map(len) == 10) & (
                        (dataset[selected_column].str.startswith("0", na=False)) | (
                    dataset[selected_column].str.contains("/", na=False)) | (
                            dataset[selected_column].str.contains("-", na=False)) | (
                            dataset[selected_column].str.contains(" ", na=False)) | (
                            dataset[selected_column].str.contains("\)", na=False)) | (
                            dataset[selected_column].str.contains("\(", na=False)))]
                dummy = ["000 00 00", "111 11 11", "222 22 22", "333 33 33", "444 44 44", "555 55 55",
                         "666 66 66",
                         "777 77 77", "888 88 88", "999 99 99", "000000", "111111", "222222", "333333",
                         "444444", "555555",
                         "666666", "777777", "888888", "999999", "12345", "23456", "34567", "45678", "56789",
                         "67890",
                         "09876", "98765", "87654", "76543", "65432", "54321"]
                dum = dataset[selected_column][dataset[selected_column].str.contains('|'.join(dummy), na=False)]
                invalid = dataset[selected_column][
                    (dataset[selected_column].astype(str).map(len) < 10) | dataset[
                        selected_column].str.contains('[A-Za-z]', na=False)]
                yothers = dataset[selected_column][(dataset[selected_column].astype(str).map(len) > 10)]
                prob = (pd.concat(
                    [d111, d211, d311, d411, d112, d212, d312, d412, d512, d612, d712, d812, d912, d1012, d1112,
                     d1212, d1312, d113, d213, d313, d413, d513, d613, d713, d813, d913, d1013, d1113, d1213,
                     d1313, d1413, d1513, d1613, d1713, d1813, d1913, d114, d214, d314, d414, d514, d614, d714,
                     d814, d914, d1014, d1114, d1214, d1314, d1414, d1514, d1614, d1714, d1814, d1914, d2014,
                     d115, d215, d315, d415, d515, d615, d715, d815, d915, d1015, d1115, d1215, d1315, d1415,
                     d1515, d1615, d1715, d1815, d116, d216, d316, d416, d516, d616, d716, d816, d916, d1016,
                     d1116, d1216, d117, d217, d317, d118, d119, y10, dum, invalid, yothers],
                    ignore_index=False, sort=False).drop_duplicates(
                    keep='first')).dropna()
                probforgraph = (pd.concat(
                    [d111, d211, d311, d411, d112, d212, d312, d412, d512, d612, d712, d812, d912, d1012, d1112,
                     d1212, d1312, d113, d213, d313, d413, d513, d613, d713, d813, d913, d1013, d1113, d1213,
                     d1313, d1413, d1513, d1613, d1713, d1813, d1913, d114, d214, d314, d414, d514, d614, d714,
                     d814, d914, d1014, d1114, d1214, d1314, d1414, d1514, d1614, d1714, d1814, d1914, d2014,
                     d115, d215, d315, d415, d515, d615, d715, d815, d915, d1015, d1115, d1215, d1315, d1415,
                     d1515, d1615, d1715, d1815, d116, d216, d316, d416, d516, d616, d716, d816, d916, d1016,
                     d1116, d1216, d117, d217, d317, d118, d119, y10, dum, invalid, yothers],
                    ignore_index=False, sort=False).dropna())
                nofr = probforgraph.groupby(probforgraph.index).first()
                NOFR = nofr.shape[0]
                cols = st.beta_columns(2)
                with cols[1]:
                    st.write("Records that do not match with the quality rules defined for Telefon No:", prob)
                goodJob = pd.concat([dataset[selected_column], prob]).drop_duplicates(keep=False)
                with cols[0]:
                    st.write("Records with no data quality problems detected:", goodJob.astype('object'))

            PFR = (dataset[selected_column].shape[0]) - (nanCount + NOFR)
            dqst = pd.DataFrame([["Null Records", nanCount],
                                 ["Out of Format Records", NOFR],
                                 ["Proper Format Records", PFR]],
                                    columns=["Records Type", "Number of Records"])
            st.write("----")
            dq_score = round((PFR / dataset[selected_column].shape[0] * 100), 2)
            table = st.selectbox("Add to", ["'Before' Summary Table", "'After' Summary Table"], key = "add_st")
            insert = st.button("Insert", key="insert")
            if table == "'Before' Summary Table":
                if insert:
                    before.loc[len(before)] = [selected_column, nanCount, NOFR, PFR, dq_score]
                    st.session_state.beforeSS = before
                    st.success("Values have been added to 'Before' Summary Table.")
            elif table == "'After' Summary Table":
                if insert:
                    after.loc[len(after)] = [selected_column, nanCount, NOFR, PFR, dq_score]
                    st.session_state.afterSS = after
                    st.success("Values have been added to 'After' Summary Table.")

            st.subheader("Data Quality Measurement Results for {}".format(selected_column))
            st.write("")
            cols = st.beta_columns((2, 1))
            with cols[0]:
                rtypes = list(dqst["Records Type"])
                noR = list(dqst["Number of Records"])
                fig = plt.figure(figsize=(10, 6))
                # creating the bar plot
                plt.bar(rtypes, noR, color='#023047',
                        width=0.4)

                def addlabels(x, y):
                    for i in range(len(x)):
                        plt.text(i, y[i] + 2, y[i], ha='center', size='large')

                addlabels(rtypes, noR)
                ax = plt.gca()
                ax.tick_params(axis='both', which='major', labelsize=13)
                plt.ylabel("No. of Records")
                plt.title("Summary Graph")
                plt.show()
                st.pyplot(fig)

            if dq_score <= 25:
                a = 1
            elif dq_score > 25 and dq_score <= 50:
                a = 2
            elif dq_score > 50 and dq_score <= 75:
                a = 3
            else:
                a = 4

            dq_score_str = str(dq_score) + "%"
            with cols[1]:


                gauge(labels=['VERY LOW', 'LOW', 'MEDIUM', 'HIGH'], \
                      colors=["#1b0203", "#ED1C24", '#FFCC00', '#007A00'], arrow=a, title=dq_score_str)
                plt.title("Column DQ Score", fontsize=20)
                st.pyplot()




    elif task == "Data Corrector":
        st.write("")
        expanderForSearch = st.beta_expander("Run Search Engine", expanded=False)
        with expanderForSearch:
            if st.checkbox(label="value-based search", key="searchValue"):
                col_forSearch = st.text_input("Column")
                try:
                    if (dataset[col_forSearch].dtype == np.int16 or dataset[
                        col_forSearch].dtype == np.int32 or
                            dataset[col_forSearch].dtype == np.int64):
                        searchQualification = st.selectbox("Select Qualification",
                                                           ["Equals", "Greater than or equal to", "Less than",
                                                            "Between"])
                        if searchQualification == "Equals":
                            intValue = st.number_input("Value", format="%i", value=0,
                                                       min_value=-5000000000,
                                                       max_value=5000000000, step=1)
                            if st.button(label="Search", key="forSearchingint1"):
                                st.write(str('{:,}'.format(dataset[dataset[col_forSearch] == intValue].shape[0])), "results:",
                                         dataset[dataset[col_forSearch] == intValue])

                        elif searchQualification == "Greater than or equal to":
                            intValue = st.number_input("Value", format="%i", value=0,
                                                       min_value=-5000000000,
                                                       max_value=5000000000, step=1)
                            if st.button(label="Search", key="forSearchingint2"):
                                st.write(str('{:,}'.format(dataset[dataset[col_forSearch] >= intValue].shape[0])), "results:",
                                         dataset[dataset[col_forSearch] >= intValue])

                        elif searchQualification == "Less than":
                            intValue = st.number_input("Value", format="%i", value=0,
                                                       min_value=-5000000000,
                                                       max_value=5000000000, step=1)
                            if st.button(label="Search", key="forSearchingint3"):
                                st.write(str('{:,}'.format(dataset[dataset[col_forSearch] < intValue].shape[0])), "results:",
                                         dataset[dataset[col_forSearch] < intValue])


                        elif searchQualification == "Between":
                            cols = st.beta_columns((2, 1, 1, 1, 2))
                            with cols[0]:
                                intValue1 = st.number_input("Value1", format="%i", value=0,
                                                            min_value=-5000000000, max_value=5000000000,
                                                            step=1)
                            with cols[2]:
                                st.write("AND")
                            with cols[4]:
                                intValue2 = st.number_input("Value2", format="%i", value=0,
                                                            min_value=-5000000000, max_value=5000000000,
                                                            step=1)
                            if st.button(label="Search", key="forSearchingint4"):
                                st.write(str('{:,}'.format(dataset[((dataset[col_forSearch] >= intValue1) & (
                                                 dataset[col_forSearch] <= intValue2))].shape[0])), "results:",
                                         dataset[((dataset[col_forSearch] >= intValue1) & (
                                                 dataset[col_forSearch] <= intValue2))])

                    elif (dataset[col_forSearch].dtype == np.float16 or dataset[
                        col_forSearch].dtype == np.float32 or
                          dataset[col_forSearch].dtype == np.float64):
                        searchQualification = st.selectbox("Select Qualification",
                                                           ["Equals", "Greater than or equal to", "Less than",
                                                            "Between"])
                        if searchQualification == "Equals":
                            fltValue = st.number_input("Value", format="%f", value=0.0,
                                                       min_value=-5000000000.0,
                                                       max_value=5000000000.0, step=0.01)
                            if st.button(label="Search", key="forSearchingfloat1"):
                                st.write(str('{:,}'.format(dataset[dataset[col_forSearch] == fltValue].shape[0])), "results:",
                                         dataset[dataset[col_forSearch] == fltValue])

                        elif searchQualification == "Greater than or equal to":
                            fltValue = st.number_input("Value", format="%f", value=0.0,
                                                       min_value=-5000000000.0,
                                                       max_value=5000000000.0, step=0.01)
                            if st.button(label="Search", key="forSearchingfloat2"):
                                st.write(str('{:,}'.format(dataset[dataset[col_forSearch] >= fltValue].shape[0])), "results:",
                                         dataset[dataset[col_forSearch] >= fltValue])

                        elif searchQualification == "Less than":
                            fltValue = st.number_input("Value", format="%f", value=0.0,
                                                       min_value=-5000000000.0,
                                                       max_value=5000000000.0, step=0.01)
                            if st.button(label="Search", key="forSearchingfloat3"):
                                st.write(str('{:,}'.format(dataset[dataset[col_forSearch] < fltValue].shape[0])), "results:",
                                         dataset[dataset[col_forSearch] < fltValue])

                        elif searchQualification == "Between":
                            cols = st.beta_columns((2, 1, 1, 1, 2))
                            with cols[0]:
                                fltValue1 = st.number_input("Value1", format="%f", value=0.0,
                                                            min_value=-5000000000.0, max_value=5000000000.0,
                                                            step=0.01)
                            with cols[2]:
                                st.write("AND")
                            with cols[4]:
                                fltValue2 = st.number_input("Value2", format="%f", value=0.0,
                                                            min_value=-5000000000.0, max_value=5000000000.0,
                                                            step=0.01)
                            if st.button(label="Search", key="forSearchingfloat4"):
                                st.write(str('{:,}'.format(dataset[((dataset[col_forSearch] >= fltValue1) & (
                                                 dataset[col_forSearch] <= fltValue2))].shape[0])), "results:",
                                         dataset[((dataset[col_forSearch] >= fltValue1) & (
                                                 dataset[col_forSearch] <= fltValue2))])

                    elif dataset[col_forSearch].dtype.name == 'datetime64[ns]':
                        searchQualification = st.selectbox("Select Qualification", ["Equals", "Greater than or equal to", "Less than", "Between"])
                        if searchQualification == "Equals":
                            dateValue = st.date_input("Value", value=datetime.date.today(),
                                                 min_value=datetime.date.today() - relativedelta(years=125),
                                                 max_value=datetime.date.today() + relativedelta(years=35))
                            if st.button(label="Search", key="forSearchingDate1"):
                                st.write(
                                    str('{:,}'.format(dataset[dataset[col_forSearch] == pd.to_datetime(dateValue)].shape[0])),
                                    "results:",
                                    dataset[dataset[col_forSearch] == pd.to_datetime(dateValue)])

                        elif searchQualification == "Greater than or equal to":
                            dateValue = st.date_input("Value", value=datetime.date.today(),
                                                      min_value=datetime.date.today() - relativedelta(
                                                          years=125),
                                                      max_value=datetime.date.today() + relativedelta(years=35))
                            if st.button(label="Search", key="forSearchingDate2"):
                                st.write(
                                    str('{:,}'.format(dataset[dataset[col_forSearch] >= pd.to_datetime(dateValue)].shape[0])),
                                    "results:",
                                    dataset[dataset[col_forSearch] >= pd.to_datetime(dateValue)])

                        elif searchQualification == "Less than":
                            dateValue = st.date_input("Value", value=datetime.date.today(),
                                                      min_value=datetime.date.today() - relativedelta(
                                                          years=125),
                                                      max_value=datetime.date.today() + relativedelta(years=35))
                            if st.button(label="Search", key="forSearchingDate3"):
                                st.write(
                                    str('{:,}'.format(dataset[dataset[col_forSearch] < pd.to_datetime(dateValue)].shape[0])),
                                    "results:",
                                    dataset[dataset[col_forSearch] < pd.to_datetime(dateValue)])

                        elif searchQualification == "Between":
                            cols = st.beta_columns((2, 1, 1, 1, 2))
                            with cols[0]:
                                dateValue1 = st.date_input("Value1", value=datetime.date.today(),
                                                          min_value=datetime.date.today() - relativedelta(
                                                              years=125),
                                                          max_value=datetime.date.today() + relativedelta(
                                                              years=35))
                            with cols[2]:
                                st.write("AND")
                            with cols[4]:
                                dateValue2 = st.date_input("Value2", value=datetime.date.today(),
                                                          min_value=datetime.date.today() - relativedelta(
                                                              years=125),
                                                          max_value=datetime.date.today() + relativedelta(
                                                              years=35))
                            if st.button(label="Search", key="forSearchingDate4"):
                                st.write(str('{:,}'.format(dataset[((dataset[col_forSearch] >= pd.to_datetime(dateValue1)) & (
                                        dataset[col_forSearch] <= pd.to_datetime(dateValue2)))].shape[0])), "results:",
                                         dataset[((dataset[col_forSearch] >= pd.to_datetime(dateValue1)) & (
                                                 dataset[col_forSearch] <= pd.to_datetime(dateValue2)))])

                    else:
                        strValue = st.text_input("Value")
                        layo = st.beta_columns((2, 0.5, 3))
                        layou = st.beta_columns(1)
                        with layo[0]:
                            if st.button(label="Search", key="forSearching3"):
                                with layou[0]:
                                    st.write(str('{:,}'.format(dataset[dataset[col_forSearch] == strValue].shape[0])) ,"results:",
                                             dataset[dataset[col_forSearch] == strValue])
                        with layo[2]:
                            if st.button(label="Search NaN", key="forSearchingNaN"):
                                with layou[0]:
                                    st.write(str('{:,}'.format(dataset[dataset[col_forSearch].isnull()].shape[0])) ,"results:",
                                             dataset[dataset[col_forSearch].isnull()])
                except KeyError:
                    st.warning("You are awaited to enter the name of the column with the value you want to search.")

            if st.checkbox(label="index-based search"):
                idx = st.number_input("Index", format="%i", value=0, max_value=dataset.shape[0],
                                      step=1)
                if st.button(label="Search", key="forSearching4"):
                    st.write("Result:", dataset[dataset.index == idx])

        st.write("---")
        if st.checkbox(label="Run Edit Engine"):
            st.subheader("Edit Your Dataset")
            with st.form(key="edit_form_col"):
                colu = st.text_input("Edit by Column")
                if st.form_submit_button(label="Drop the Column"):
                    try:
                        dataset.drop(columns=[colu], axis=1, inplace=True)
                        st.success("The Column was deleted.")
                    except KeyError:
                        st.error("The Column was not found.")

            with st.form(key="edit_form_idx"):
                idx = st.number_input("Edit by Index", format="%i", value=0,
                                      max_value=dataset.index.max(), step=1)
                if st.form_submit_button(label="Drop the Row"):
                    try:
                        dataset.drop(index=idx, axis=0, inplace=True)
                        st.success("The Record was deleted.")
                    except KeyError:
                        st.error("The Index was not found.")

            my_expander = st.beta_expander("Edit Cells", expanded=False)
            with my_expander:
                coleditby = st.beta_columns((1, 3, 6))
                with coleditby[1]:
                    editBYindex = st.checkbox(label="Edit by Index")
                if editBYindex:
                    idx = st.number_input("Index", format="%i", value=0, max_value=dataset.shape[0],
                                          step=1)
                    column = st.text_input("Enter the column name of the cell you want to edit",
                                           key="column_for_editing_index")
                    try:
                        if (dataset[column].dtype == np.int16 or dataset[
                            column].dtype == np.int32 or
                                dataset[column].dtype == np.int64):
                            integerValue = st.number_input("Value", format="%i", value=0,
                                                           min_value=-5000000000,
                                                           max_value=5000000000, step=1)

                            lay = st.beta_columns((3, 4, 2))
                            with lay[0]:
                                if st.button("Alter the Cell"):
                                    dataset[column][idx] = integerValue
                                    st.success("The Value was changed.")
                            with lay[1]:
                                if st.button("Fill with NaN"):
                                    dataset[column][idx] = np.NaN
                                    st.success("The Cell was filled with NaN.")

                        elif (dataset[column].dtype == np.float16 or dataset[
                            column].dtype == np.float32 or
                              dataset[column].dtype == np.float64):
                            floatValue = st.number_input("Value", format="%f", value=0.0,
                                                         min_value=-5000000000.0,
                                                         max_value=5000000000.0, step=0.01)

                            lay = st.beta_columns((3, 4, 2))
                            with lay[0]:
                                if st.button("Alter the Cell"):
                                    dataset[column][idx] = floatValue
                                    st.success("The Value was changed.")
                            with lay[1]:
                                if st.button("Fill with NaN"):
                                    dataset[column][idx] = np.NaN
                                    st.success("The Cell was filled with NaN.")

                        elif dataset[column].dtype.name == 'datetime64[ns]':
                            dateValue = st.date_input("Value", value=datetime.date.today(), min_value=datetime.date.today()-relativedelta(years=125), max_value=datetime.date.today()+relativedelta(years=35), key="editingDate")
                            lay = st.beta_columns((3, 4, 2))
                            with lay[0]:
                                if st.button("Alter the Cell"):
                                    dataset[column][idx] = pd.to_datetime(dateValue)
                                    st.success("The Value was changed.")
                            with lay[1]:
                                if st.button("Fill with NaN"):
                                    dataset[column][idx] = np.NaN
                                    st.success("The Cell was filled with NaN.")

                        else:
                            stringValue = st.text_input("Value", key="value_for_editing_index")
                            lay = st.beta_columns((3, 4, 2))
                            with lay[0]:
                                if st.button("Alter the Cell", key="button_for_index"):
                                    dataset[column][idx] = stringValue
                                    st.success("The Value was changed.")
                            with lay[1]:
                                if st.button("Fill with NaN", key="button_for_idx_nan"):
                                    dataset[column][idx] = np.NaN
                                    st.success("The Cell was filled with NaN.")
                    except KeyError:
                        st.warning("You are awaited to enter the column name of the cell you want to change.")

                coleditby = st.beta_columns((1, 3, 6))
                with coleditby[1]:
                    editBYvalue = st.checkbox("Edit by Value")
                if editBYvalue:
                    column = st.text_input("Enter the column name of the cell you want to edit",
                                           key="column_for_editing_value")
                    try:
                        if (dataset[column].dtype == np.int16 or dataset[
                            column].dtype == np.int32 or
                                dataset[column].dtype == np.int64):
                            integerValue = st.number_input("old Value", format="%i", value=0,
                                                           min_value=-5000000000,
                                                           max_value=5000000000, step=1)
                            new_integerValue = st.number_input("new Value", format="%i", value=0,
                                                               min_value=-5000000000,
                                                               max_value=5000000000, step=1)
                            old = dataset[column][dataset[column] == integerValue].shape[0]
                            success_text1 = str(old) + " values were changed."
                            success_text2 = str(old) + " values were filled with NaN."
                            success_text3 = str(old) + " records were deleted."
                            lay = st.beta_columns((3, 4, 3))
                            with lay[0]:
                                if st.button("Alter the Cell"):
                                    dataset[column][dataset[column] == integerValue] = new_integerValue
                                    st.success(success_text1)
                            with lay[1]:
                                if st.button("Fill with NaN"):
                                    dataset[column][dataset[column] == integerValue] = np.NaN
                                    st.success(success_text2)
                            with lay[2]:
                                if st.button("Drop rows"):
                                    dataset.drop(index=dataset[dataset[column] == integerValue].index, inplace=True)
                                    st.success(success_text3)

                        elif (dataset[column].dtype == np.float16 or dataset[
                            column].dtype == np.float32 or
                              dataset[column].dtype == np.float64):
                            floatValue = st.number_input("old Value", format="%f", value=0.0,
                                                         min_value=-5000000000.0,
                                                         max_value=5000000000.0, step=0.01)
                            new_floatValue = st.number_input("new Value", format="%f", value=0.0,
                                                             min_value=-5000000000.0,
                                                             max_value=5000000000.0, step=0.01, key="newFloat")
                            old = dataset[column][dataset[column] == floatValue].shape[0]
                            success_text1 = str(old) + " values were changed."
                            success_text2 = str(old) + " values were filled with NaN."
                            success_text3 = str(old) + " records were deleted."
                            lay = st.beta_columns((3, 4, 3))
                            with lay[0]:
                                if st.button("Alter the Cell"):
                                    dataset[column][dataset[column] == floatValue] = new_floatValue
                                    st.success(success_text1)
                            with lay[1]:
                                if st.button("Fill with NaN"):
                                    dataset[column][dataset[column] == floatValue] = np.NaN
                                    st.success(success_text2)
                            with lay[2]:
                                if st.button("Drop rows"):
                                    dataset.drop(
                                        index=dataset[dataset[column] == floatValue].index,
                                        inplace=True)
                                    st.success(success_text3)

                        elif dataset[column].dtype.name == 'datetime64[ns]':
                            dateValue = st.date_input("old Value", value=datetime.date.today(), min_value=datetime.date.today()-relativedelta(years=125), max_value=datetime.date.today()+relativedelta(years=35), key="oldDate")
                            new_dateValue = st.date_input("new Value", value=datetime.date.today(), min_value=datetime.date.today()-relativedelta(years=125), max_value=datetime.date.today()+relativedelta(years=35), key="newDate")
                            old = dataset[column][dataset[column] == pd.to_datetime(dateValue)].shape[0]
                            success_text1 = str(old) + " values were changed."
                            success_text2 = str(old) + " values were filled with NaN."
                            success_text3 = str(old) + " records were deleted."
                            lay = st.beta_columns((3, 4, 3))
                            with lay[0]:
                                if st.button("Alter the Cell"):
                                    dataset[column][dataset[column] == pd.to_datetime(dateValue)] = pd.to_datetime(new_dateValue)
                                    st.success(success_text1)
                            with lay[1]:
                                if st.button("Fill with NaN"):
                                    dataset[column][dataset[column] == pd.to_datetime(dateValue)] = np.NaN
                                    st.success(success_text2)
                            with lay[2]:
                                if st.button("Drop rows"):
                                    dataset.drop(
                                        index=dataset[dataset[column] == pd.to_datetime(dateValue)].index,
                                        inplace=True)
                                    st.success(success_text3)

                        else:
                            stringValue = st.text_input("old Value")
                            new_stringValue = st.text_input("new Value", key="value_for_editing,value")
                            old = dataset[column][dataset[column] == stringValue].shape[0]
                            success_text1 = str(old) + " values were changed."
                            success_text2 = str(old) + " values were filled with NaN."
                            success_text3 = str(old) + " records were deleted."
                            lay = st.beta_columns((3, 4, 3))
                            with lay[0]:
                                if st.button("Alter the Cell", key="button_for_value"):
                                    dataset[column][dataset[column] == stringValue] = new_stringValue
                                    st.success(success_text1)
                            with lay[1]:
                                if st.button("Fill with NaN", key="button_for_nan"):
                                    dataset[column][dataset[column] == stringValue] = np.NaN
                                    st.success(success_text2)
                            with lay[2]:
                                if st.button("Drop rows"):
                                    dataset.drop(
                                        index=dataset[dataset[column] == stringValue].index,
                                        inplace=True)
                                    st.success(success_text3)

                    except KeyError:
                        st.warning("You are awaited to enter the column name of the cell you want to change.")

            convert_expander = st.beta_expander("Convert Values in a Column by Using String Methods",
                                                expanded=False)
            with convert_expander:
                obj_cols = dataset.select_dtypes(include=['object', 'category']).columns
                betacolumns1 = st.beta_columns((0.5, 6, 3.5))
                with betacolumns1[1]:
                    convert_toTitle = st.checkbox(
                        label="Convert the first character of each word to upper case, 'Aaa Aaaa'")
                if convert_toTitle:
                    selected_col = st.selectbox("Select the column with the values you want to convert", obj_cols,
                                                key="forTitle")
                    if st.button("Convert", key="button_for_convertingTitle"):
                        dataset[selected_col] = dataset[selected_col].str.title()
                        st.success("Values were converted.")

                betacolumns2 = st.beta_columns((0.5, 6, 3.5))
                with betacolumns2[1]:
                    convert_toLower = st.checkbox(label="Convert values into lower case, 'aaaaaaaa'")
                if convert_toLower:
                    selected_col = st.selectbox("Select the column with the values you want to convert", obj_cols,
                                                key="forLower")
                    if st.button("Convert", key="button_for_convertingLower"):
                        dataset[selected_col] = dataset[selected_col].str.lower()
                        st.success("Values were converted.")

                betacolumns3 = st.beta_columns((0.5, 6, 3.5))
                with betacolumns3[1]:
                    convert_toUpper = st.checkbox(label="Convert values into upper case, 'AAAAA AAAAAA'")
                if convert_toUpper:
                    selected_col = st.selectbox("Select the column with the values you want to convert", obj_cols,
                                                key="forUpper")
                    if st.button("Convert", key="button_for_convertingUpper"):
                        dataset[selected_col] = dataset[selected_col].str.upper()
                        st.success("Values were converted.")

                betacolumns4 = st.beta_columns((0.5, 6, 3.5))
                with betacolumns4[1]:
                    convert_to1space = st.checkbox(label="Remove multiple spaces")
                if convert_to1space:
                    selected_col = st.selectbox("Select the column with the values you want to convert", obj_cols,
                                                key="forSpace")
                    if st.button("Remove", key="button_for_removingSpace"):
                        dataset[selected_col] = dataset[selected_col].apply(
                            lambda x: re.sub(' +', ' ', str(x))).replace('nan', np.NaN)
                        st.success("Multispaces were removed.")

                betacolumns5 = st.beta_columns((0.5, 6, 3.5))
                with betacolumns5[1]:
                    strip = st.checkbox(label="Strip")
                if strip:
                    selected_col = st.selectbox("Select the column with the values you want to convert", obj_cols,
                                                key="forStrip")
                    strp = st.text_input("Value")
                    if st.button("Strip", key="button_for_Strip"):
                        dataset[selected_col] = dataset[selected_col].str.strip(strp)
                        st.success("Changes were applied.")

                betacolumns6 = st.beta_columns((0.5, 6, 3.5))
                with betacolumns6[1]:
                    replace = st.checkbox(label="Replace")
                if replace:
                    st.info("If you want to remove the value instead of replacing it with another value, type 'none'.")
                    selected_col = st.selectbox("Select the column with the values you want to change", obj_cols,
                                                key="forReplace")
                    cols = st.beta_columns((3, 2, 3))
                    with cols[0]:
                        val1 = st.text_input("Find what:")
                        if val1 == "(":
                            val1 = '\('
                        if val1 == "?":
                            val1 = '\?'
                        if val1 == "|":
                            val1 = '\|'
                        if val1 == '[':
                            val1 = '\['
                        if val1 == '+':
                            val1 = '\+'
                        if val1 == ')':
                            val1 = '\)'
                        if val1 == '*':
                            val1 = '\*'
                        if val1 == '^':
                            val1 = '\^'
                        if val1 == '$':
                            val1 = '\$'
                    with cols[2]:
                        valrep = st.text_input("Replace with:" )
                        if valrep == "none":
                            valrep = ""
                        if valrep == "(":
                            valrep = '\('
                        if valrep == "?":
                            valrep = '\?'
                        if valrep == "|":
                            valrep = '\|'
                        if valrep == '[':
                            valrep = '\['
                        if valrep == '+':
                            valrep = '\+'
                        if valrep == ')':
                            valrep = '\)'
                        if valrep == '*':
                            valrep = '\*'
                        if valrep == '^':
                            valrep = '\^'
                        if valrep == '$':
                            valrep = '\$'

                    if st.button("Replace", key="button_for_replace"):
                        countrep = dataset[selected_col].str.count(val1).sum()
                        dataset[selected_col] = dataset[selected_col].str.replace(val1, valrep)
                        success_text = str(int(countrep)) + " values were changed."
                        st.success(success_text)

                betacolumns5 = st.beta_columns((0.5, 9.5))
                with betacolumns5[1]:
                    strip = st.checkbox(label="Format Corrector for 'Telefon Numarası' (to reduce the character length of examples like '0XXXXXXXXXX' to 10)")
                if strip:
                    selected_col = st.selectbox("Select column with 'Telefon Numarası' values",
                                                obj_cols,
                                                key="forReducing")
                    first_char = st.text_input("Character")
                    if st.button("Remove", key="button_for_Reducing"):
                        dataset[selected_col] = dataset[selected_col].astype('str').apply(lambda x : x[1:] if x.startswith(first_char) else x).replace('nan', np.NaN)
                        st.success("Changes were applied.")

            enrich_expander = st.beta_expander("Enrich your Dataset",
                                               expanded=False)
            with enrich_expander:
                col_forEnriching = st.text_input("Enter the source column name to enrich",
                                                 key="column_for_enriching")
                try:
                    enrich_method = st.selectbox("What do you want to add to the dataset?",
                                                 ["Select", "Gender", "Age", "Anniversary", "Day", "Weekday", "Month", "Year", "Quarter", "WeekofYear", "Latitude - Longitude"])
                    button_forEnrich = st.button("Enrich", key="Enrich_data")
                    if (enrich_method == "Latitude - Longitude") and (button_forEnrich):
                        city_latitude_dict = {}
                        city_latitude_dict['Adana'] = 37.00167
                        city_latitude_dict['Adıyaman'] = 37.76441
                        city_latitude_dict['Afyon'] = 38.75667
                        city_latitude_dict['Ağrı'] = 39.71944
                        city_latitude_dict['Amasya'] = 40.65333
                        city_latitude_dict['Ankara'] = 39.91987
                        city_latitude_dict['Antalya'] = 36.90812
                        city_latitude_dict['Artvin'] = 41.18161
                        city_latitude_dict['Aydın'] = 37.84501
                        city_latitude_dict['Balıkesir'] = 39.64917
                        city_latitude_dict['Bilecik'] = 40.14192
                        city_latitude_dict['Bingöl'] = 38.88472
                        city_latitude_dict['Bitlis'] = 38.40115
                        city_latitude_dict['Bolu'] = 40.73583
                        city_latitude_dict['Burdur'] = 37.72028
                        city_latitude_dict['Bursa'] = 40.19266
                        city_latitude_dict['Çanakkale'] = 40.14556
                        city_latitude_dict['Çankırı'] = 40.536907
                        city_latitude_dict['Çorum'] = 40.54889
                        city_latitude_dict['Denizli'] = 37.77417
                        city_latitude_dict['Diyarbakır'] = 37.91363
                        city_latitude_dict['Edirne'] = 41.67719
                        city_latitude_dict['Elazığ'] = 38.67431
                        city_latitude_dict['Erzincan'] = 39.73919
                        city_latitude_dict['Erzurum'] = 39.90861
                        city_latitude_dict['Eskişehir'] = 39.77667
                        city_latitude_dict['Gaziantep'] = 37.05944
                        city_latitude_dict['Giresun'] = 40.91698
                        city_latitude_dict['Gümüşhane'] = 40.4562
                        city_latitude_dict['Hakkari'] = 37.57444
                        city_latitude_dict['Hatay'] = 36.200001
                        city_latitude_dict['Isparta'] = 37.762649
                        city_latitude_dict['İçel'] = 36.812104
                        city_latitude_dict['İstanbul'] = 41.01384
                        city_latitude_dict['İzmir'] = 38.41273
                        city_latitude_dict['Kars'] = 40.60199
                        city_latitude_dict['Kastamonu'] = 41.37805
                        city_latitude_dict['Kayseri'] = 38.73222
                        city_latitude_dict['Kırklareli'] = 41.73508
                        city_latitude_dict['Kırşehir'] = 39.14583
                        city_latitude_dict['Kocaeli'] = 40.85327
                        city_latitude_dict['Konya'] = 37.87135
                        city_latitude_dict['Kütahya'] = 39.42417
                        city_latitude_dict['Malatya'] = 38.35018
                        city_latitude_dict['Manisa'] = 38.61202
                        city_latitude_dict['Kahramanmaraş'] = 37.575275
                        city_latitude_dict['Mardin'] = 37.31309
                        city_latitude_dict['Muğla'] = 37.21807
                        city_latitude_dict['Muş'] = 38.73163
                        city_latitude_dict['Nevşehir'] = 38.625
                        city_latitude_dict['Niğde'] = 37.96583
                        city_latitude_dict['Ordu'] = 40.98472
                        city_latitude_dict['Rize'] = 41.02083
                        city_latitude_dict['Sakarya'] = 40.773074
                        city_latitude_dict['Samsun'] = 41.28667
                        city_latitude_dict['Siirt'] = 37.93262
                        city_latitude_dict['Sinop'] = 42.02683
                        city_latitude_dict['Sivas'] = 39.74833
                        city_latitude_dict['Tekirdağ'] = 40.97801
                        city_latitude_dict['Tokat'] = 40.31389
                        city_latitude_dict['Trabzon'] = 41.005
                        city_latitude_dict['Tunceli'] = 39.09921
                        city_latitude_dict['Şanlıurfa'] = 37.16708
                        city_latitude_dict['Uşak'] = 38.67351
                        city_latitude_dict['Van'] = 38.49457
                        city_latitude_dict['Yozgat'] = 39.82
                        city_latitude_dict['Zonguldak'] = 41.45139
                        city_latitude_dict['Aksaray'] = 38.37255
                        city_latitude_dict['Bayburt'] = 40.25631
                        city_latitude_dict['Karaman'] = 37.18111
                        city_latitude_dict['Kırıkkale'] = 39.84528
                        city_latitude_dict['Batman'] = 37.88738
                        city_latitude_dict['Şırnak'] = 37.51393
                        city_latitude_dict['Bartın'] = 41.63583
                        city_latitude_dict['Ardahan'] = 41.10871
                        city_latitude_dict['Iğdır'] = 39.920060
                        city_latitude_dict['Yalova'] = 40.65501
                        city_latitude_dict['Karabük'] = 41.20488
                        city_latitude_dict['Kilis'] = 36.71611
                        city_latitude_dict['Osmaniye'] = 37.07417
                        city_latitude_dict['Düzce'] = 40.83889

                        dataset[str('Latitude_' + col_forEnriching)] = dataset[col_forEnriching].apply(
                            lambda x: city_latitude_dict[x] if x in city_latitude_dict.keys() else x)

                        city_longitude_dict = {}
                        city_longitude_dict['Adana'] = 35.32889
                        city_longitude_dict['Adıyaman'] = 38.27629
                        city_longitude_dict['Afyon'] = 30.54333
                        city_longitude_dict['Ağrı'] = 43.05139
                        city_longitude_dict['Amasya'] = 35.83306
                        city_longitude_dict['Ankara'] = 32.85427
                        city_longitude_dict['Antalya'] = 30.69556
                        city_longitude_dict['Artvin'] = 41.82172
                        city_longitude_dict['Aydın'] = 27.83963
                        city_longitude_dict['Balıkesir'] = 27.88611
                        city_longitude_dict['Bilecik'] = 29.97932
                        city_longitude_dict['Bingöl'] = 40.49389
                        city_longitude_dict['Bitlis'] = 42.10784
                        city_longitude_dict['Bolu'] = 31.60611
                        city_longitude_dict['Burdur'] = 30.29083
                        city_longitude_dict['Bursa'] = 29.08403
                        city_longitude_dict['Çanakkale'] = 26.40639
                        city_longitude_dict['Çankırı'] = 33.588389
                        city_longitude_dict['Çorum'] = 34.95333
                        city_longitude_dict['Denizli'] = 29.0875
                        city_longitude_dict['Diyarbakır'] = 40.21721
                        city_longitude_dict['Edirne'] = 26.55597
                        city_longitude_dict['Elazığ'] = 39.22321
                        city_longitude_dict['Erzincan'] = 39.49015
                        city_longitude_dict['Erzurum'] = 41.27694
                        city_longitude_dict['Eskişehir'] = 30.52056
                        city_longitude_dict['Gaziantep'] = 37.3825
                        city_longitude_dict['Giresun'] = 38.38741
                        city_longitude_dict['Gümüşhane'] = 39.4755
                        city_longitude_dict['Hakkari'] = 43.74083
                        city_longitude_dict['Hatay'] = 36.166668
                        city_longitude_dict['Isparta'] = 30.553705
                        city_longitude_dict['İçel'] = 34.641481
                        city_longitude_dict['İstanbul'] = 28.94966
                        city_longitude_dict['İzmir'] = 27.13838
                        city_longitude_dict['Kars'] = 43.09495
                        city_longitude_dict['Kastamonu'] = 33.77528
                        city_longitude_dict['Kayseri'] = 35.48528
                        city_longitude_dict['Kırklareli'] = 27.22521
                        city_longitude_dict['Kırşehir'] = 34.16389
                        city_longitude_dict['Kocaeli'] = 29.88152
                        city_longitude_dict['Konya'] = 32.48464
                        city_longitude_dict['Kütahya'] = 29.98333
                        city_longitude_dict['Malatya'] = 38.31667
                        city_longitude_dict['Manisa'] = 27.42647
                        city_longitude_dict['Kahramanmaraş'] = 36.922822
                        city_longitude_dict['Mardin'] = 40.74357
                        city_longitude_dict['Muğla'] = 28.3665
                        city_longitude_dict['Muş'] = 41.48482
                        city_longitude_dict['Nevşehir'] = 34.71222
                        city_longitude_dict['Niğde'] = 34.67935
                        city_longitude_dict['Ordu'] = 37.87889
                        city_longitude_dict['Rize'] = 40.52194
                        city_longitude_dict['Sakarya'] = 30.394817
                        city_longitude_dict['Samsun'] = 36.33
                        city_longitude_dict['Siirt'] = 41.94025
                        city_longitude_dict['Sinop'] = 35.16253
                        city_longitude_dict['Sivas'] = 37.01611
                        city_longitude_dict['Tekirdağ'] = 27.50852
                        city_longitude_dict['Tokat'] = 36.55444
                        city_longitude_dict['Trabzon'] = 39.72694
                        city_longitude_dict['Tunceli'] = 39.54351
                        city_longitude_dict['Şanlıurfa'] = 38.79392
                        city_longitude_dict['Uşak'] = 29.4058
                        city_longitude_dict['Van'] = 43.38323
                        city_longitude_dict['Yozgat'] = 34.80444
                        city_longitude_dict['Zonguldak'] = 31.79305
                        city_longitude_dict['Aksaray'] = 34.02537
                        city_longitude_dict['Bayburt'] = 40.22289
                        city_longitude_dict['Karaman'] = 33.215
                        city_longitude_dict['Kırıkkale'] = 33.50639
                        city_longitude_dict['Batman'] = 41.13221
                        city_longitude_dict['Şırnak'] = 42.45432
                        city_longitude_dict['Bartın'] = 32.3375
                        city_longitude_dict['Ardahan'] = 42.70222
                        city_longitude_dict['Iğdır'] = 44.043615
                        city_longitude_dict['Yalova'] = 29.27693
                        city_longitude_dict['Karabük'] = 32.62768
                        city_longitude_dict['Kilis'] = 37.115
                        city_longitude_dict['Osmaniye'] = 36.24778
                        city_longitude_dict['Düzce'] = 31.16389

                        dataset[str('Longitude_' + col_forEnriching)] = dataset[col_forEnriching].apply(
                            lambda x: city_longitude_dict[x] if x in city_longitude_dict.keys() else x)
                        st.success("Your Dataset was enriched with Latitude and Longitude info.")

                    if (enrich_method == "Age") and (button_forEnrich):
                        try:
                            now = pd.Timestamp('now')
                            dataset[col_forEnriching] = pd.to_datetime(dataset[col_forEnriching],
                                                                       format='%d%m%Y')  # 1
                            dataset[col_forEnriching] = dataset[col_forEnriching].where(
                                dataset[col_forEnriching] < now,
                                dataset[col_forEnriching] - np.timedelta64(100, 'Y'))  # 2
                            dataset[str('Age_'+col_forEnriching)] = (now - dataset[col_forEnriching]).astype(
                                '<m8[Y]').astype('int8')  # 3
                            st.success("Your Dataset was enriched with Age info.")
                        except ValueError:
                            st.error("Error: The source column cannot contain null or irrelevant values.")

                    if (enrich_method == "Anniversary") and (button_forEnrich):
                        try:
                            now = pd.Timestamp('now')
                            dataset[col_forEnriching] = pd.to_datetime(dataset[col_forEnriching],
                                                                       format='%d%m%Y')  # 1
                            dataset[col_forEnriching] = dataset[col_forEnriching].where(
                                dataset[col_forEnriching] < now,
                                dataset[col_forEnriching] - np.timedelta64(100, 'Y'))  # 2
                            dataset[str('Anniversary_'+col_forEnriching)] = (now - dataset[col_forEnriching]).astype(
                                '<m8[Y]').astype('int8')  # 3
                            st.success("Your Dataset was enriched with Anniversary info.")
                        except ValueError:
                            st.error("Error: The source column cannot contain null or irrelevant values.")

                    if (enrich_method == "Gender") and (button_forEnrich):
                        dataset['Ön İsim'] = \
                            dataset[col_forEnriching].str.split(' ', expand=True, n=1)[0]
                        dataset[str('Gender_'+col_forEnriching)] = dataset['Ön İsim'].map(
                            dict(TR_name_gender.isim_cinsiyet_tuple))
                        dataset.drop('Ön İsim', axis=1, inplace=True)
                        st.success("Your Dataset was enriched with Gender info.")

                    if (enrich_method == "Day") and (button_forEnrich):
                        dataset[str('Day_'+col_forEnriching)] = dataset[col_forEnriching].dt.day
                        st.success("Your Dataset was enriched with Day info.")

                    if (enrich_method == "Weekday") and (button_forEnrich):
                        dataset[str('Weekday_'+col_forEnriching)] = dataset[col_forEnriching].apply(
                            lambda x: x.weekday())
                        weekday_dict = {}
                        weekday_dict[0] = 'Monday'
                        weekday_dict[1] = 'Tuesday'
                        weekday_dict[2] = 'Wednesday'
                        weekday_dict[3] = 'Thursday'
                        weekday_dict[4] = 'Friday'
                        weekday_dict[5] = 'Saturday'
                        weekday_dict[6] = 'Sunday'
                        dataset[str('Weekday_'+col_forEnriching)] = dataset[str('Weekday_'+col_forEnriching)].apply(
                            lambda x: weekday_dict[x] if x in weekday_dict.keys() else x)
                        st.success("Your Dataset was enriched with Weekday info.")

                    if (enrich_method == "Month") and (button_forEnrich):
                        dataset[str('Month_'+col_forEnriching)] = dataset[col_forEnriching].dt.month
                        st.success("Your Dataset was enriched with Month info.")

                    if (enrich_method == "Year") and (button_forEnrich):
                        dataset[str('Year_'+col_forEnriching)] = dataset[col_forEnriching].dt.year
                        st.success("Your Dataset was enriched with Year info.")

                    if (enrich_method == "Quarter") and (button_forEnrich):
                        dataset[str('Quarter_'+col_forEnriching)] = pd.DatetimeIndex(dataset[col_forEnriching]).quarter
                        st.success("Your Dataset was enriched with Quarter info.")

                    if (enrich_method == "WeekofYear") and (button_forEnrich):
                        dataset[str('WeekofYear_'+col_forEnriching)] = pd.DatetimeIndex(dataset[col_forEnriching]).weekofyear
                        st.success("Your Dataset was enriched with WeekofYear info.")
                except KeyError:
                    st.warning("You are awaited to enter source column name.")

            sorting_expander = st.beta_expander("Sorting Transformation",
                                                expanded=False)
            with sorting_expander:
                col_for_sorting = dataset.columns
                colSort = st.multiselect("Select the columns whose values you want to sort", col_for_sorting,
                                         key="multiselect_forSorting22")
                asc = canContain = st.text_input(
                    "Please separate the ascending argument values with commas and use only True/False, for example 'True,False' (Do not put a space after comma)")
                asc = asc.split(',')
                if st.button("Sort", key="Sorting2"):
                    st.success("Changes were applied.")
                    res = list(map(lambda ele: ele == "True", asc))
                    dataset.sort_values(by=colSort, ascending=res, ignore_index=False, inplace=True)

            if st.button("Show my Dataset", key="display"):
                st.write(dataset)

    bst = st.session_state.beforeSS
    ast = st.session_state.afterSS
    if task == "Review Summary Report and Download Adjusted Data":
        st.write("'Before' Summary Table")
        st.dataframe(bst.style.format({"Column DQ Score(%)": '{:,.2f}'}))

        st.write("'After' Summary Table")
        st.dataframe(ast.style.format({"Column DQ Score(%)": '{:,.2f}'}))

        st.write("")
        bodq_score = round(bst["Column DQ Score(%)"].mean(), 2)
        aodq_score = round(ast["Column DQ Score(%)"].mean(), 2)

        if bodq_score <= 25:
            before_arrow = 1
        elif bodq_score > 25 and bodq_score <= 50:
            before_arrow = 2
        elif bodq_score > 50 and bodq_score <= 75:
            before_arrow = 3
        else:
            before_arrow = 4

        if aodq_score <= 25:
            after_arrow = 1
        elif aodq_score > 25 and aodq_score <= 50:
            after_arrow = 2
        elif aodq_score > 50 and aodq_score <= 75:
            after_arrow = 3
        else:
            after_arrow = 4

        odq_graph = st.beta_columns(2)
        with odq_graph[0]:
            gauge(labels=['VERY LOW', 'LOW', 'MEDIUM', 'HIGH'], \
                  colors=["#1b0203", "#ED1C24", '#FFCC00', '#007A00'], arrow=before_arrow, title=str(bodq_score) + '%')
            plt.title("'Before' Overall DQ Score", fontsize=16)
            st.pyplot()
        with odq_graph[1]:
            gauge(labels=['VERY LOW', 'LOW', 'MEDIUM', 'HIGH'], \
                  colors=["#1b0203", "#ED1C24", '#FFCC00', '#007A00'], arrow=after_arrow, title=str(aodq_score) + '%')
            plt.title("'After' Overall DQ Score", fontsize=16)
            st.pyplot()

        prepare_expander = st.beta_expander("Prepare Dataset for Download", expanded=False)
        with prepare_expander:
            session_state = SessionState.get(df=dataset)
            if st.checkbox("Reorder and Eliminate Columns", key = "reorder_eliminate"):
                col_for_order = dataset.columns
                colOrder = st.multiselect("Select the columns in the order you want them to be", col_for_order,
                                              key="multiselect_forOrder22")
                if st.button("Set", key="set_order2"):
                    session_state.df = dataset[colOrder]
                    st.success("The adjustments were applied.")
                    st.write("Sample", session_state.df.head())
                    download_button(get_table_download_link(session_state.df), "AdjustedData.xlsx", "📥 Download (.xlsx)")

            else:
                download_button(get_table_download_link(dataset), "AdjustedData.xlsx", "📥 Download (.xlsx)")

    if task == "Contact Me":
        """
        
        Hey there! 👋 I'm Beytullah, who studied Business Informatics. I have been working for Eczacibasi ICT as a Jr. Data Scientist since October 5, 2020.
        
        Source Code: [![Star](https://img.shields.io/github/stars/baligoyem/dataqtor.svg?logo=github&style=social)](https://github.com/baligoyem/dataqtor/stargazers)
        
        If you found this app useful, you can&nbsp[![Buy me a coffee](https://img.shields.io/badge/Buy%20me%20a%20Turkish%20coffee--yellow.svg?logo=buy-me-a-coffee&logoColor=orange&style=social)](https://www.buymeacoffee.com/baligoyem)
        
        Please feel free to contact me via the channels below if you have any questions or comments.
        """
        st.write("&nbsp[![Connect](https://img.shields.io/badge/-Beytullah_Ali_Göyem-blue?style=flat-square&logo=Linkedin&logoColor=white&link=https://tr.linkedin.com/in/beytullah-ali-g%C3%B6yem-461749152)](https://tr.linkedin.com/in/beytullah-ali-g%C3%B6yem-461749152) &nbsp[![mailto](https://img.shields.io/badge/-beytullahali.goyem@gmail.com-c14438?style=flat-square&logo=Gmail&logoColor=white&link=mailto:beytullahali.goyem@gmail.com)](mailto:beytullahali.goyem@gmail.com)&nbsp[![Follow](https://img.shields.io/twitter/follow/baligoyem?style=social)](https://twitter.com/baligoyem)")

else:
    st.write("")
    st.info('Awaiting for file to be uploaded.')
    st.write("")
    st.write("Interested in advertising here on this website? Please contact me at &nbsp[![mailto](https://img.shields.io/badge/-beytullahali.goyem@gmail.com-c14438?style=flat-square&logo=Gmail&logoColor=white&link=mailto:beytullahali.goyem@gmail.com)](mailto:beytullahali.goyem@gmail.com)")
    st.image('yourAdHere.PNG', width=750)
    st.write("")
    """
    **Get your data ready for use before you start working with it:**

    1. Upload your Excel/CSV file 📁
    2. Gain insight into your data 💡
    3. Measure the quality of your data 📊
    4. Repair your data in light of analyzes 🛠
    5. Observe improvement in data quality 📈
    6. Download the dataset you repaired 📥
    ---
    **DataQtor video tutorials (in Turkish)**
    
    Watch these short videos to learn about getting started with DataQtor.
    """
    st.markdown('<iframe width="650" height="350" src="https://www.youtube.com/embed/videoseries?list=PLQ04AOSABpu9wm7oosXX2pi7Js4RxSm0D" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>', unsafe_allow_html=True)
