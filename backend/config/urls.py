from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/ingestion/', include('apps.ingestion.urls')),
    path('api/pipeline/', include('apps.ingestion.pipeline_urls')),
    path('api/quarantine/', include('apps.quarantine.urls')),
    path('api/replay/', include('apps.replay.urls')),
    path('api/processed/', include('apps.processing.urls')),
    path('api/metrics/', include('apps.monitoring.urls')),
    path('api/data/', include('apps.processing.data_urls')),
]
