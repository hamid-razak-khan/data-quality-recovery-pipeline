from django.urls import path
from apps.processing.views import ProcessedOrderListView, ProcessedOrderDetailView

urlpatterns = [
    path('', ProcessedOrderListView.as_view(), name='processed-orders-list'),
    path('<str:order_id>/', ProcessedOrderDetailView.as_view(), name='processed-order-detail'),
]
