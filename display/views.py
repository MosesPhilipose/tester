import os
from django.http import JsonResponse, HttpResponse
from django.views.decorators.cache import never_cache
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from pathlib import Path
from display.scripts.ohlc_analysis import OHLCAnalysis

BASE_DIR = Path(__file__).resolve().parent.parent

def market_analysis(request):
    return render(request, 'indexstats/market_analysis.html')

@csrf_exempt
def refresh_data(request):
    if request.method == 'POST':
        try:
            # Path to your configuration file
            config_file = os.path.join(BASE_DIR, 'display', 'configs', 'config.ini')
            
            # Run the Python script to update data.json
            OHLCAnalysis.generate_json_for_all_tickers(config_file)
            
            # Return success response
            return JsonResponse({"status": "success", "message": "Data refreshed successfully!","TICKER": "All"}, status=200)
        except Exception as e:
            # Return error response
            return JsonResponse({"status": "error_ohlc", "message": str(e)}, status=500)
    else:
        return JsonResponse({"status": "error", "message": "Invalid request method"}, status=400)
    
@never_cache
def serve_data_json(request):
    """
    Serves the data.json file without caching.
    """
    # Define the path to the data.json file
    json_file_path = os.path.join(settings.STATIC_ROOT, 'indexstats', 'data.json')
    
    # Check if the file exists
    if not os.path.exists(json_file_path):
        return JsonResponse({"error": "data.json not found"}, status=404)
    
    # Read and return the contents of the file
    with open(json_file_path, 'r') as file:
        json_content = file.read()
    
    # Return the JSON content with the appropriate MIME type
    return HttpResponse(json_content, content_type='application/json')