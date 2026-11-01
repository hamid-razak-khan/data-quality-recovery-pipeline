from rest_framework import generics, views, status
from rest_framework.response import Response
from django.db.models import Count
from apps.quarantine.models import QuarantineRecord
from apps.quarantine.serializers import (
    QuarantineRecordListSerializer,
    QuarantineRecordDetailSerializer,
)
from data_pipeline.engine.quarantine_manager import QuarantineManager


class QuarantineRecordListView(generics.ListAPIView):
    """
    GET /api/quarantine/
    Supports filtering by status, error_code, validation_stage, run_id, and search.
    """
    serializer_class = QuarantineRecordListSerializer

    def get_queryset(self):
        qs = QuarantineRecord.objects.all().order_by('-created_at')

        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param.upper())

        error_code = self.request.query_params.get('error_code')
        if error_code:
            qs = qs.filter(error_code=error_code)

        stage = self.request.query_params.get('stage')
        if stage:
            qs = qs.filter(validation_stage=stage.upper())

        run_id = self.request.query_params.get('run_id')
        if run_id:
            qs = qs.filter(run_id=run_id)

        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(record_id__icontains=search)

        return qs


class QuarantineRecordDetailView(generics.RetrieveAPIView):
    """
    GET /api/quarantine/{id}/
    Returns complete record including raw payload, corrected payload, validation errors, and audit history.
    """
    queryset = QuarantineRecord.objects.all()
    serializer_class = QuarantineRecordDetailSerializer
    lookup_field = 'quarantine_id'


class QuarantineCorrectionView(views.APIView):
    """
    PATCH /api/quarantine/{id}/correct/
    Applies operator manual corrections to a quarantined record.
    Transitions status to CORRECTED and preserves correction history.
    """
    def patch(self, request, quarantine_id, *args, **kwargs):
        corrected_record = request.data.get('corrected_record')
        if not corrected_record or not isinstance(corrected_record, dict):
            return Response({
                'error': 'Missing or invalid corrected_record dictionary in request payload.'
            }, status=status.HTTP_400_BAD_REQUEST)

        operator_name = request.data.get('operator_name', 'operator')
        notes = request.data.get('notes', 'Operator correction via Operations UI')

        try:
            updated_record = QuarantineManager.apply_correction(
                quarantine_id=quarantine_id,
                corrected_payload=corrected_record,
                operator_name=operator_name,
                notes=notes
            )
            return Response({
                'message': 'Record corrected successfully. Ready for controlled replay.',
                'record': QuarantineRecordDetailSerializer(updated_record).data
            }, status=status.HTTP_200_OK)
        except QuarantineRecord.DoesNotExist:
            return Response({
                'error': f"Quarantine record '{quarantine_id}' not found."
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class QuarantineSummaryView(views.APIView):
    """
    GET /api/quarantine/summary/
    Returns aggregated metrics and distributions for quarantine operations.
    """
    def get(self, request, *args, **kwargs):
        total_quarantined = QuarantineRecord.objects.count()

        status_counts = dict(
            QuarantineRecord.objects.values_list('status').annotate(c=Count('quarantine_id'))
        )

        error_code_counts = dict(
            QuarantineRecord.objects.values_list('error_code').annotate(c=Count('quarantine_id')).order_by('-c')[:10]
        )

        stage_counts = dict(
            QuarantineRecord.objects.values_list('validation_stage').annotate(c=Count('quarantine_id'))
        )

        eligible_for_replay = status_counts.get('CORRECTED', 0)

        return Response({
            'total_quarantined': total_quarantined,
            'status_breakdown': status_counts,
            'top_error_codes': error_code_counts,
            'stage_breakdown': stage_counts,
            'eligible_for_replay': eligible_for_replay,
        }, status=status.HTTP_200_OK)
