from rest_framework import views, generics, status
from rest_framework.response import Response
from apps.replay.models import ReplayHistory
from apps.replay.serializers import ReplayHistorySerializer
from data_pipeline.engine.replay_engine import ReplayEngine


class ReplayTriggerView(views.APIView):
    """
    POST /api/replay/
    Triggers controlled replay of corrected quarantine records.
    CRITICAL RULE: Replays ONLY records where status == 'CORRECTED'.
    Never reprocesses previously successful records.
    Payload:
    {
        "record_ids": ["uuid1", "uuid2"], // Optional: specific quarantine record IDs
        "replay_all": true/false,          // Optional: replay all eligible corrected records
        "run_id": "uuid"                   // Optional
    }
    """
    def post(self, request, *args, **kwargs):
        record_ids = request.data.get('record_ids')
        replay_all = request.data.get('replay_all', False)
        run_id = request.data.get('run_id')

        if not record_ids and not replay_all:
            return Response({
                'error': 'Must provide either a list of record_ids or replay_all=true.'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = ReplayEngine.execute_replay(
                quarantine_ids=record_ids,
                replay_all_eligible=replay_all,
                run_id=run_id,
            )
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': f"Replay execution failed: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ReplayHistoryListView(generics.ListAPIView):
    """
    GET /api/replay/history/
    Lists historical replay executions with metrics.
    """
    serializer_class = ReplayHistorySerializer

    def get_queryset(self):
        return ReplayHistory.objects.all().order_by('-started_at')


class ReplayDetailView(generics.RetrieveAPIView):
    """
    GET /api/replay/{replay_id}/
    Returns details of a specific replay batch.
    """
    queryset = ReplayHistory.objects.all()
    serializer_class = ReplayHistorySerializer
    lookup_field = 'replay_id'
