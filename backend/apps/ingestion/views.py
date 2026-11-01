import os
import uuid
import hashlib
import json
import pandas as pd
from django.conf import settings
from rest_framework import status, views, generics
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from apps.ingestion.models import SourceFile, PipelineRun
from apps.ingestion.serializers import SourceFileSerializer, PipelineRunSerializer
from apps.quarantine.models import QuarantineRecord
from data_pipeline.engine.ingestion import IngestionEngine


class FileUploadView(views.APIView):
    """
    POST /api/ingestion/upload/
    Accepts CSV or JSON file uploads, validates file format and size,
    saves the raw file to backend/storage/raw/, and extracts a preview snippet.
    """
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response({'error': 'No file was provided in the request.'}, status=status.HTTP_400_BAD_REQUEST)

        filename = uploaded_file.name
        file_ext = os.path.splitext(filename)[1].lower()

        if file_ext not in ('.csv', '.json'):
            return Response({
                'error': f"Unsupported file extension '{file_ext}'. Allowed formats: .csv, .json"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Max file size: 50MB
        if uploaded_file.size > 50 * 1024 * 1024:
            return Response({
                'error': 'File size exceeds maximum allowable limit of 50MB.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Read content and compute hash
        content = uploaded_file.read()
        file_hash = hashlib.sha256(content).hexdigest()

        # Save to storage/raw/
        os.makedirs(settings.STORAGE_RAW, exist_ok=True)
        unique_name = f"{uuid.uuid4().hex[:8]}_{filename}"
        dest_path = os.path.join(settings.STORAGE_RAW, unique_name)
        with open(dest_path, 'wb') as f:
            f.write(content)

        # Generate sample preview (up to 5 records)
        preview_records = []
        try:
            if file_ext == '.csv':
                df = pd.read_csv(dest_path, nrows=5, dtype=str, keep_default_na=False)
                preview_records = df.to_dict(orient='records')
            elif file_ext == '.json':
                with open(dest_path, 'r', encoding='utf-8') as jf:
                    data = json.load(jf)
                    if isinstance(data, list):
                        preview_records = data[:5]
                    else:
                        preview_records = [data]
        except Exception as e:
            preview_records = [{'warning': f'Could not generate preview: {str(e)}'}]

        source_file = SourceFile.objects.create(
            filename=filename,
            file_path=dest_path,
            file_format=file_ext[1:].upper(),
            file_size_bytes=uploaded_file.size,
            file_hash=file_hash,
            status='UPLOADED',
        )

        return Response({
            'message': 'File uploaded successfully',
            'file': SourceFileSerializer(source_file).data,
            'preview': preview_records,
        }, status=status.HTTP_201_CREATED)


class PipelineRunTriggerView(views.APIView):
    """
    POST /api/pipeline/run/
    Triggers end-to-end ingestion pipeline execution on an uploaded file.
    Payload: { "file_id": "...", "batch_size": 5000 } or { "file_path": "..." }
    """
    parser_classes = [JSONParser]

    def post(self, request, *args, **kwargs):
        file_id = request.data.get('file_id')
        file_path = request.data.get('file_path')
        batch_size = int(request.data.get('batch_size', 5000))
        schema_name = request.data.get('schema_name')

        if file_id:
            try:
                sf = SourceFile.objects.get(file_id=file_id)
                target_path = sf.file_path
                filename = sf.filename
            except SourceFile.DoesNotExist:
                return Response({'error': f"SourceFile with ID '{file_id}' not found."}, status=status.HTTP_404_NOT_FOUND)
        elif file_path:
            target_path = file_path
            filename = os.path.basename(file_path)
        else:
            return Response({'error': 'Either file_id or file_path must be provided.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = IngestionEngine.run_pipeline(
                file_path=target_path,
                filename=filename,
                batch_size=batch_size,
                schema_name=schema_name,
            )
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': f"Pipeline execution failed: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PipelineRunListView(generics.ListAPIView):
    """
    GET /api/pipeline/runs/
    Lists historical pipeline execution runs with pagination and filtering.
    """
    serializer_class = PipelineRunSerializer

    def get_queryset(self):
        qs = PipelineRun.objects.all().order_by('-start_time')
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(run_status=status_filter.upper())
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(filename__icontains=search)
        return qs


class PipelineRunDetailView(views.APIView):
    """
    GET /api/pipeline/runs/{run_id}/
    Provides detailed execution report and error reconciliation for a specific run.
    """
    def get(self, request, run_id, *args, **kwargs):
        try:
            run = PipelineRun.objects.get(run_id=run_id)
        except PipelineRun.DoesNotExist:
            return Response({'error': f"Pipeline run '{run_id}' not found."}, status=status.HTTP_404_NOT_FOUND)

        # Quarantined breakdown for this run
        quarantine_errors = QuarantineRecord.objects.filter(run_id=run.run_id)
        error_breakdown = {}
        for q in quarantine_errors:
            error_breakdown[q.error_code] = error_breakdown.get(q.error_code, 0) + 1

        reconciliation = {
            'total_input_records': run.total_records,
            'valid_records': run.valid_records,
            'quarantined_records': run.rejected_records,
            'formula_balance': run.total_records == (run.valid_records + run.rejected_records),
            'execution_duration_sec': run.execution_duration,
            'records_per_second': round(run.total_records / run.execution_duration, 2) if run.execution_duration > 0 else 0,
        }

        return Response({
            'run': PipelineRunSerializer(run).data,
            'reconciliation': reconciliation,
            'quarantine_error_breakdown': error_breakdown,
        }, status=status.HTTP_200_OK)
