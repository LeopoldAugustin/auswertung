import streamlit as st
import pandas as pd
import numpy as np

# Title and Description
st.title("BMF Classification Application")
st.write("""
This application allows you to upload an Excel file, select options, and process the data using the BMF classification functions.
""")

# Step 1: Upload an Excel file
uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx"])

if uploaded_file is not None:
    # Read the Excel file into a dataframe
    df = pd.read_excel(uploaded_file, header=10, usecols=[0, 1, 4])

    # Rename columns
    df.rename(columns={
        "Analyse in der Gesamtfraktion": "Stoff",
        "Unnamed: 1": "Aggregat",
        "Unnamed: 4": "Menge"
    }, inplace=True)

    # Filter the DataFrame
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
    df = df[df["Stoff"].isin(filter_values)]

    # Clean and convert the 'Menge' column to numeric
    def clean_menge(value):
        if isinstance(value, str):
            value = value.replace('<', '').replace(',', '.').strip()
        return pd.to_numeric(value, errors='coerce')

    df['Menge'] = df['Menge'].apply(clean_menge)

    # Update 'Aggregat' for 'pH-Wert'
    df.loc[df['Stoff'] == 'pH-Wert', 'Aggregat'] = '-'

    # Delete the row where 'Stoff' is 'Benzo(a)pyren' and 'Aggregat' is 'µg/l'
    df = df[~((df['Stoff'] == 'Benzo(a)pyren') & (df['Aggregat'] == 'µg/l'))]

    # Reset the index after deletion
    df = df.reset_index(drop=True)

    # User inputs via dropdowns
    # For 'subcategory' in 'classify_bmf' function
    subcategory_options = ['Sand', 'Lehm Schluff', 'Ton']
    subcategory = st.selectbox('Select Subcategory', subcategory_options)

    # For 'fremdbestandteile_under_10' in 'process_dataframe' function
    fremdbestandteile_option = st.selectbox('Are Fremdbestandteile under 10%?', ['Yes', 'No'])
    fremdbestandteile_under_10 = True if fremdbestandteile_option == 'Yes' else False

    # 'Run' button
    if st.button('Run'):
        # Classification function
        def classify_bmf(row, df, subcategory=None):
            stoff = row['Stoff']
            aggregat = row['Aggregat']
            menge = row['Menge']

            # Map 'Stoff' to 'Aggregat' if needed
            if stoff in ['Sulfat', 'Sulfat (SO4)']:
                aggregat = 'mg/l'

            # Determine 'toc_indicator' within the function
            # Initialize 'toc_indicator'
            toc_indicator = None

            # Check if 'Kohlenstoff(C) organisch (TOC)' exists in the dataframe
            if 'Kohlenstoff(C) organisch (TOC)' in df['Stoff'].values:
                # Get the 'Menge' value for 'Kohlenstoff(C) organisch (TOC)'
                toc_menge = df.loc[df['Stoff'] == 'Kohlenstoff(C) organisch (TOC)', 'Menge'].iloc[0]
                # Determine the 'toc_indicator' value
                if toc_menge > 0.5:
                    toc_indicator = 'TOC'
                else:
                    toc_indicator = 'no_TOC'
            else:
                # Default value if 'Kohlenstoff(C) organisch (TOC)' is not found
                toc_indicator = 'no_TOC'

            # Classification logic
            if stoff in classification_table and aggregat in classification_table[stoff]:
                stoff_agg = classification_table[stoff][aggregat]

                # Check if subcategory is needed
                if isinstance(stoff_agg, dict) and 'thresholds' not in stoff_agg:
                    # Subcategory is needed
                    if subcategory in stoff_agg:
                        stoff_data = stoff_agg[subcategory]
                    elif toc_indicator in stoff_agg:
                        # Use 'toc_indicator' as subcategory
                        stoff_data = stoff_agg[toc_indicator]
                    else:
                        # Proceed as if there was no subcategory
                        row['BMF_Klassifizierung_primär'] = "Not Classified"
                        return row
                else:
                    stoff_data = stoff_agg

                thresholds = stoff_data['thresholds']
                classifications = stoff_data['classifications']

                # Find the classification
                for idx, threshold in enumerate(thresholds):
                    if menge <= threshold:
                        classification = classifications[idx]
                        row['BMF_Klassifizierung_primär'] = classification
                        break
                else:
                    # Check if "Stoff" is "Benzo(a)pyren" or "EOX" and "Menge" exceeds the rightmost threshold
                    if stoff in ["Benzo(a)pyren", "EOX"] and menge > thresholds[-1]:
                        row['BMF_Klassifizierung_primär'] = "> BM-0 BG-0"
                    else:
                        row['BMF_Klassifizierung_primär'] = "DepV"
            else:
                row['BMF_Klassifizierung_primär'] = "Not Classified"

            # New logic for 'fremdbestandteile_under_10'
            if not fremdbestandteile_under_10:
                # Check if 'BMF_Klassifizierung_primär' is in ['BM-0 BG-0', 'BM-0* BG-0*']
                if row['BMF_Klassifizierung_primär'] in ['BM-0 BG-0', 'BM-0* BG-0*', '> BM-0 BG-0']:
                    # Replace with 'BM-F0 BG-F0'
                    row['BMF_Klassifizierung_primär'] = 'BM-F0 BG-F0'
                # If not, leave the value as it is

            return row
        


        def process_dataframe(df, fremdbestandteile_under_10=True):
            """
            Processes the dataframe by applying several transformations in a specific order.

            Parameters:
            df (pandas.DataFrame): The input dataframe.
            fremdbestandteile_under_10 (bool): Flag indicating if 'Fremdbestandteile' are under 10%.

            Returns:
            pandas.DataFrame: The processed dataframe.
            """
            # Step 1: Update 'BMF_Klassifizierung_primär' for specific 'Stoff' values
            stoff_list = ['Kohlenwasserstoffe C10-C22 (GC)', 'Kohlenwasserstoffe C10-C40']
            condition = df['Stoff'].isin(stoff_list) & (df['BMF_Klassifizierung_primär'] == 'BM-0* BG-0*')
            df.loc[condition, 'BMF_Klassifizierung_primär'] = 'BM-0 BG-0'

            # Step 2: Initialize new columns and apply initial conditions
            stoff_values = [
                'Arsen (As)', 'Blei (Pb)', 'Cadmium (Cd)', 'Chrom (Cr)', 'Kupfer (Cu)',
                'Nickel (Ni)', 'Quecksilber (Hg)', 'Thallium (Tl)', 'Zink (Zn)',
                'PAK EPA Summe gem. ErsatzbaustoffV', 'PCB 7 Summe gem. ErsatzbaustoffV'
            ]
            additional_stoff_values = ['Kohlenwasserstoffe C10-C22 (GC)', 'Kohlenwasserstoffe C10-C40']
            combined_stoff_values = stoff_values + additional_stoff_values

            df['BMF_sekundär'] = 'unrelevant'
            df['Deponie_klasse'] = 'unkritisch'

            condition_a = df['Stoff'].isin(stoff_values) & df['Aggregat'].isin(['mg/kg', 'mg/l']) & (df['BMF_Klassifizierung_primär'] == 'BM-0 BG-0')
            df.loc[condition_a, 'BMF_sekundär'] = 'BM-0 BG-0'

            condition_b = df['Stoff'].isin(additional_stoff_values) & (df['BMF_Klassifizierung_primär'] == 'BM-0* BG-0*')
            df.loc[condition_b, 'BMF_sekundär'] = 'BM-0* BG-0*'

            condition_c = df['Stoff'].isin(combined_stoff_values) & (df['Aggregat'] == 'µg/l')
            df.loc[condition_c, 'BMF_sekundär'] = 'unrelevant'

            combined_condition = condition_a | condition_b | condition_c
            df.loc[combined_condition, 'Deponie_klasse'] = 'unkritisch'

            # Update 'pH-Wert' and 'elektrische Leitfähigkeit'
            for stoff in ['pH-Wert', 'elektrische Leitfähigkeit']:
                condition = df['Stoff'] == stoff
                if condition.any():
                    bmf_prim_value = df.loc[condition, 'BMF_Klassifizierung_primär'].values[0]
                    if bmf_prim_value != 'BM-0 BG-0':
                        df.loc[condition, 'BMF_sekundär'] = bmf_prim_value
                        df.loc[condition, 'Deponie_klasse'] = f"{bmf_prim_value}¹"

            # Step 3: Additional checks and updates
            stoff_list_A = stoff_values.copy()
            condition1 = df['Stoff'].isin(stoff_list_A) & (df['Aggregat'] == 'mg/kg') & (df['BMF_Klassifizierung_primär'] == 'BM-0* BG-0*')
            leicht_verdacht = df.loc[condition1, 'Stoff'].unique().tolist()

            if leicht_verdacht:
                df.loc[condition1, ['BMF_sekundär', 'Deponie_klasse']] = 'BM-0* BG-0*'
                el_condition = df['Stoff'] == 'elektrische Leitfähigkeit'
                if el_condition.any():
                    el_bmf_prim = df.loc[el_condition, 'BMF_Klassifizierung_primär'].values[0]
                    df.loc[el_condition, 'BMF_sekundär'] = el_bmf_prim
                    df.loc[el_condition, 'Deponie_klasse'] = f"{el_bmf_prim}¹"

                bmf_f_list = ['BM-F0 BG-F0', 'BM-F1 BG-F1', 'BM-F2 BG-F2', 'BM-F3 BG-F3']
                all_stoffs = stoff_list_A + additional_stoff_values

                for stoff in leicht_verdacht:
                    condition_stoff_ug_l = (df['Stoff'] == stoff) & (df['Aggregat'] == 'µg/l')
                    if not condition_stoff_ug_l.any():
                        continue
                    bmf_klass_ug_l = df.loc[condition_stoff_ug_l, 'BMF_Klassifizierung_primär'].values[0]
                    if bmf_klass_ug_l == 'BM-0* BG-0*':
                        df.loc[condition_stoff_ug_l, ['BMF_sekundär', 'Deponie_klasse']] = ['unrelevant', 'unkritisch']
                    elif bmf_klass_ug_l in bmf_f_list:
                        df.loc[condition_stoff_ug_l, 'BMF_sekundär'] = bmf_klass_ug_l
                        for stoff in all_stoffs:
                            condition_stoff_aggregat = (df['Stoff'] == stoff) & (df['Aggregat'] == 'µg/l')
                            df.loc[condition_stoff_aggregat, 'BMF_sekundär'] = df.loc[condition_stoff_aggregat, 'BMF_Klassifizierung_primär']

            # Step 4: Further updates based on specific conditions
            bmf_f_list = ['BM-F0 BG-F0', 'BM-F1 BG-F1', 'BM-F2 BG-F2', 'BM-F3 BG-F3']
            all_stoffs = stoff_list_A + additional_stoff_values

            for stoff in all_stoffs:
                condition_stoff_mg_kg = (df['Stoff'] == stoff) & (df['Aggregat'] == 'mg/kg')
                if not condition_stoff_mg_kg.any():
                    continue
                bmf_klass_mg_kg = df.loc[condition_stoff_mg_kg, 'BMF_Klassifizierung_primär'].values[0]
                if bmf_klass_mg_kg in bmf_f_list:
                    df.loc[condition_stoff_mg_kg, 'BMF_sekundär'] = bmf_klass_mg_kg
                    el_condition = df['Stoff'] == 'elektrische Leitfähigkeit'
                    if el_condition.any():
                        el_bmf_prim = df.loc[el_condition, 'BMF_Klassifizierung_primär'].values[0]
                        df.loc[el_condition, 'BMF_sekundär'] = el_bmf_prim
                        df.loc[el_condition, 'Deponie_klasse'] = f"{el_bmf_prim}¹"
                    for stoff in all_stoffs:
                        condition_stoff_aggregat = df['Stoff'] == stoff
                        df.loc[condition_stoff_aggregat, 'BMF_sekundär'] = df.loc[condition_stoff_aggregat, 'BMF_Klassifizierung_primär']

            # Step 5: Adjustments based on 'fremdbestandteile_under_10' value
            if not fremdbestandteile_under_10:
                condition = ~df['Stoff'].isin(['pH-Wert', 'elektrische Leitfähigkeit']) & df['BMF_Klassifizierung_primär'].isin(['BM-0 BG-0', 'BM-0* BG-0*', '> BM-0 BG-0', 'BM-F0 BG-F0'])
                df.loc[condition, 'BMF_Klassifizierung_primär'] = 'BM-F0 BG-F0'
                df.loc[condition, ['BMF_sekundär', 'Deponie_klasse']] = ['unrelevant', 'unkritisch']

            # Step 6: Special handling for 'Sulfat (SO4)'
            exclude_stoffs = ['Sulfat (SO4)', 'pH-Wert', 'elektrische Leitfähigkeit']
            condition_exclude = ~df['Stoff'].isin(exclude_stoffs)
            bmf_sekundar_excluded = df.loc[condition_exclude, 'BMF_sekundär'].dropna()
            all_bm0_bg0_or_unrelevant = bmf_sekundar_excluded.isin(['BM-0 BG-0', 'unrelevant']).all()
            condition_sulfat = df['Stoff'] == 'Sulfat (SO4)'

            if condition_sulfat.any():
                sulfat_menge = df.loc[condition_sulfat, 'Menge'].iloc[0]
                sulfat_bmf_primar = df.loc[condition_sulfat, 'BMF_Klassifizierung_primär'].iloc[0]
                if all_bm0_bg0_or_unrelevant and (250 < sulfat_menge <= 450):
                    df.loc[condition_sulfat, ['BMF_Klassifizierung_primär', 'BMF_sekundär']] = 'BM-0 BG-0²'
                    df.loc[condition_sulfat, 'Deponie_klasse'] = 'BM-0 BG-0²'
                else:
                    df.loc[condition_sulfat, ['BMF_sekundär', 'Deponie_klasse']] = sulfat_bmf_primar

            # Step 7: Apply specific adjustments in 'halbtransparenz'
            cond1 = df.loc[df['Stoff'] == 'PAK EPA Summe gem. ErsatzbaustoffV', 'BMF_Klassifizierung_primär'].eq('BM-0 BG-0').any()
            cond2 = df.loc[df['Stoff'] == 'Benzo(a)pyren', 'BMF_Klassifizierung_primär'].eq('BM-0 BG-0').any()
            exclude_stoffs = ['pH-Wert', 'elektrische Leitfähigkeit', 'PAK EPA Summe gem. ErsatzbaustoffV', 'Benzo(a)pyren']
            condition_others = ~df['Stoff'].isin(exclude_stoffs)
            valid_bmf_sekundar_values = ['BM-0 BG-0', 'BM-0* BG-0*', 'unrelevant']
            bmf_sekundar_others = df.loc[condition_others, 'BMF_sekundär'].dropna()
            cond3 = bmf_sekundar_others.isin(valid_bmf_sekundar_values).all()
            target_stoffs = ['PAK 15 Summe gem. ErsatzbaustoffV', 'Naphthalin/Methylnaph.-Summe gem. ErsatzbaustoffV']
            condition_targets = df['Stoff'].isin(target_stoffs)

            if cond1 and cond2 and cond3:
                df.loc[condition_targets, ['BMF_sekundär', 'Deponie_klasse']] = ['unrelevant', 'unkritisch']
            else:
                df.loc[condition_targets, ['BMF_sekundär', 'Deponie_klasse']] = df.loc[condition_targets, 'BMF_Klassifizierung_primär']

            # Step 8: Final adjustments based on 'BMF_sekundär' and 'Deponie_klasse'
            # Exclude specified 'Stoff's
            exclude_stoffs = ['pH-Wert', 'elektrische Leitfähigkeit']
            condition_exclude = ~df['Stoff'].isin(exclude_stoffs)

            if fremdbestandteile_under_10:
                # Scenario 1
                #condition_bmf_not_bm0 = df['BMF_sekundär'] != 'BM-0 BG-0'
                condition_bmf_not_bm0 = ~df['BMF_sekundär'].isin(['BM-0 BG-0', 'BM-0* BG-0*'])

                # Update 'Deponie_klasse' where conditions are met
                condition_update = condition_exclude & condition_bmf_not_bm0 
                df.loc[condition_update, 'Deponie_klasse'] = df.loc[condition_update, 'BMF_sekundär']

                # Condition where 'BMF_sekundär' is either 'BM-0 BG-0' or 'BM-0* BG-0*'
                condition_bmf_bm0 = df['BMF_sekundär'].isin(['BM-0 BG-0', 'BM-0* BG-0*'])
                # Update 'Deponie_klasse' where conditions are met
                condition_update = condition_exclude & condition_bmf_bm0
                df.loc[condition_update, 'Deponie_klasse'] = 'unkritisch'

            else:
                # Scenario 2
                condition_bmf_not_bmf0 = df['BMF_sekundär'] != 'BM-F0 BG-F0'
                # Update 'Deponie_klasse' where conditions are met
                condition_update = condition_exclude & condition_bmf_not_bmf0 
                df.loc[condition_update, 'Deponie_klasse'] = df.loc[condition_update, 'BMF_sekundär']

                # Condition where 'BMF_sekundär' is either 'BM-0 BG-0' or 'BM-0* BG-0*'
                condition_bmf_bmf0 = df['BMF_sekundär'].isin(["BM-F0 BG-F0"])
                # Update 'Deponie_klasse' where conditions are met
                condition_update = condition_exclude & condition_bmf_bmf0
                df.loc[condition_update, 'Deponie_klasse'] = 'unkritisch'

            return df


        classification_table = {
            "Sulfat (SO4)": {
                "mg/l": {
                    "Sand": {
                        "thresholds": [250, 250, 250, 450, 450, 1000],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    },
                    "Lehm Schluff": {
                        "thresholds": [250, 250, 250, 450, 450, 1000],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    },
                    "Ton": {
                        "thresholds": [250, 250, 250, 450, 450, 1000],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    }
                }
            },
            "Arsen (As)": {
                "mg/kg": {
                    "Sand": {
                        "thresholds": [10, 20, 40, 40, 40, 150],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    },
                    "Lehm Schluff": {
                        "thresholds": [20, 20, 40, 40, 40, 150],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    },
                    "Ton": {
                        "thresholds": [20, 20, 40, 40, 40, 150],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    }
                },
                "µg/l": {
                    "no_TOC": {
                        "thresholds": [0, 8, 12, 20, 85, 100],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    },
                    "TOC": {
                        "thresholds": [0, 13, 13, 20, 85, 100],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    }  
                }
            },
            "Blei (Pb)": {
                "mg/kg": {
                    "Sand": {
                        "thresholds": [40, 140, 140, 140, 140, 700],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    },
                    "Lehm Schluff": {
                        "thresholds": [70, 140, 140, 140, 140, 700],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    },
                    "Ton": {
                        "thresholds": [100, 140, 140, 140, 140, 700],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    }
                },
                "µg/l": {
                    "no_TOC": {
                        "thresholds": [0, 23, 35, 90, 250, 470],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    },
                    "TOC": {
                        "thresholds": [0, 43, 43, 90, 250, 470],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    }  
                }
            },
            "Cadmium (Cd)": {
                "mg/kg": {
                    "Sand": {
                        "thresholds": [0.4, 1.5, 2, 2, 2, 10],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    },
                    "Lehm Schluff": {
                        "thresholds": [1, 1.5, 2, 2, 2, 10],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    },
                    "Ton": {
                        "thresholds": [1.5, 1.5, 2, 2, 2, 10],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    }
                },
                "µg/l": {
                    "no_TOC": {
                        "thresholds": [0, 2, 3, 3, 10, 15],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    },
                    "TOC": {
                        "thresholds": [0, 4, 4, 4, 10, 15],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    }  
                }
            },
            "Chrom (Cr)": {
                "mg/kg": {
                    "Sand": {
                        "thresholds": [30, 120, 120, 120, 120, 600],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    },
                    "Lehm Schluff": {
                        "thresholds": [60, 120, 120, 120, 120, 600],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    },
                    "Ton": {
                        "thresholds": [100, 120, 120, 120, 120, 600],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    }
                },
                "µg/l": {
                    "no_TOC": {
                        "thresholds": [0, 10, 15, 150, 290, 530],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    },
                    "TOC": {
                        "thresholds": [0, 19, 19, 150, 290, 530],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    }  
                }
            },
            "Kupfer (Cu)": {
                "mg/kg": {
                    "Sand": {
                        "thresholds": [20, 80, 80, 80, 80, 320],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    },
                    "Lehm Schluff": {
                        "thresholds": [40, 80, 80, 80, 80, 320],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    },
                    "Ton": {
                        "thresholds": [60, 80, 80, 80, 80, 320],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    }
                },
                "µg/l": {
                    "no_TOC": {
                        "thresholds": [0, 20, 30, 110, 170, 320],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    },
                    "TOC": {
                        "thresholds": [0, 41, 41, 110, 170, 320],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    }  
                }        
            },
            "Nickel (Ni)": {
                "mg/kg": {
                    "Sand": {
                        "thresholds": [15, 100, 100, 100, 100, 350],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    },
                    "Lehm Schluff": {
                        "thresholds": [50, 100, 100, 100, 100, 350],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    },
                    "Ton": {
                        "thresholds": [70, 100, 100, 100, 100, 350],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    }
                },
                "µg/l": {
                    "no_TOC": {
                        "thresholds": [0, 20, 30, 30, 150, 280],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    },
                    "TOC": {
                        "thresholds": [0, 31, 31, 31, 150, 280],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    }  
                }    
            },
            "Quecksilber (Hg)": {
                "mg/kg": {
                    "Sand": {
                        "thresholds": [0.2, 0.6, 0.6, 0.6, 0.6, 5],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    },
                    "Lehm Schluff": {
                        "thresholds": [0.3, 0.6, 0.6, 0.6, 0.6, 5],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    },
                    "Ton": {
                        "thresholds": [0.3, 0.6, 0.6, 0.6, 0.6, 5],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    }
                },
                "µg/l": {
                    "thresholds": [0, 0.1, 0.1, 0.1, 0.1, 0.1],
                    "classifications": [
                        "BM-0 BG-0",
                        "BM-0* BG-0*",
                        "BM-F0 BG-F0",
                        "BM-F1 BG-F1",
                        "BM-F2 BG-F2",
                        "BM-F3 BG-F3"
                    ]
                }
            },
            "Thallium (Tl)": {
                "mg/kg": {
                    "Sand": {
                        "thresholds": [0.5, 2, 2, 2, 2, 7],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    },
                    "Lehm Schluff": {
                        "thresholds": [1.0, 2, 2, 2, 2, 7],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    },
                    "Ton": {
                        "thresholds": [1.0, 2, 2, 2, 2, 7],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    }
                },
                "µg/l": {
                    "no_TOC": {
                        "thresholds": [0, 0.2, 0.2, 0.2, 0.2, 0.2],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    },
                    "TOC": {
                        "thresholds": [0, 0.3, 0.3, 0.3, 0.3, 0.3],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    }  
                }    
            },
            "Zink (Zn)": {
                "mg/kg": {
                    "Sand": {
                        "thresholds": [60, 300, 300, 300, 300, 1200],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    },
                    "Lehm Schluff": {
                        "thresholds": [150, 300, 300, 300, 300, 1200],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    },
                    "Ton": {
                        "thresholds": [200, 300, 300, 300, 300, 1200],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    }
                },
                "µg/l": {
                    "no_TOC": {
                        "thresholds": [0, 100, 150, 160, 840, 1600],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    },
                    "TOC": {
                        "thresholds": [0, 210, 210, 210, 840, 1600],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    }  
                }    
            },
            "Kohlenstoff(C) organisch (TOC)": {
                "%": {
                    "Sand": {
                        "thresholds": [1, 1, 5, 5, 5, 5],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    },
                    "Lehm Schluff": {
                        "thresholds": [1, 1, 5, 5, 5, 5],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    },
                    "Ton": {
                        "thresholds": [1, 1, 5, 5, 5, 5],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    }
                }
            },
            "Kohlenwasserstoffe C10-C22 (GC)": {
                "mg/kg": {
                    "Sand": {
                        "thresholds": [0, 300, 300, 300, 300, 1000],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    },
                    "Lehm Schluff": {
                        "thresholds": [0, 300, 300, 300, 300, 1000],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    },
                    "Ton": {
                        "thresholds": [0, 300, 300, 300, 300, 1000],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    }
                }
            },
            "Kohlenwasserstoffe C10-C40": {
                "mg/kg": {
                    "Sand": {
                        "thresholds": [0, 600, 600, 600, 600, 2000],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    },
                    "Lehm Schluff": {
                        "thresholds": [0, 600, 600, 600, 600, 2000],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    },
                    "Ton": {
                        "thresholds": [0, 600, 600, 600, 600, 2000],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    }
                }
            },
            "Benzo(a)pyren": {
                "mg/kg": {
                    "Sand": {
                        "thresholds": [0.3, 0.3, 0.3, 0.3, 0.3, 0.3],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    },
                    "Lehm Schluff": {
                        "thresholds": [0.3, 0.3, 0.3, 0.3, 0.3, 0.3],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    },
                    "Ton": {
                        "thresholds": [0.3, 0.3, 0.3, 0.3, 0.3, 0.3],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    }
                }
            },
            "PAK EPA Summe gem. ErsatzbaustoffV": {
                "mg/kg": {
                    "Sand": {
                        "thresholds": [3, 6, 6, 6, 9, 30],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    },
                    "Lehm Schluff": {
                        "thresholds": [3, 6, 6, 6, 9, 30],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    },
                    "Ton": {
                        "thresholds": [3, 6, 6, 6, 9, 30],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    }
                }
            },
            "PAK 15 Summe gem. ErsatzbaustoffV": {
                "µg/l": {
                    "thresholds": [0, 0.2, 0.3, 1.5, 3.8, 20],
                    "classifications": [
                        "BM-0 BG-0",
                        "BM-0* BG-0*",
                        "BM-F0 BG-F0",
                        "BM-F1 BG-F1",
                        "BM-F2 BG-F2",
                        "BM-F3 BG-F3"
                    ]
                }
            },
            "Naphthalin/Methylnaph.-Summe gem. ErsatzbaustoffV": {
                "µg/l": {
                    "thresholds": [2, 2, 2, 2, 2, 2],
                    "classifications": [
                        "BM-0 BG-0",
                        "BM-0* BG-0*",
                        "BM-F0 BG-F0",
                        "BM-F1 BG-F1",
                        "BM-F2 BG-F2",
                        "BM-F3 BG-F3"
                    ]
                }
            },
            "PCB 7 Summe gem. ErsatzbaustoffV": {
                "mg/kg": {
                    "Sand": {
                        "thresholds": [0.05, 0.1, 0.1, 0.1, 0.1, 0.1],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    },
                    "Lehm Schluff": {
                        "thresholds": [0.05, 0.1, 0.1, 0.1, 0.1, 0.1],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    },
                    "Ton": {
                        "thresholds": [0.05, 0.1, 0.1, 0.1, 0.1, 0.1],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    }
                },
                "µg/l": {
                    "thresholds": [0.01, 0.01, 0.01, 0.01, 0.01, 0.01],
                    "classifications": [
                        "BM-0 BG-0",
                        "BM-0* BG-0*",
                        "BM-F0 BG-F0",
                        "BM-F1 BG-F1",
                        "BM-F2 BG-F2",
                        "BM-F3 BG-F3"
                    ]
                }
            },
            "EOX": {
                "mg/kg": {
                    "Sand": {
                        "thresholds": [1, 1, 1, 1, 1, 1],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    },
                    "Lehm Schluff": {
                        "thresholds": [1, 1, 1, 1, 1, 1],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    },
                    "Ton": {
                        "thresholds": [1, 1, 1, 1, 1, 1],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    }
                }
            },
            "elektrische Leitfähigkeit": {
                "µS/cm": {
                    "Sand": {
                        "thresholds": [0, 350, 350, 500, 500, 2000],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    },
                    "Lehm Schluff": {
                        "thresholds": [0, 350, 350, 500, 500, 2000],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    },
                    "Ton": {
                        "thresholds": [0, 350, 350, 500, 500, 2000],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    }
                }
            },
            "pH-Wert": {
                "-": {
                    "Sand": {
                        "thresholds": [0, 0, 9.5, 9.5, 9.5, 12],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    },
                    "Lehm Schluff": {
                        "thresholds": [0, 0, 9.5, 9.5, 9.5, 12],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    },
                    "Ton": {
                        "thresholds": [0, 0, 9.5, 9.5, 9.5, 12],
                        "classifications": [
                            "BM-0 BG-0",
                            "BM-0* BG-0*",
                            "BM-F0 BG-F0",
                            "BM-F1 BG-F1",
                            "BM-F2 BG-F2",
                            "BM-F3 BG-F3"
                        ]
                    }
                }
            }
        }


        # Ensure the classification_table is available
        if not classification_table:
            st.error("Classification table is missing.")
        else:
            # Apply 'classify_bmf' function
            df = df.apply(
                lambda row: classify_bmf(
                    row,
                    df,
                    subcategory=subcategory
                ),
                axis=1
            )

            # Apply 'process_dataframe' function
            df = process_dataframe(df, fremdbestandteile_under_10=fremdbestandteile_under_10)

            # Display the final dataframe
            st.subheader("Processed DataFrame")
            st.dataframe(df)

            # Option to download the dataframe as a CSV
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download data as CSV",
                data=csv,
                file_name='processed_dataframe.csv',
                mime='text/csv',
            )
else:
    st.info("Please upload an Excel file to proceed.")
