import streamlit as st
st.set_page_config(layout="wide")  # Set the layout to wide
import pandas as pd
from pathlib import Path
import numpy as np
import pickle

# Load the dictionary from the pickle file
with open('classification_table.pkl', 'rb') as file:
    classification_table = pickle.load(file)

# Load the list from the pickle file
with open('complete_df_stoffe.pkl', 'rb') as file:
    complete_df_stoffe = pickle.load(file)

# Title and Description
st.title("BMF Klassifizierung")
st.write("""
Lade den agrolab Auswertungsbericht als Excel Datei hoch und erhalte die BMF Klassifizierung, welche die aktuellsten gesetzlichen Vorgaben erfüllt.
""")

# Step 1: Upload an Excel file
uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx"])

if uploaded_file is not None:
    ############################################################
    #START DATA PART OF CODE - WITHOUT FIRST LINE
    ############################################################
    
    # Define filter_values
    filter_values = [
        "Kohlenstoff(C) organisch (TOC)",
        "EOX",
        "Arsen (As)",
        "Blei (Pb)",
        "Cadmium (Cd)",
        "Chrom (Cr)",
        "Kupfer (Cu)",
        "Nickel (Ni)",
        "Quecksilber (Hg)",
        "Thallium (Tl)",
        "Zink (Zn)",
        "Kohlenwasserstoffe C10-C22 (GC)",
        "Kohlenwasserstoffe C10-C40",
        "Benzo(a)pyren",
        "PAK EPA Summe gem. ErsatzbaustoffV",
        "PCB 7 Summe gem. ErsatzbaustoffV",
        "pH-Wert",
        "elektrische Leitfähigkeit",
        "Sulfat (SO4)",
        "Naphthalin/Methylnaph.-Summe gem. ErsatzbaustoffV",
        "PAK 15 Summe gem. ErsatzbaustoffV"
    ]

    # Check F6 for multiple tables
    temp_df = pd.read_excel(uploaded_file, header=None, nrows=6, usecols="F")
    
    # Step 2: Check if F6 is empty
    if pd.isna(temp_df.iloc[5, 0]):
        print("Cell F6 is empty. Proceeding with the usual process...")
        
        # Read the first 15 rows without header to check cell values
        temp_df = pd.read_excel(uploaded_file, header=None, nrows=15)

        # Determine the header row based on cell values
        if temp_df.iloc[9, 0] == "Parameter":
            header_row = 10
        elif temp_df.iloc[6, 0] == "Parameter":
            header_row = 7
        elif temp_df.iloc[13, 0] == "PARAMETER MIT BEWERTUNG NACH MANTELV":
            header_row = 15
        else:
            raise ValueError("Unknown Excel format")

        # Read the data with the correct header
        df = pd.read_excel(uploaded_file, header=header_row, usecols=[0, 1, 4])
        df.columns = ['Stoff', 'Aggregat', 'Menge']
        df = df[df["Stoff"].isin(filter_values)]

        # Clean and convert the 'Menge' column to numeric
        def clean_menge(value):
            if isinstance(value, str):
                value = value.replace('<', '').replace('>', '').replace('<=', '').replace('≥', '').replace('>=', '').replace('=', '').replace(',', '.').strip()
            return pd.to_numeric(value, errors='coerce')

        df['Menge'] = df['Menge'].apply(clean_menge)

        # Update 'Aggregat' for 'pH-Wert'
        df.loc[df['Stoff'] == 'pH-Wert', 'Aggregat'] = '-'

        # Delete the row where 'Stoff' is 'Benzo(a)pyren' and 'Aggregat' is 'µg/l'
        df = df[~((df['Stoff'] == 'Benzo(a)pyren') & (df['Aggregat'] == 'µg/l'))]
        df = df.reset_index(drop=True)
        dataframes = [df]  # Wrap the single dataframe into a list

    else:
        print("Cell F6 is not empty. Handling multiple tables...")

        # Check how many columns starting from column E are not empty
        temp_df = pd.read_excel(uploaded_file, header=None, nrows=6)
        non_empty_columns = temp_df.iloc[5, 4:].notna().sum()

        dataframes = []
        for i in range(non_empty_columns):
            col_letter = chr(ord('E') + i)
            df = pd.read_excel(uploaded_file, header=10, usecols=[0, 1, 4 + i])
            df.columns = ['Stoff', 'Aggregat', 'Menge']
            df = df[df["Stoff"].isin(filter_values)]
            df['Menge'] = df['Menge'].apply(clean_menge)
            df.loc[df['Stoff'] == 'pH-Wert', 'Aggregat'] = '-'
            df = df[~((df['Stoff'] == 'Benzo(a)pyren') & (df['Aggregat'] == 'µg/l'))]
            df = df.reset_index(drop=True)
            dataframes.append(df)

    ############################################################
    #END DATA PART OF CODE
    ############################################################

    # User inputs via dropdowns
    subcategory_options = ['Sand', 'Lehm Schluff', 'Ton']
    subcategory = st.selectbox('Select Subcategory', subcategory_options)
    
    fremdbestandteile_option = st.selectbox('Are Fremdbestandteile under 10%?', ['Yes', 'No'])
    fremdbestandteile_under_10 = True if fremdbestandteile_option == 'Yes' else False

    if st.button('Run'):
        def classify_bmf(row, df, subcategory=None):
            stoff = row['Stoff']
            aggregat = row['Aggregat']
            menge = row['Menge']

            if stoff in ['Sulfat', 'Sulfat (SO4)']:
                aggregat = 'mg/l'

            toc_indicator = None

            if 'Kohlenstoff(C) organisch (TOC)' in df['Stoff'].values:
                toc_menge = df.loc[df['Stoff'] == 'Kohlenstoff(C) organisch (TOC)', 'Menge'].iloc[0]
                toc_indicator = 'TOC' if toc_menge > 0.5 else 'no_TOC'
            else:
                toc_indicator = 'no_TOC'

            if stoff in classification_table and aggregat in classification_table[stoff]:
                stoff_agg = classification_table[stoff][aggregat]

                if isinstance(stoff_agg, dict) and 'thresholds' not in stoff_agg:
                    if subcategory in stoff_agg:
                        stoff_data = stoff_agg[subcategory]
                    elif toc_indicator in stoff_agg:
                        stoff_data = stoff_agg[toc_indicator]
                    else:
                        row['BMF_primär'] = "Not Classified"
                        return row
                else:
                    stoff_data = stoff_agg

                thresholds = stoff_data['thresholds']
                classifications = stoff_data['classifications']

                valid_thresholds = [threshold for threshold in thresholds if threshold > menge]
                if valid_thresholds:
                    min_threshold = min(valid_thresholds)
                    for idx, threshold in enumerate(thresholds):
                        if threshold == min_threshold:
                            row['BMF_primär'] = classifications[idx]
                            break
                else:
                    if stoff in ["Benzo(a)pyren", "EOX"] and menge > thresholds[-1]:
                        row['BMF_primär'] = "> BM-0 BG-0"
                    else:
                        row['BMF_primär'] = ">BM-F3 BG-F3"
            else:
                row['BMF_primär'] = "Not Classified"

            return row

        def fullpipeline(df, subcategory="Sand", eluat=True, fremdbestandteile_under_10=True):
            df = df.apply(lambda row: classify_bmf(row, df, subcategory=subcategory), axis=1)
            df['BMF_sekundär'] = df['BMF_primär']
            df['Relevante_Klassen'] = ''
            return df

        final_dfs = []
        for idx, df in enumerate(dataframes):
            final_df = fullpipeline(df, subcategory=subcategory, eluat=True, fremdbestandteile_under_10=fremdbestandteile_under_10)
            final_dfs.append(final_df)

        final_result = pd.concat(final_dfs, ignore_index=True)

        st.subheader("Processed DataFrame")
        st.dataframe(final_result)

        csv = final_result.to_csv(index=False).encode('utf-8')
        st.download_button(label="Download data as CSV", data=csv, file_name='processed_dataframe.csv', mime='text/csv')

else:
    st.info("Please upload an Excel file to proceed.")
