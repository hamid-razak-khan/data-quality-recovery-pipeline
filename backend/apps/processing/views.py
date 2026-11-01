import csv
import os
from django.http import HttpResponse
from django.conf import settings
from django.db.models import Q
from rest_framework import generics, views, status
from rest_framework.response import Response
from apps.processing.models import ProcessedOrder, Customer
from apps.processing.serializers import ProcessedOrderSerializer
from data_pipeline.generators.generate_data import SyntheticDataGenerator


class ProcessedOrderListView(generics.ListAPIView):
    """
    GET /api/processed/
    Lists published processed records with search, filtering, and optional CSV export.
    QueryParams:
    - search: string (matches record_id, entity_id, event_type, order_id, product_name)
    - status: string (status or order_status)
    - customer_id / entity_id: string
    - start_date: ISO date
    - end_date: ISO date
    - export: 'csv' (triggers CSV file download)
    """
    serializer_class = ProcessedOrderSerializer

    def get_queryset(self):
        qs = ProcessedOrder.objects.select_related('customer').all().order_by('-processed_at')

        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(order_id__icontains=search) |
                Q(reading_id__icontains=search) |
                Q(asset_code__icontains=search) |
                Q(metric_name__icontains=search) |
                Q(entity_id__icontains=search) |
                Q(event_type__icontains=search) |
                Q(product_name__icontains=search) |
                Q(customer_id__icontains=search)
            )

        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(
                Q(status__iexact=status_param) |
                Q(quality_flag__iexact=status_param) |
                Q(order_status__iexact=status_param)
            )

        cust_id = self.request.query_params.get('customer_id') or self.request.query_params.get('entity_id') or self.request.query_params.get('asset_code')
        if cust_id:
            qs = qs.filter(Q(customer_id=cust_id) | Q(entity_id=cust_id) | Q(asset_code=cust_id))

        start_date = self.request.query_params.get('start_date')
        if start_date:
            qs = qs.filter(Q(order_date__gte=start_date) | Q(event_timestamp__gte=start_date) | Q(observed_at__gte=start_date))

        end_date = self.request.query_params.get('end_date')
        if end_date:
            qs = qs.filter(Q(order_date__lte=end_date) | Q(event_timestamp__lte=end_date) | Q(observed_at__lte=end_date))

        return qs

    def list(self, request, *args, **kwargs):
        if request.query_params.get('export') == 'csv':
            return self._export_csv(self.get_queryset()[:10000])
        return super().list(request, *args, **kwargs)

    def _export_csv(self, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="processed_records_export.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'record_id', 'entity_id', 'event_type', 'amount',
            'quantity', 'event_timestamp', 'status',
            'source_file', 'source_row_number', 'run_id', 'processed_at'
        ])

        for o in queryset:
            writer.writerow([
                o.order_id,
                o.entity_id or o.customer_id or '',
                o.event_type or o.product_name or '',
                o.amount if o.amount is not None else o.total_amount,
                o.quantity,
                o.event_timestamp.isoformat() if o.event_timestamp else (o.order_date.isoformat() if o.order_date else ''),
                o.status or o.order_status or '',
                o.source_file,
                o.source_row_number,
                str(o.run_id),
                o.processed_at.isoformat() if o.processed_at else '',
            ])

        return response


class ProcessedOrderDetailView(generics.RetrieveAPIView):
    """
    GET /api/processed/{id}/
    Returns details of single processed record.
    """
    queryset = ProcessedOrder.objects.select_related('customer').all()
    serializer_class = ProcessedOrderSerializer
    lookup_field = 'order_id'


class DataGenerateView(views.APIView):
    """
    POST /api/data/generate/
    Generates synthetic orders and customer records for testing.
    Payload: { "records": 1000, "seed": 42, "invalid_ratio": 0.10 }
    """
    def post(self, request, *args, **kwargs):
        records = int(request.data.get('records', 1000))
        seed = int(request.data.get('seed', 42))
        invalid_ratio = float(request.data.get('invalid_ratio', 0.10))

        records = max(10, min(records, 500000))
        invalid_ratio = max(0.0, min(invalid_ratio, 0.50))

        try:
            output_path, count = SyntheticDataGenerator.generate(
                record_count=records,
                seed=seed,
                invalid_ratio=invalid_ratio
            )
            return Response({
                'message': f"Generated {count} synthetic order records successfully.",
                'file_name': os.path.basename(output_path),
                'file_path': output_path,
                'record_count': count,
                'invalid_ratio': invalid_ratio,
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
