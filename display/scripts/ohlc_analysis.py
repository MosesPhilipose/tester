import os
import configparser
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import connection
from ..models import ReportTime, ReportDate, TickerData
import pytz

class OHLCAnalysis:
    ranges = ["High Gap Up", "Moderate Gap Up", "Flat Open", "Moderate Gap Down", "High Gap Down"]
    trends = ["Up Trend", "Down Trend", "Indecisive"]
    closes = ["Up", "Down", "Flat Close"]

    symbol_mapping = {
        "BANK_NIFTY": "^NSEBANK", "NIFTY_IT": "^CNXIT", "SENSEX": "^BSESN", "NIFTY_FINANCE": "^CNXFIN",
        "NIFTY50": "^NSEI", "CRUDE_OIL": "CL=F", "GOLD": "GC=F", "SILVER": "SI=F"
    }

    def __init__(self, config_file):
        self.analysis_to_case = {
            f"{r} n {t} n {c}": i + 1
            for i, (r, t, c) in enumerate((r, t, c) for r in self.ranges for t in self.trends for c in self.closes)
        }
        self.config = configparser.ConfigParser()
        self.config.read(config_file)

        self.symbol = self.config.get('OHLC_Settings', 'symbol')
        self.num_years = self.config.getint('OHLC_Settings', 'num_years')
        self.base_gap = self.config.getfloat('OHLC_Settings', 'base_gap')
        self.step_size = self.config.getfloat('OHLC_Settings', 'step_size')
        self.threshold_m1 = self.config.getfloat('OHLC_Settings', 'threshold_m1')
        self.threshold_n1 = self.config.getfloat('OHLC_Settings', 'threshold_n1')
        self.close_threshold = self.config.getfloat('OHLC_Settings', 'close_threshold')

        self.data = None
        self.reverse_symbol_mapping = {v: k for k, v in self.symbol_mapping.items()}

    def download_data(self, end_date=None):
        if end_date is None:
            end_date = timezone.now().strftime('%Y-%m-%d')
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
        start_date = (end_date_obj - timedelta(days=self.num_years * 365)).strftime('%Y-%m-%d')
        end_date = (end_date_obj + timedelta(days=1)).strftime('%Y-%m-%d')

        self.data = yf.download(self.symbol, start=start_date, end=end_date)
        self.data.reset_index(inplace=True)
        self.data['Date'] = pd.to_datetime(self.data['Date']).dt.strftime('%d-%m-%Y')

    def preprocess_data(self):
        if isinstance(self.data.columns, pd.MultiIndex):
            self.data.columns = [col[0] if isinstance(col, tuple) else col for col in self.data.columns]
        self.data.columns = [str(col).capitalize() if str(col) != 'Date' else 'Date' for col in self.data.columns]

        required_columns = ['Open', 'High', 'Low', 'Close']
        missing_columns = [col for col in required_columns if col not in self.data.columns]
        if missing_columns:
            raise KeyError(f"Missing required columns: {missing_columns}")
        self.data = self.data.dropna(subset=['Close'])

    def get_range(self, opening_per):
        if pd.isna(opening_per):
            return ""
        flat_open_min, flat_open_max = -self.base_gap, self.base_gap
        moderate_gap_up_min, moderate_gap_up_max = flat_open_max, flat_open_max + self.step_size
        moderate_gap_down_max, moderate_gap_down_min = flat_open_min, flat_open_min - self.step_size
        high_gap_up_min = moderate_gap_up_max
        high_gap_down_max = moderate_gap_down_min

        if flat_open_min <= opening_per <= flat_open_max:
            return "Flat Open"
        elif moderate_gap_up_min < opening_per <= moderate_gap_up_max:
            return "Moderate Gap Up"
        elif opening_per > high_gap_up_min:
            return "High Gap Up"
        elif moderate_gap_down_max > opening_per >= moderate_gap_down_min:
            return "Moderate Gap Down"
        elif opening_per < high_gap_down_max:
            return "High Gap Down"
        return ""

    def determine_trend(self, row):
        opening_per = row['Opening_per']
        low_per = row['Low_per']
        high_per = row['High_per']
        high_per_opening_per = row['High_per_Opening_per']
        low_per_opening_per = row['Low_per_Opening_per']
        m1 = self.threshold_m1
        n1 = self.threshold_n1

        if ((opening_per >= 0 and low_per >= m1 and not pd.isna(high_per_opening_per) and high_per_opening_per >= n1) or
            (opening_per > 0.25 and low_per >= m1 and not pd.isna(high_per_opening_per) and high_per_opening_per >= n1) or
            (-0.25 <= opening_per <= 0.25 and not pd.isna(high_per_opening_per) and high_per_opening_per >= n1 and
             not pd.isna(low_per_opening_per) and low_per_opening_per >= -n1) or
            (opening_per < 0 and high_per > m1 and not pd.isna(low_per_opening_per) and low_per_opening_per >= -n1)):
            return "Up Trend"
        elif ((opening_per >= 0 and low_per <= -m1 and not pd.isna(high_per_opening_per) and high_per_opening_per < n1) or
              (opening_per > 0.25 and low_per <= -m1 and not pd.isna(high_per_opening_per) and high_per_opening_per < n1) or
              (-0.25 <= opening_per <= 0.25 and not pd.isna(high_per_opening_per) and high_per_opening_per < n1 and
               not pd.isna(low_per_opening_per) and low_per_opening_per < -n1) or
              (opening_per < 0 and high_per <= -m1 and not pd.isna(low_per_opening_per) and low_per_opening_per < -n1)):
            return "Down Trend"
        elif ((opening_per >= 0 and low_per > -m1 and low_per < m1 and not pd.isna(high_per_opening_per) and high_per_opening_per >= n1) or
              (opening_per >= 0 and low_per >= m1 and not pd.isna(high_per_opening_per) and high_per_opening_per < n1) or
              (opening_per >= 0 and low_per > -m1 and low_per < m1 and not pd.isna(high_per_opening_per) and high_per_opening_per < n1) or
              (opening_per >= 0 and low_per <= -m1 and not pd.isna(high_per_opening_per) and high_per_opening_per >= n1) or
              (opening_per > 0.25 and -m1 <= low_per <= m1 and not pd.isna(high_per_opening_per) and high_per_opening_per >= n1) or
              (opening_per > 0.25 and low_per >= m1 and not pd.isna(high_per_opening_per) and high_per_opening_per < n1) or
              (opening_per > 0.25 and -m1 <= low_per <= m1 and not pd.isna(high_per_opening_per) and high_per_opening_per < n1) or
              (opening_per > 0.25 and low_per <= -m1 and not pd.isna(high_per_opening_per) and high_per_opening_per >= n1) or
              (opening_per < 0 and high_per <= -m1 and not pd.isna(low_per_opening_per) and low_per_opening_per >= -n1) or
              (opening_per < 0 and high_per > -m1 and high_per <= m1 and not pd.isna(low_per_opening_per) and low_per_opening_per < -n1) or
              (opening_per < 0 and high_per > -m1 and high_per <= m1 and not pd.isna(low_per_opening_per) and low_per_opening_per >= -n1) or
              (opening_per < 0 and high_per > m1 and not pd.isna(low_per_opening_per) and low_per_opening_per < -n1) or
              (opening_per < -0.25 and -m1 <= high_per <= m1 and not pd.isna(low_per_opening_per) and low_per_opening_per < -n1) or
              (opening_per < -0.25 and -m1 <= high_per <= m1 and not pd.isna(low_per_opening_per) and low_per_opening_per >= -n1) or
              (-0.25 <= opening_per <= 0.25 and not pd.isna(high_per_opening_per) and high_per_opening_per < n1 and
               not pd.isna(low_per_opening_per) and low_per_opening_per >= -n1)):
            return "Indecisive"
        return "No Trend"

    def process_data(self):
        previous_close = self.data['Close'].shift(1)
        self.data['Opening_Value'] = (self.data['Open'] - previous_close).round(2)
        self.data['Opening_per'] = ((self.data['Open'] - previous_close) / previous_close.replace(to_replace=0, value=np.nan) * 100).round(2)
        self.data['High_Close'] = (self.data['High'] - previous_close).round(2)
        self.data['Low_Close'] = (self.data['Low'] - previous_close).round(2)
        self.data['High_per'] = ((self.data['High'] - previous_close) / previous_close.replace(to_replace=0, value=np.nan) * 100).round(2)
        self.data['Low_per'] = ((self.data['Low'] - previous_close) / previous_close.replace(to_replace=0, value=np.nan) * 100).round(2)
        self.data['Close_Prev_Close_per'] = ((self.data['Close'] - previous_close) / previous_close.replace(to_replace=0, value=np.nan) * 100).round(2)

        self.data = self.data.assign(
            High_per_Opening_per=lambda x: np.where(x['Opening_per'] >= -0.25, (x['High_per'] - x['Opening_per']).round(2), np.nan),
            Low_per_Opening_per=lambda x: np.where(x['Opening_per'] <= 0.25, (x['Low_per'] - x['Opening_per']).round(2), np.nan),
            EOD_per_Gap_per=lambda x: ((x['Close_Prev_Close_per'] - x['Opening_per']) /
                                       x['Opening_per'].replace(to_replace=0, value=np.nan) * 100).round(2),
            Ranges_7=lambda x: x['Opening_per'].apply(self.get_range),
            Trend=lambda x: x.apply(self.determine_trend, axis=1),
            Closed=lambda x: np.where(x['Close_Prev_Close_per'] > self.close_threshold, "Up",
                                      np.where(x['Close_Prev_Close_per'] < -self.close_threshold, "Down", "Flat Close")),
            Day=lambda x: pd.to_datetime(x['Date'], format='%d-%m-%Y').dt.day_name()
        )

        self.data['Analysis'] = self.data['Ranges_7'] + " n " + self.data['Trend'] + " n " + self.data['Closed']
        self.data['Sr_no'] = self.data['Analysis'].map(self.analysis_to_case).fillna("")

        reordered_columns = [
            'Date', 'Day', 'Open', 'High', 'Low', 'Close', 'Opening_Value', 'Opening_per', 'Ranges_7',
            'High_Close', 'Low_Close', 'High_per', 'Low_per', 'High_per_Opening_per', 'Low_per_Opening_per',
            'Trend', 'Close_Prev_Close_per', 'EOD_per_Gap_per', 'Closed', 'Sr_no', 'Analysis'
        ]
        self.data = self.data[reordered_columns]

    def create_statistics_sheet(self):
        cf_base = pd.DataFrame({'Cases': list(self.analysis_to_case.keys()), 'S_no': list(self.analysis_to_case.values())})
        freq_df = self.data['Analysis'].value_counts().reset_index()
        freq_df.columns = ['Cases', 'Frequency']

        cf = (cf_base.merge(freq_df, on='Cases', how='left')
              .fillna(0)
              .assign(**{
                  '7 Ranges': lambda df: df['Cases'].str.split(' n ').str[0],
                  'Probability Out of Group': lambda df: (df['Frequency'] / df.groupby('7 Ranges')['Frequency'].transform('sum') * 100).round(2),
                  'Probability Out of Total': lambda df: (df['Frequency'] / df['Frequency'].sum() * 100).round(2),
                  'Trend': lambda df: df['Cases'].str.split(' n ').str[1],
                  'Closed': lambda df: df['Cases'].str.split(' n ').str[2],
                  'At Close': lambda df: (df['Frequency'] / df.groupby(['7 Ranges', 'Trend'])['Frequency'].transform('sum') * 100).round(2).fillna(0)
              })
              [['Cases', 'S_no', 'Frequency', 'Probability Out of Group', 'Probability Out of Total', 'At Close']])

        ranges, trends, closes = ["Moderate Gap Up", "Moderate Gap Down", "Flat Open"], ["Up Trend", "Down Trend", "Indecisive"], ["Up", "Down", "Flat Close"]
        additional_cases = ([r for r in ranges] +
                            [f"{r} n {t}" for r in ranges for t in trends] +
                            [f"{r} n {t1} or {t2}" for r in ranges for t1, t2 in [("Down Trend", "Indecisive"), ("Up Trend", "Indecisive")]] +
                            [f"{r} n {t1} or {t2} n {c}" for r in ranges for t1, t2 in [("Down Trend", "Indecisive"), ("Up Trend", "Indecisive")] for c in closes if not (r == "Flat Open" and t1 == "Up Trend" and c != "Down")] +
                            [f"{r} n Down Trend n Up" if r == "Flat Open" else f"{r} n Down Trend or Indecisive n Down or Flat Close" for r in ranges])

        def gen_cond(case):
            parts = case.split(" n ")
            r = parts[0]
            base_cond = lambda d: d['Ranges_7'] == r
            if len(parts) == 1:
                return base_cond, 'total'
            t = parts[1].split(" or ")
            t_cond = lambda d: d['Trend'].isin(t) if "or" in parts[1] else d['Trend'] == t[0]
            if len(parts) == 2:
                return lambda d: base_cond(d) & t_cond(d), r
            c = parts[2].split(" or ")
            return lambda d: base_cond(d) & t_cond(d) & d['Closed'].isin(c if "or" in parts[2] else [c[0]]), f"{r} n {parts[1]}"

        total_freq = self.data.shape[0]
        additional_data = [[case, '', (freq := self.data[cond(self.data)].shape[0]),
                            round(freq / (total_freq if denom == 'total' else self.data[gen_cond(denom)[0](self.data)].shape[0]) * 100, 2), '', '']
                           for case in additional_cases for cond, denom in [gen_cond(case)]]

        return pd.concat([cf, pd.DataFrame([['', '', '', '', '', '']], columns=cf.columns),
                          pd.DataFrame(additional_data, columns=['Cases', 'S_no', 'Frequency', 'Probability Out of Group', 'Probability Out of Total', 'At Close'])],
                         ignore_index=True)

    @staticmethod
    def initialize_database():
        """Create tables if they don’t exist."""
        with connection.cursor() as cursor:
            # Check if tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            
            if 'display_reporttime' not in tables:
                cursor.execute("""
                    CREATE TABLE display_reporttime (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        time TEXT NOT NULL,
                        created_at DATETIME NOT NULL
                    )
                """)
            if 'display_reportdate' not in tables:
                cursor.execute("""
                    CREATE TABLE display_reportdate (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT NOT NULL,
                        created_at DATETIME NOT NULL
                    )
                """)
            if 'display_tickerdata' not in tables:
                cursor.execute("""
                    CREATE TABLE display_tickerdata (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        opening_scenario TEXT NOT NULL,
                        trend_observed TEXT NOT NULL,
                        upward_close REAL NOT NULL,
                        downward_close REAL NOT NULL,
                        flat_close REAL NOT NULL,
                        created_at DATETIME NOT NULL
                    )
                """)
        print("Database tables initialized if they didn’t exist.")

    @staticmethod
    def generate_data_for_all_tickers(config_file):
        """Generate and save OHLC analysis data to SQLite, creating tables if needed."""
        config = configparser.ConfigParser()
        config.read(config_file)
        symbols = config.get('OHLC_Settings', 'symbol').split(',')
        
        # Check if tables exist; if not, create them
        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='display_tickerdata';")
            if not cursor.fetchone():
                OHLCAnalysis.initialize_database()
                print("First run: Tables created.")
            else:
                # Clear existing data for subsequent runs
                ReportTime.objects.all().delete()
                ReportDate.objects.all().delete()
                TickerData.objects.all().delete()
                print("Subsequent run: Existing data cleared.")

        # Store generation time and date
        now = timezone.now()
        local_tz = pytz.timezone('Asia/Kolkata')  # Replace with your timezone
        local_time = now.astimezone(local_tz)
        ReportTime.objects.create(time=local_time.strftime('%I:%M %p'))
        ReportDate.objects.create(date=now.strftime('%B %d, %Y'))  # e.g., "March 25, 2025"

        for symbol in symbols:
            symbol = symbol.strip()
            config.set('OHLC_Settings', 'symbol', symbol)
            with open('temp_config.ini', 'w') as configfile:
                config.write(configfile)

            ohlc_analysis = OHLCAnalysis('temp_config.ini')
            ohlc_analysis.download_data()
            ohlc_analysis.preprocess_data()
            ohlc_analysis.process_data()

            last_day_data = ohlc_analysis.data.iloc[-1]
            seven_ranges_value = last_day_data['Ranges_7']
            trend_value = last_day_data['Trend']

            statistics_df = ohlc_analysis.create_statistics_sheet()
            filtered_stats = statistics_df[
                (statistics_df['Cases'].str.startswith(seven_ranges_value)) &
                (statistics_df['Cases'].str.contains(trend_value))
            ]
            up_probability = filtered_stats[filtered_stats['Cases'].str.endswith('Up')]['At Close'].values[0] if not filtered_stats[filtered_stats['Cases'].str.endswith('Up')].empty else 0
            down_probability = filtered_stats[filtered_stats['Cases'].str.endswith('Down')]['At Close'].values[0] if not filtered_stats[filtered_stats['Cases'].str.endswith('Down')].empty else 0
            flat_close_probability = filtered_stats[filtered_stats['Cases'].str.endswith('Flat Close')]['At Close'].values[0] if not filtered_stats[filtered_stats['Cases'].str.endswith('Flat Close')].empty else 0
            
            symbol_name = ohlc_analysis.reverse_symbol_mapping.get(symbol, symbol)

            TickerData.objects.create(
                symbol=symbol_name,
                opening_scenario=seven_ranges_value.lower(),
                trend_observed=trend_value.lower(),
                upward_close=float(up_probability),
                downward_close=float(down_probability),
                flat_close=float(flat_close_probability)
            )
        
        print("OHLC analysis data saved to SQLite: ReportTime, ReportDate, and TickerData tables.")
