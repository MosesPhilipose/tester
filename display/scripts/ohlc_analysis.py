import os
import configparser
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

class OHLCAnalysis:
    analysis_to_case = {
        "High Gap Up n Up Trend n Up": 1,
        "High Gap Up n Up Trend n Down": 2,
        "High Gap Up n Up Trend n Flat Close": 3,
        "High Gap Up n Down Trend n Up": 4,
        "High Gap Up n Down Trend n Down": 5,
        "High Gap Up n Down Trend n Flat Close": 6,
        "High Gap Up n Indecisive n Up": 7,
        "High Gap Up n Indecisive n Down": 8,
        "High Gap Up n Indecisive n Flat Close": 9,
        "Moderate Gap Up n Up Trend n Up": 10,
        "Moderate Gap Up n Up Trend n Down": 11,
        "Moderate Gap Up n Up Trend n Flat Close": 12,
        "Moderate Gap Up n Down Trend n Up": 13,
        "Moderate Gap Up n Down Trend n Down": 14,
        "Moderate Gap Up n Down Trend n Flat Close": 15,
        "Moderate Gap Up n Indecisive n Up": 16,
        "Moderate Gap Up n Indecisive n Down": 17,
        "Moderate Gap Up n Indecisive n Flat Close": 18,
        "Flat Open n Up Trend n Up": 19,
        "Flat Open n Up Trend n Down": 20,
        "Flat Open n Up Trend n Flat Close": 21,
        "Flat Open n Down Trend n Up": 22,
        "Flat Open n Down Trend n Down": 23,
        "Flat Open n Down Trend n Flat Close": 24,
        "Flat Open n Indecisive n Up": 25,
        "Flat Open n Indecisive n Down": 26,
        "Flat Open n Indecisive n Flat Close": 27,
        "Moderate Gap Down n Up Trend n Up": 28,
        "Moderate Gap Down n Up Trend n Down": 29,
        "Moderate Gap Down n Up Trend n Flat Close": 30,
        "Moderate Gap Down n Down Trend n Up": 31,
        "Moderate Gap Down n Down Trend n Down": 32,
        "Moderate Gap Down n Down Trend n Flat Close": 33,
        "Moderate Gap Down n Indecisive n Up": 34,
        "Moderate Gap Down n Indecisive n Down": 35,
        "Moderate Gap Down n Indecisive n Flat Close": 36,
        "High Gap Down n Up Trend n Up": 37,
        "High Gap Down n Up Trend n Down": 38,
        "High Gap Down n Up Trend n Flat Close": 39,
        "High Gap Down n Down Trend n Up": 40,
        "High Gap Down n Down Trend n Down": 41,
        "High Gap Down n Down Trend n Flat Close": 42,
        "High Gap Down n Indecisive n Up": 43,
        "High Gap Down n Indecisive n Down": 44,
        "High Gap Down n Indecisive n Flat Close": 45
    }
    
    # Define the symbol mapping
    symbol_mapping = {
        "BANK_NIFTY": "^NSEBANK",
        "NIFTY_IT": "^CNXIT",
        "SENSEX": "^BSESN",
        "NIFTY_FINANCE": "^CNXFIN",
        "NIFTY50": "^NSEI",
        "CRUDE_OIL": "CL=F",  # Crude Oil Futures
        "GOLD": "GC=F",       # Gold Futures
        "SILVER": "SI=F",     # Silver Futures
    }

    def __init__(self, config_file):
        # Load configuration from the .ini file
        self.config = configparser.ConfigParser()
        self.config.read(config_file)

        # Extract settings from the .ini file
        self.symbol = self.config.get('OHLC_Settings', 'symbol')
        self.num_years = self.config.getint('OHLC_Settings', 'num_years')
        self.base_gap = self.config.getfloat('OHLC_Settings', 'base_gap')
        self.step_size = self.config.getfloat('OHLC_Settings', 'step_size')
        self.threshold_m1 = self.config.getfloat('OHLC_Settings', 'threshold_m1')
        self.threshold_n1 = self.config.getfloat('OHLC_Settings', 'threshold_n1')
        self.close_threshold = self.config.getfloat('OHLC_Settings', 'close_threshold')

        # Initialize other variables
        self.data = None
        
        # Create a reverse mapping for symbol names
        self.reverse_symbol_mapping = {v: k for k, v in self.symbol_mapping.items()}

    def download_data(self, end_date=None):
        # If no end_date is provided, use the current date
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        # Convert end_date to a datetime object
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
        
        # Calculate the start date based on num_years
        start_date = (end_date_obj - timedelta(days=self.num_years * 365)).strftime('%Y-%m-%d')
        end_date = (end_date_obj + timedelta(days=1)).strftime('%Y-%m-%d')  # Add one day to include the end_date in the data
        
        # Download the data using yfinance
        self.data = yf.download(self.symbol, start=start_date, end=end_date)
        
        # Reset index and format the 'Date' column
        self.data.reset_index(inplace=True)
        self.data['Date'] = pd.to_datetime(self.data['Date']).dt.strftime('%d-%m-%Y')
        
        pass

    def preprocess_data(self):
        if isinstance(self.data.columns, pd.MultiIndex):
            self.data.columns = [' '.join(col).strip() for col in self.data.columns]
        self.data.rename(
            columns={
                'Date': 'Date',
                f'Close {self.symbol}': 'Close',
                f'Open {self.symbol}': 'Open',
                f'High {self.symbol}': 'High',
                f'Low {self.symbol}': 'Low',
                f'Volume {self.symbol}': 'Volume',
            },
            inplace=True,
            errors='ignore',
        )
        required_columns = ['Open', 'High', 'Low', 'Close']
        missing_columns = [col for col in required_columns if col not in self.data.columns]
        if missing_columns:
            raise KeyError(f"Missing required columns: {missing_columns}")
        self.data = self.data.dropna(subset=['Close'])
        
        pass

    def calculate_indicators(self):
        previous_close = self.data['Close'].shift(1)
        self.data['Opening Value'] = (self.data['Open'] - previous_close).round(2)
        self.data['Opening per'] = ((self.data['Opening Value'] / previous_close.replace(to_replace=0, value=np.nan)) * 100).round(2)
        self.data['High-Close'] = (self.data['High'] - previous_close).round(2)
        self.data['Low-Close'] = (self.data['Low'] - previous_close).round(2)
        self.data['High per'] = (((self.data['High'] - previous_close) / previous_close.replace(to_replace=0, value=np.nan)) * 100).round(2)
        self.data['Low per'] = (((self.data['Low'] - previous_close) / previous_close.replace(to_replace=0, value=np.nan)) * 100).round(2)
        self.data['High per-Opening per'] = np.where(
            self.data['Opening per'] >= 0,
            (self.data['High per'] - self.data['Opening per']).round(2),
            np.nan
        )
        self.data['Low per-Opening per'] = np.where(
            self.data['Opening per'] < 0,
            (self.data['Low per'] - self.data['Opening per']).round(2),
            np.nan
        )
        self.data['Close-Prev Close per'] = ((self.data['Close'] - previous_close) / previous_close.replace(to_replace=0, value=np.nan) * 100).round(2)
        self.data['EOD per-Gap per'] = ((self.data['Close-Prev Close per'] - self.data['Opening per']) / self.data['Opening per'].replace(to_replace=0, value=np.nan) * 100).round(2)

        pass
    def assign_ranges(self):
        flat_open_min = -self.base_gap
        flat_open_max = self.base_gap
        moderate_gap_up_min = flat_open_max
        moderate_gap_up_max = moderate_gap_up_min + self.step_size
        moderate_gap_down_max = flat_open_min
        moderate_gap_down_min = moderate_gap_down_max - self.step_size
        high_gap_up_min = moderate_gap_up_max
        high_gap_up_max = high_gap_up_min + self.step_size
        high_gap_down_max = moderate_gap_down_min
        high_gap_down_min = high_gap_down_max - self.step_size
        power_gap_up_min = high_gap_up_max
        power_gap_down_max = high_gap_down_min
        self.data['7 Ranges'] = np.where(
            self.data['Opening per'].isna(), "",
            np.where(
                (self.data['Opening per'] >= flat_open_min) & (self.data['Opening per'] <= flat_open_max), "Flat Open",
                np.where(
                    (self.data['Opening per'] > moderate_gap_up_min) & (self.data['Opening per'] <= moderate_gap_up_max), "Moderate Gap Up",
                    np.where(
                        (self.data['Opening per'] > high_gap_up_min), "High Gap Up",
                        np.where(
                            (self.data['Opening per'] < moderate_gap_down_max) & (self.data['Opening per'] >= moderate_gap_down_min), "Moderate Gap Down",
                            np.where(
                                (self.data['Opening per'] < high_gap_down_max), "High Gap Down",
                                ""
                            )
                        )
                    )
                )
            )
        )
        pass

    def trend_setter(self, M1, N1):
        self.data['Trend'] = np.nan
        self.data['Trend'] = self.data['Trend'].astype(object)
        self.data['Trend'] = np.where(
            (self.data['Opening per'] >= 0) &
            (self.data['Low per'] >= M1) &
            (~np.isnan(self.data['High per-Opening per'])) & (self.data['High per-Opening per'] >= N1), "Up Trend",
            np.where(
                (self.data['Opening per'] >= 0) &
                (self.data['Low per'] > -M1) & (self.data['Low per'] < M1) &
                (~np.isnan(self.data['High per-Opening per'])) & (self.data['High per-Opening per'] >= N1), "Indecisive",
                np.where(
                    (self.data['Opening per'] >= 0) &
                    (self.data['Low per'] >= M1) &
                    (~np.isnan(self.data['High per-Opening per'])) & (self.data['High per-Opening per'] < N1), "Indecisive",
                    np.where(
                        (self.data['Opening per'] >= 0) &
                        (self.data['Low per'] > -M1) & (self.data['Low per'] < M1) &
                        (~np.isnan(self.data['High per-Opening per'])) & (self.data['High per-Opening per'] < N1), "Indecisive",
                        np.where(
                            (self.data['Opening per'] >= 0) &
                            (self.data['Low per'] <= -M1) &
                            (~np.isnan(self.data['High per-Opening per'])) & (self.data['High per-Opening per'] >= N1), "Indecisive",
                            np.where(
                                (self.data['Opening per'] >= 0) &
                                (self.data['Low per'] <= -M1) &
                                (~np.isnan(self.data['High per-Opening per'])) & (self.data['High per-Opening per'] < N1), "Down Trend",
                                np.where(
                                    (self.data['Opening per'] < 0) &
                                    (self.data['High per'] <= -M1) &
                                    (~np.isnan(self.data['Low per-Opening per'])) & (self.data['Low per-Opening per'] < -N1), "Down Trend",
                                    np.where(
                                        (self.data['Opening per'] < 0) &
                                        (self.data['High per'] <= -M1) &
                                        (~np.isnan(self.data['Low per-Opening per'])) & (self.data['Low per-Opening per'] >= -N1), "Indecisive",
                                        np.where(
                                            (self.data['Opening per'] < 0) &
                                            (self.data['High per'] > -M1) & (self.data['High per'] <= M1) &
                                            (~np.isnan(self.data['Low per-Opening per'])) & (self.data['Low per-Opening per'] < -N1), "Indecisive",
                                            np.where(
                                                (self.data['Opening per'] < 0) &
                                                (self.data['High per'] > -M1) & (self.data['High per'] <= M1) &
                                                (~np.isnan(self.data['Low per-Opening per'])) & (self.data['Low per-Opening per'] >= -N1), "Indecisive",
                                                np.where(
                                                    (self.data['Opening per'] < 0) &
                                                    (self.data['High per'] > M1) &
                                                    (~np.isnan(self.data['Low per-Opening per'])) & (self.data['Low per-Opening per'] < -N1), "Indecisive",
                                                    np.where(
                                                        (self.data['Opening per'] < 0) &
                                                        (self.data['High per'] > M1) &
                                                        (~np.isnan(self.data['Low per-Opening per'])) & (self.data['Low per-Opening per'] >= -N1), "Up Trend",
                                                        "No Trend"
                                                    )
                                                )
                                            )
                                        )
                                    )
                                )
                            )
                        )
                    )
                )
            )
        )
        pass

    def final_indicators(self, close_threshold):
        self.data['Closed'] = np.where(
            self.data['Close-Prev Close per'] > close_threshold, "Up",
            np.where(self.data['Close-Prev Close per'] < -close_threshold, "Down", "Flat Close")
        )
        self.data['Analysis'] = (
            self.data['7 Ranges'] + " n " +
            self.data['Trend'] + " n " +
            self.data['Closed']
        )
        self.data['Sr no '] = self.data['Analysis'].map(self.analysis_to_case).fillna("")

        pass
    def finalize_data(self):
        self.data['Day'] = pd.to_datetime(self.data['Date'], format='%d-%m-%Y').dt.day_name()
        reordered_columns = [
            'Opening Value',
            'Opening per',
            '7 Ranges',
            'High-Close',
            'Low-Close',
            'High per',
            'Low per',
            'High per-Opening per',
            'Low per-Opening per',
            'Trend',
            'Close-Prev Close per',
            'EOD per-Gap per',
            'Closed',
            'Sr no ',
            'Analysis',
        ]
        self.data = self.data[['Date', 'Day', 'Open', 'High', 'Low', 'Close'] + reordered_columns]

        pass
    def create_statistics_sheet(self):
        all_cases = pd.DataFrame({
            'Cases': list(self.analysis_to_case.keys()),
            'S.no.': list(self.analysis_to_case.values())
        })


        case_frequency = self.data['Analysis'].value_counts().reset_index()
        case_frequency.columns = ['Cases', 'Frequency']

        case_frequency = all_cases.merge(case_frequency, on='Cases', how='left').fillna(0)


        case_frequency['7 Ranges'] = case_frequency['Cases'].str.split(' n ').str[0]
        group_frequency = case_frequency.groupby('7 Ranges')['Frequency'].transform('sum')
        total_frequency = case_frequency['Frequency'].sum()
        case_frequency['Probability Out of Group'] = (case_frequency['Frequency'] / group_frequency * 100).round(2)

        case_frequency['Probability Out of Total'] = (case_frequency['Frequency'] / total_frequency * 100).round(2)

        # Calculate At Close
        case_frequency[['Trend', 'Closed']] = case_frequency['Cases'].str.split(' n ', expand=True).iloc[:, [1, 2]]
        close_frequency = case_frequency.groupby(['7 Ranges', 'Trend'])['Frequency'].transform('sum')
        case_frequency['At Close'] = (case_frequency['Frequency'] / close_frequency * 100).round(2)
        case_frequency['At Close'] = case_frequency['At Close'].fillna(0)  # Handle zero division errors

        case_frequency = case_frequency[['Cases', 'S.no.', 'Frequency', 'Probability Out of Group', 'Probability Out of Total', 'At Close']]

        # Append a blank row for separation
        blank_row = pd.DataFrame([['', '', '', '', '', '']], columns=case_frequency.columns)
        case_frequency = pd.concat([case_frequency, blank_row], ignore_index=True)

        additional_cases = [
            "Moderate Gap Up",
            "Moderate Gap Up n Up Trend",
            "Moderate Gap Up n Down Trend",
            "Moderate Gap Up n Indecisive",
            "Moderate Gap Up n Down Trend or Indecisive",
            "Moderate Gap Up n Down Trend or Indecisive n Down",
            "Moderate Gap Up n Down Trend or Indecisive n Down or Flat Close",
            "Moderate Gap Up n Up Trend or Indecisive",
            "Moderate Gap Up n Up Trend or Indecisive n Up",
            "Moderate Gap Up n Up Trend or Indecisive n Up or Flat Close",
            "Moderate Gap Down",
            "Moderate Gap Down n Up Trend",
            "Moderate Gap Down n Down Trend",
            "Moderate Gap Down n Indecisive",
            "Moderate Gap Down n Down Trend or Indecisive",
            "Moderate Gap Down n Down Trend or Indecisive n Down",
            "Moderate Gap Down n Down Trend or Indecisive n Down or Flat Close",
            "Moderate Gap Down n Up Trend or Indecisive",
            "Moderate Gap Down n Up Trend or Indecisive n Up",
            "Moderate Gap Down n Up Trend or Indecisive n Up or Flat Close",
            "Flat Open",
            "Flat Open n Up Trend",
            "Flat Open n Down Trend",
            "Flat Open n Indecisive",
            "Flat Open n Down Trend n Up",
            "Flat Open n Down Trend or Indecisive",
            "Flat Open n Down Trend or Indecisive n Up",
            "Flat Open n Down Trend or Indecisive n Down",
            "Flat Open n Up Trend n Down",
            "Flat Open n Up Trend or Indecisive",
            "Flat Open n Up Trend or Indecisive n Up",
            "Flat Open n Up Trend or Indecisive n Down"
        ]

        additional_case_data = []
        for case in additional_cases:
            if case == "Moderate Gap Up":
                frequency_sum = self.data[self.data['7 Ranges'] == "Moderate Gap Up"].shape[0]
                probability_out_of_group = (frequency_sum / total_frequency) * 100
            elif case == "Moderate Gap Up n Up Trend":
                frequency_sum = self.data[(self.data['7 Ranges'] == "Moderate Gap Up") & (self.data['Trend'] == "Up Trend")].shape[0]
                Moderate_Gap_Up = self.data[self.data['7 Ranges'] == "Moderate Gap Up"].shape[0]
                probability_out_of_group = (frequency_sum / Moderate_Gap_Up) * 100
            elif case == "Moderate Gap Up n Down Trend":
                frequency_sum = self.data[(self.data['7 Ranges'] == "Moderate Gap Up") & (self.data['Trend'] == "Down Trend")].shape[0]
                Moderate_Gap_Up = self.data[self.data['7 Ranges'] == "Moderate Gap Up"].shape[0]
                probability_out_of_group = (frequency_sum / Moderate_Gap_Up) * 100
            elif case == "Moderate Gap Up n Indecisive":
                frequency_sum = self.data[(self.data['7 Ranges'] == "Moderate Gap Up") & (self.data['Trend'] == "Indecisive")].shape[0]
                Moderate_Gap_Up = self.data[self.data['7 Ranges'] == "Moderate Gap Up"].shape[0]
                probability_out_of_group = (frequency_sum / Moderate_Gap_Up) * 100
            elif case == "Moderate Gap Up n Down Trend or Indecisive":
                frequency_sum = self.data[
                    (self.data['7 Ranges'] == "Moderate Gap Up") &
                    ((self.data['Trend'] == "Down Trend") | (self.data['Trend'] == "Indecisive"))
                ].shape[0]
                Moderate_Gap_Up = self.data[self.data['7 Ranges'] == "Moderate Gap Up"].shape[0]
                probability_out_of_group = (frequency_sum / Moderate_Gap_Up) * 100
            elif case == "Moderate Gap Up n Down Trend or Indecisive n Down":
                frequency_sum = self.data[
                    (self.data['7 Ranges'] == "Moderate Gap Up") &
                    ((self.data['Trend'] == "Down Trend") | (self.data['Trend'] == "Indecisive")) &
                    (self.data['Closed'] == "Down")
                ].shape[0]
                Moderate_Gap_Up_n_Down_Trend_or_Indecisive = self.data[
                    (self.data['7 Ranges'] == "Moderate Gap Up") &
                    ((self.data['Trend'] == "Down Trend") | (self.data['Trend'] == "Indecisive"))
                ].shape[0]
                probability_out_of_group = (frequency_sum / Moderate_Gap_Up_n_Down_Trend_or_Indecisive) * 100
            elif case == "Moderate Gap Up n Down Trend or Indecisive n Down or Flat Close":
                frequency_sum = self.data[
                    (self.data['7 Ranges'] == "Moderate Gap Up") &
                    ((self.data['Trend'] == "Down Trend") | (self.data['Trend'] == "Indecisive")) &
                    ((self.data['Closed'] == "Down") | (self.data['Closed'] == "Flat Close"))
                ].shape[0]
                Moderate_Gap_Up_n_Down_Trend_or_Indecisive = self.data[
                    (self.data['7 Ranges'] == "Moderate Gap Up") &
                    ((self.data['Trend'] == "Down Trend") | (self.data['Trend'] == "Indecisive"))
                ].shape[0]
                probability_out_of_group = (frequency_sum / Moderate_Gap_Up_n_Down_Trend_or_Indecisive) * 100
            elif case == "Moderate Gap Up n Up Trend or Indecisive":
                frequency_sum = self.data[
                    (self.data['7 Ranges'] == "Moderate Gap Up") &
                    ((self.data['Trend'] == "Up Trend") | (self.data['Trend'] == "Indecisive"))
                ].shape[0]
                Moderate_Gap_Up = self.data[self.data['7 Ranges'] == "Moderate Gap Up"].shape[0]
                probability_out_of_group = (frequency_sum / Moderate_Gap_Up) * 100
            elif case == "Moderate Gap Up n Up Trend or Indecisive n Up":
                frequency_sum = self.data[
                    (self.data['7 Ranges'] == "Moderate Gap Up") &
                    ((self.data['Trend'] == "Up Trend") | (self.data['Trend'] == "Indecisive")) &
                    (self.data['Closed'] == "Up")
                ].shape[0]
                Moderate_Gap_Up_n_Up_Trend_or_Indecisive = self.data[
                    (self.data['7 Ranges'] == "Moderate Gap Up") &
                    ((self.data['Trend'] == "Up Trend") | (self.data['Trend'] == "Indecisive"))
                ].shape[0]
                probability_out_of_group = (frequency_sum / Moderate_Gap_Up_n_Up_Trend_or_Indecisive) * 100
            elif case == "Moderate Gap Up n Up Trend or Indecisive n Up or Flat Close":
                frequency_sum = self.data[
                    (self.data['7 Ranges'] == "Moderate Gap Up") &
                    ((self.data['Trend'] == "Up Trend") | (self.data['Trend'] == "Indecisive")) &
                    ((self.data['Closed'] == "Up") | (self.data['Closed'] == "Flat Close"))
                ].shape[0]
                Moderate_Gap_Up_n_Up_Trend_or_Indecisive = self.data[
                    (self.data['7 Ranges'] == "Moderate Gap Up") &
                    ((self.data['Trend'] == "Up Trend") | (self.data['Trend'] == "Indecisive"))
                ].shape[0]
                probability_out_of_group = (frequency_sum / Moderate_Gap_Up_n_Up_Trend_or_Indecisive) * 100
            elif case == "Moderate Gap Down":
                frequency_sum = self.data[self.data['7 Ranges'] == "Moderate Gap Down"].shape[0]
                probability_out_of_group = (frequency_sum / total_frequency) * 100
            elif case == "Moderate Gap Down n Up Trend":
                frequency_sum = self.data[(self.data['7 Ranges'] == "Moderate Gap Down") & (self.data['Trend'] == "Up Trend")].shape[0]
                Moderate_Gap_Down = self.data[self.data['7 Ranges'] == "Moderate Gap Down"].shape[0]
                probability_out_of_group = (frequency_sum / Moderate_Gap_Down) * 100
            elif case == "Moderate Gap Down n Down Trend":
                frequency_sum = self.data[(self.data['7 Ranges'] == "Moderate Gap Down") & (self.data['Trend'] == "Down Trend")].shape[0]
                Moderate_Gap_Down = self.data[self.data['7 Ranges'] == "Moderate Gap Down"].shape[0]
                probability_out_of_group = (frequency_sum / Moderate_Gap_Down) * 100
            elif case == "Moderate Gap Down n Indecisive":
                frequency_sum = self.data[(self.data['7 Ranges'] == "Moderate Gap Down") & (self.data['Trend'] == "Indecisive")].shape[0]
                Moderate_Gap_Down = self.data[self.data['7 Ranges'] == "Moderate Gap Down"].shape[0]
                probability_out_of_group = (frequency_sum / Moderate_Gap_Down) * 100
            elif case == "Moderate Gap Down n Down Trend or Indecisive":
                frequency_sum = self.data[
                    (self.data['7 Ranges'] == "Moderate Gap Down") &
                    ((self.data['Trend'] == "Down Trend") | (self.data['Trend'] == "Indecisive"))
                ].shape[0]
                Moderate_Gap_Down = self.data[self.data['7 Ranges'] == "Moderate Gap Down"].shape[0]
                probability_out_of_group = (frequency_sum / Moderate_Gap_Down) * 100
            elif case == "Moderate Gap Down n Down Trend or Indecisive n Down":
                frequency_sum = self.data[
                    (self.data['7 Ranges'] == "Moderate Gap Down") &
                    ((self.data['Trend'] == "Down Trend") | (self.data['Trend'] == "Indecisive")) &
                    (self.data['Closed'] == "Down")
                ].shape[0]
                Moderate_Gap_Down_n_Down_Trend_or_Indecisive = self.data[
                    (self.data['7 Ranges'] == "Moderate Gap Down") &
                    ((self.data['Trend'] == "Down Trend") | (self.data['Trend'] == "Indecisive"))
                ].shape[0]
                probability_out_of_group = (frequency_sum / Moderate_Gap_Down_n_Down_Trend_or_Indecisive) * 100
            elif case == "Moderate Gap Down n Down Trend or Indecisive n Down or Flat Close":
                frequency_sum = self.data[
                    (self.data['7 Ranges'] == "Moderate Gap Down") &
                    ((self.data['Trend'] == "Down Trend") | (self.data['Trend'] == "Indecisive")) &
                    ((self.data['Closed'] == "Down") | (self.data['Closed'] == "Flat Close"))
                ].shape[0]
                Moderate_Gap_Down_n_Down_Trend_or_Indecisive = self.data[
                    (self.data['7 Ranges'] == "Moderate Gap Down") &
                    ((self.data['Trend'] == "Down Trend") | (self.data['Trend'] == "Indecisive"))
                ].shape[0]
                probability_out_of_group = (frequency_sum / Moderate_Gap_Down_n_Down_Trend_or_Indecisive) * 100
            elif case == "Moderate Gap Down n Up Trend or Indecisive":
                frequency_sum = self.data[
                    (self.data['7 Ranges'] == "Moderate Gap Down") &
                    ((self.data['Trend'] == "Up Trend") | (self.data['Trend'] == "Indecisive"))
                ].shape[0]
                Moderate_Gap_Down = self.data[self.data['7 Ranges'] == "Moderate Gap Down"].shape[0]
                probability_out_of_group = (frequency_sum / Moderate_Gap_Down) * 100
            elif case == "Moderate Gap Down n Up Trend or Indecisive n Up":
                frequency_sum = self.data[
                    (self.data['7 Ranges'] == "Moderate Gap Down") &
                    ((self.data['Trend'] == "Up Trend") | (self.data['Trend'] == "Indecisive")) &
                    (self.data['Closed'] == "Up")
                ].shape[0]
                Moderate_Gap_Down_n_Up_Trend_or_Indecisive = self.data[
                    (self.data['7 Ranges'] == "Moderate Gap Down") &
                    ((self.data['Trend'] == "Up Trend") | (self.data['Trend'] == "Indecisive"))
                ].shape[0]
                probability_out_of_group = (frequency_sum / Moderate_Gap_Down_n_Up_Trend_or_Indecisive) * 100
            elif case == "Moderate Gap Down n Up Trend or Indecisive n Up or Flat Close":
                frequency_sum = self.data[
                    (self.data['7 Ranges'] == "Moderate Gap Down") &
                    ((self.data['Trend'] == "Up Trend") | (self.data['Trend'] == "Indecisive")) &
                    ((self.data['Closed'] == "Up") | (self.data['Closed'] == "Flat Close"))
                ].shape[0]
                Moderate_Gap_Down_n_Up_Trend_or_Indecisive = self.data[
                    (self.data['7 Ranges'] == "Moderate Gap Down") &
                    ((self.data['Trend'] == "Up Trend") | (self.data['Trend'] == "Indecisive"))
                ].shape[0]
                probability_out_of_group = (frequency_sum / Moderate_Gap_Down_n_Up_Trend_or_Indecisive) * 100
            elif case == "Flat Open":
                frequency_sum = self.data[self.data['7 Ranges'] == "Flat Open"].shape[0]
                probability_out_of_group = (frequency_sum / total_frequency) * 100
            elif case == "Flat Open n Up Trend":
                frequency_sum = self.data[(self.data['7 Ranges'] == "Flat Open") & (self.data['Trend'] == "Up Trend")].shape[0]
                Flat_Open = self.data[self.data['7 Ranges'] == "Flat Open"].shape[0]
                probability_out_of_group = (frequency_sum / Flat_Open) * 100
            elif case == "Flat Open n Down Trend":
                frequency_sum = self.data[(self.data['7 Ranges'] == "Flat Open") & (self.data['Trend'] == "Down Trend")].shape[0]
                Flat_Open = self.data[self.data['7 Ranges'] == "Flat Open"].shape[0]
                probability_out_of_group = (frequency_sum / Flat_Open) * 100
            elif case == "Flat Open n Indecisive":
                frequency_sum = self.data[(self.data['7 Ranges'] == "Flat Open") & (self.data['Trend'] == "Indecisive")].shape[0]
                Flat_Open = self.data[self.data['7 Ranges'] == "Flat Open"].shape[0]
                probability_out_of_group = (frequency_sum / Flat_Open) * 100
            elif case == "Flat Open n Down Trend n Up":
                frequency_sum = self.data[
                    (self.data['7 Ranges'] == "Flat Open") &
                    (self.data['Trend'] == "Down Trend") &
                    (self.data['Closed'] == "Up")
                ].shape[0]
                Flat_Open_n_Down_Trend = self.data[
                    (self.data['7 Ranges'] == "Flat Open") &
                    (self.data['Trend'] == "Down Trend")
                ].shape[0]
                probability_out_of_group = (frequency_sum / Flat_Open_n_Down_Trend) * 100
            elif case == "Flat Open n Down Trend or Indecisive":
                frequency_sum = self.data[
                    (self.data['7 Ranges'] == "Flat Open") &
                    ((self.data['Trend'] == "Down Trend") | (self.data['Trend'] == "Indecisive"))
                ].shape[0]
                Flat_Open = self.data[self.data['7 Ranges'] == "Flat Open"].shape[0]
                probability_out_of_group = (frequency_sum / Flat_Open) * 100
            elif case == "Flat Open n Down Trend or Indecisive n Up":
                frequency_sum = self.data[
                    (self.data['7 Ranges'] == "Flat Open") &
                    ((self.data['Trend'] == "Down Trend") | (self.data['Trend'] == "Indecisive")) &
                    (self.data['Closed'] == "Up")
                ].shape[0]
                Flat_Open_n_Down_Trend_or_Indecisive = self.data[
                    (self.data['7 Ranges'] == "Flat Open") &
                    ((self.data['Trend'] == "Down Trend") | (self.data['Trend'] == "Indecisive"))
                ].shape[0]
                probability_out_of_group = (frequency_sum / Flat_Open_n_Down_Trend_or_Indecisive) * 100
            elif case == "Flat Open n Down Trend or Indecisive n Down":
                frequency_sum = self.data[
                    (self.data['7 Ranges'] == "Flat Open") &
                    ((self.data['Trend'] == "Down Trend") | (self.data['Trend'] == "Indecisive")) &
                    (self.data['Closed'] == "Down")
                ].shape[0]
                Flat_Open_n_Down_Trend_or_Indecisive = self.data[
                    (self.data['7 Ranges'] == "Flat Open") &
                    ((self.data['Trend'] == "Down Trend") | (self.data['Trend'] == "Indecisive"))
                ].shape[0]
                probability_out_of_group = (frequency_sum / Flat_Open_n_Down_Trend_or_Indecisive) * 100
            elif case == "Flat Open n Up Trend n Down":
                frequency_sum = self.data[
                    (self.data['7 Ranges'] == "Flat Open") &
                    (self.data['Trend'] == "Up Trend") &
                    (self.data['Closed'] == "Down")
                ].shape[0]
                Flat_Open_n_Up_Trend = self.data[
                    (self.data['7 Ranges'] == "Flat Open") &
                    (self.data['Trend'] == "Up Trend")
                ].shape[0]
                probability_out_of_group = (frequency_sum / Flat_Open_n_Up_Trend) * 100
            elif case == "Flat Open n Up Trend or Indecisive":
                frequency_sum = self.data[
                    (self.data['7 Ranges'] == "Flat Open") &
                    ((self.data['Trend'] == "Up Trend") | (self.data['Trend'] == "Indecisive"))
                ].shape[0]
                Flat_Open = self.data[self.data['7 Ranges'] == "Flat Open"].shape[0]
                probability_out_of_group = (frequency_sum / Flat_Open) * 100
            elif case == "Flat Open n Up Trend or Indecisive n Up":
                frequency_sum = self.data[
                    (self.data['7 Ranges'] == "Flat Open") &
                    ((self.data['Trend'] == "Up Trend") | (self.data['Trend'] == "Indecisive")) &
                    (self.data['Closed'] == "Up")
                ].shape[0]
                Flat_Open_n_Up_Trend_or_Indecisive = self.data[
                    (self.data['7 Ranges'] == "Flat Open") &
                    ((self.data['Trend'] == "Up Trend") | (self.data['Trend'] == "Indecisive"))
                ].shape[0]
                probability_out_of_group = (frequency_sum / Flat_Open_n_Up_Trend_or_Indecisive) * 100
            elif case == "Flat Open n Up Trend or Indecisive n Down":
                frequency_sum = self.data[
                    (self.data['7 Ranges'] == "Flat Open") &
                    ((self.data['Trend'] == "Up Trend") | (self.data['Trend'] == "Indecisive")) &
                    (self.data['Closed'] == "Down")
                ].shape[0]
                Flat_Open_n_Up_Trend_or_Indecisive = self.data[
                    (self.data['7 Ranges'] == "Flat Open") &
                    ((self.data['Trend'] == "Up Trend") | (self.data['Trend'] == "Indecisive"))
                ].shape[0]
                probability_out_of_group = (frequency_sum / Flat_Open_n_Up_Trend_or_Indecisive) * 100

            # Append the result to additional_case_data
            additional_case_data.append([case, '', frequency_sum, probability_out_of_group, '', ''])

        # Create a DataFrame for additional cases
        additional_case_df = pd.DataFrame(additional_case_data, columns=['Cases', 'S.no.', 'Frequency', 'Probability Out of Group', 'Probability Out of Total', 'At Close'])

        # Concatenate the main case frequency and additional cases
        case_frequency = pd.concat([case_frequency, additional_case_df], ignore_index=True)

        return case_frequency
    
        pass
    @staticmethod
    def generate_json_for_all_tickers(config_file):
        # Load configuration from the .ini file
        config = configparser.ConfigParser()
        config.read(config_file)
        
        # Extract the list of symbols from the config file
        symbols = config.get('OHLC_Settings', 'symbol').split(',')
        all_tickers_data = []
        common_date_time = None

        # Define the path to the static directory
        static_dir = os.path.join(os.path.dirname(__file__), '..', 'static', 'indexstats')  # Navigate up one level to the app folder
        os.makedirs(static_dir, exist_ok=True)  # Ensure the directory exists

        # Loop through each symbol and generate analysis data
        for symbol in symbols:
            # Update the symbol in the config object
            config.set('OHLC_Settings', 'symbol', symbol.strip())
            
            # Save the updated config to a temporary file
            with open('temp_config.ini', 'w') as configfile:
                config.write(configfile)
            
            # Initialize OHLCAnalysis with the temporary config file
            ohlc_analysis = OHLCAnalysis('temp_config.ini')
            
            # Execute the analysis pipeline
            ohlc_analysis.download_data()
            ohlc_analysis.preprocess_data()
            ohlc_analysis.calculate_indicators()
            ohlc_analysis.assign_ranges()
            ohlc_analysis.trend_setter(M1=ohlc_analysis.threshold_m1, N1=ohlc_analysis.threshold_n1)
            ohlc_analysis.final_indicators(close_threshold=ohlc_analysis.close_threshold)
            ohlc_analysis.finalize_data()

            # Generate summary data for the current symbol
            last_day_data = ohlc_analysis.data.iloc[-1]
            seven_ranges_value = last_day_data['7 Ranges']
            trend_value = last_day_data['Trend']
            last_date = pd.to_datetime(last_day_data['Date'], format='%d-%m-%Y')

            # Fetch probabilities from the statistics sheet
            statistics_df = ohlc_analysis.create_statistics_sheet()
            filtered_stats = statistics_df[
                (statistics_df['Cases'].str.startswith(seven_ranges_value)) &
                (statistics_df['Cases'].str.contains(trend_value))
            ]
            up_probability = filtered_stats[filtered_stats['Cases'].str.endswith('Up')]['At Close'].values[0] if not filtered_stats[filtered_stats['Cases'].str.endswith('Up')].empty else 0
            down_probability = filtered_stats[filtered_stats['Cases'].str.endswith('Down')]['At Close'].values[0] if not filtered_stats[filtered_stats['Cases'].str.endswith('Down')].empty else 0
            flat_close_probability = filtered_stats[filtered_stats['Cases'].str.endswith('Flat Close')]['At Close'].values[0] if not filtered_stats[filtered_stats['Cases'].str.endswith('Flat Close')].empty else 0
            symbol_name = ohlc_analysis.reverse_symbol_mapping.get(symbol.strip(), symbol.strip())

            # Append the data for the current symbol to the list
            all_tickers_data.append({
                "Symbol": symbol_name,
                "Opening Scenario": seven_ranges_value.lower(),
                "Trend Observed": trend_value.lower(),
                "Upward Close": f"{up_probability:.2f}",
                "Downward Close": f"{down_probability:.2f}",
                "Flat Close": f"{flat_close_probability:.2f}"
            })

            # Extract the common date and time (use the first symbol's date)
            if common_date_time is None:
                month_name = last_date.strftime('%B')  # Get the full month name (e.g., February)
                year = last_date.year  # Extract the year
                current_time = datetime.now().strftime('%I:%M %p')  # Format: "12:30 PM"
                common_date_time = f"Generated on: {current_time}, at {month_name} {last_date.day}, {year}"

        # Add the common date and time to the JSON data
        json_output = {
            "Data Generated On": common_date_time,
            "Tickers": all_tickers_data
        }

        # Save the data to a JSON file in the static directory
        json_file_path = os.path.join(static_dir, 'data.json')
        with open(json_file_path, 'w') as json_file:
            json.dump(json_output, json_file, indent=4)
        print(f"JSON file saved at: {json_file_path}")