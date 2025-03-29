import os
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from pathlib import Path
from .scripts.ohlc_analysis import OHLCAnalysis
from .models import ReportTime, ReportDate, TickerData

BASE_DIR = Path(__file__).resolve().parent.parent

def market_analysis(request):
    """Render the market analysis dashboard."""
    return render(request, 'indexstats/market_analysis.html')

@csrf_exempt
def refresh_data(request):
    """Handle POST request to refresh ticker data in SQLite."""
    if request.method == 'POST':
        try:
            config_file = os.path.join(BASE_DIR, 'display', 'configs', 'config.ini')
            OHLCAnalysis.generate_data_for_all_tickers(config_file)
            return JsonResponse({
                "status": "success",
                "message": "Data refreshed successfully!",
                "TICKER": "All"
            }, status=200)
        except Exception as e:
            return JsonResponse({"status": "error_ohlc", "message": str(e)}, status=500)
    else:
        return JsonResponse({"status": "error", "message": "Invalid request method"}, status=400)

@never_cache
def get_ticker_data(request):
    """Serve the latest ticker data from SQLite as JSON."""
    try:
        # If no data exists, prompt user to refresh
        if not TickerData.objects.exists():
            return JsonResponse({
                "status": "no_data",
                "message": "No data available. Please click 'Refresh Data' to initialize the database."
            }, status=200)

        report_time = ReportTime.objects.latest('created_at') if ReportTime.objects.exists() else None
        report_date = ReportDate.objects.latest('created_at') if ReportDate.objects.exists() else None
        tickers = TickerData.objects.all()

        data = {
            "Generated on": f"Generated on: {report_time.time if report_time else 'N/A'}, at {report_date.date if report_date else 'N/A'}",
            "Tickers": [
                {
                    "Symbol": ticker.symbol,
                    "Opening Scenario": ticker.opening_scenario,
                    "Trend Observed": ticker.trend_observed,
                    "Upward Close": f"{ticker.upward_close:.2f}",
                    "Downward Close": f"{ticker.downward_close:.2f}",
                    "Flat Close": f"{ticker.flat_close:.2f}"
                } for ticker in tickers
            ]
        }
        response = JsonResponse(data)
        response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        return response
    except Exception as e:
        return JsonResponse({"status": "error", "message": f"Failed to fetch ticker data: {str(e)}"}, status=500)
