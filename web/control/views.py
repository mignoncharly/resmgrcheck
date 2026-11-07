from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

@require_GET
def health(request):return JsonResponse({'status':'alive'})

@require_GET
def readiness(request):
    try:
        with connection.cursor() as cursor:cursor.execute('SELECT 1');cursor.fetchone()
    except Exception:return JsonResponse({'status':'unavailable'},status=503)
    return JsonResponse({'status':'ready'})

@require_GET
def home(request):return render(request,'control/home.html')
