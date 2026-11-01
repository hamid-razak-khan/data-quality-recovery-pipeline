from rest_framework import views, status
from rest_framework.response import Response
from django.db.models import Sum, Count, Avg, Max, Q
from apps.ingestion.models import PipelineRun, SourceRecord
from apps.processing.models import ProcessedOrder
from apps.quarantine.models import QuarantineRecord
from apps.replay.models import ReplayHistory
from apps.ingestion.serializers import PipelineRunSerializer


class MetricsDashboardView(views.APIView):
    """
    GET /api/metrics/
    Aggregates all live data engineering operational metrics for the React Dashboard.
    All figures are derived directly from PostgreSQL queries.
    Supports filtering trend metrics by start_date, end_date, source_file, schema, and status.
    """
    def get(self, request, *args, **kwargs):
        # 1. Ingestion totals from PipelineRun
        run_aggregates = PipelineRun.objects.aggregate(
            total_in=Sum('total_records'),
            valid_in=Sum('valid_records'),
            rejected_in=Sum('rejected_records'),
        )
        total_records_received = run_aggregates['total_in'] or 0
        cumulative_valid = run_aggregates['valid_in'] or 0
        cumulative_quarantined = run_aggregates['rejected_in'] or 0

        # 2. Target database counts (distinct published canonical records)
        successfully_processed = ProcessedOrder.objects.count()

        # 3. Quarantine states breakdown
        quarantine_counts = dict(
            QuarantineRecord.objects.values_list('status').annotate(c=Count('quarantine_id'))
        )
        quarantined_pending = quarantine_counts.get('PENDING', 0)
        quarantined_corrected = quarantine_counts.get('CORRECTED', 0)
        replayed_records = quarantine_counts.get('REPLAYED', 0)
        failed_records = quarantine_counts.get('FAILED', 0)
        total_active_quarantine = quarantined_pending + quarantined_corrected + failed_records
        total_quarantine_records = QuarantineRecord.objects.count()

        # 4. Overall quality rate & published yield
        if total_records_received > 0:
            first_pass_quality_rate = round((cumulative_valid / total_records_received) * 100, 2)
            unique_published_yield = round((successfully_processed / total_records_received) * 100, 2)
        else:
            first_pass_quality_rate = 100.0 if successfully_processed > 0 else 0.0
            unique_published_yield = 100.0 if successfully_processed > 0 else 0.0

        # 5. Latest pipeline run
        latest_run_obj = PipelineRun.objects.order_by('-start_time').first()
        latest_run = PipelineRunSerializer(latest_run_obj).data if latest_run_obj else None

        # 6. Recent 5 pipeline runs
        recent_runs = PipelineRunSerializer(
            PipelineRun.objects.order_by('-start_time')[:5], many=True
        ).data

        # 7. Quality Trend with dynamic filters
        trend_qs = PipelineRun.objects.all().order_by('-start_time')

        start_date = request.query_params.get('start_date')
        if start_date:
            trend_qs = trend_qs.filter(start_time__gte=start_date)

        end_date = request.query_params.get('end_date')
        if end_date:
            trend_qs = trend_qs.filter(start_time__lte=end_date)

        source_file = request.query_params.get('source_file')
        if source_file:
            trend_qs = trend_qs.filter(filename__icontains=source_file)

        status_param = request.query_params.get('status')
        if status_param:
            trend_qs = trend_qs.filter(run_status=status_param)

        schema_param = request.query_params.get('schema')
        if schema_param:
            trend_qs = trend_qs.filter(metadata__schema_detected=schema_param)

        trend_runs = list(trend_qs[:15])

        quality_trends = []
        for r in reversed(trend_runs):
            schema_name = 'generic'
            if r.metadata and isinstance(r.metadata, dict):
                schema_name = r.metadata.get('schema_detected', 'generic')
            else:
                fn = (r.filename or '').lower()
                if 'telemetry' in fn:
                    schema_name = 'telemetry'
                elif 'generic' in fn:
                    schema_name = 'generic'
                elif 'order' in fn:
                    schema_name = 'ecommerce'

            dur = float(r.execution_duration) if r.execution_duration else 0.0
            throughput = round(r.total_records / dur, 1) if dur > 0 and r.total_records else 0.0

            quality_trends.append({
                'run_id': str(r.run_id)[:8],
                'full_run_id': str(r.run_id),
                'filename': r.filename,
                'schema': schema_name,
                'valid_records': r.valid_records,
                'rejected_records': r.rejected_records,
                'total_records': r.total_records,
                'execution_duration': dur,
                'throughput_rps': throughput,
                'run_status': r.run_status,
                'start_time': r.start_time.strftime('%Y-%m-%d %H:%M'),
                'timestamp_iso': r.start_time.isoformat(),
            })

        # 8. Top Quarantine Error Causes (Counts, Percentages, Active vs Historical)
        error_breakdown_raw = QuarantineRecord.objects.values('error_code').annotate(
            total=Count('quarantine_id'),
            active=Count('quarantine_id', filter=~Q(status='REPLAYED')),
            historical=Count('quarantine_id', filter=Q(status='REPLAYED')),
        ).order_by('-total')

        error_breakdown = [
            {
                'error_code': item['error_code'],
                'count': item['total'],
                'active_count': item['active'],
                'historical_count': item['historical'],
                'percentage': round((item['total'] / total_quarantine_records) * 100, 1) if total_quarantine_records > 0 else 0.0,
                'active_percentage': round((item['active'] / total_active_quarantine) * 100, 1) if total_active_quarantine > 0 else 0.0,
            }
            for item in error_breakdown_raw[:8]
        ]

        # 9. Performance Analytics (Throughput & Duration)
        perf_agg = PipelineRun.objects.filter(execution_duration__gt=0).aggregate(
            total_duration=Sum('execution_duration'),
            avg_duration=Avg('execution_duration'),
            total_records=Sum('total_records'),
            max_duration=Max('execution_duration'),
        )
        total_dur = float(perf_agg['total_duration'] or 0.0)
        avg_dur = round(float(perf_agg['avg_duration'] or 0.0), 2)
        total_perf_recs = perf_agg['total_records'] or 0
        avg_throughput = round(total_perf_recs / total_dur, 1) if total_dur > 0 else 0.0

        latest_dur = float(latest_run_obj.execution_duration) if latest_run_obj and latest_run_obj.execution_duration else 0.0
        latest_throughput = round(latest_run_obj.total_records / latest_dur, 1) if latest_run_obj and latest_dur > 0 and latest_run_obj.total_records else 0.0

        performance = {
            'avg_throughput_rps': avg_throughput,
            'latest_throughput_rps': latest_throughput,
            'avg_duration_seconds': avg_dur,
            'total_duration_seconds': round(total_dur, 2),
            'total_batches_executed': PipelineRun.objects.count(),
        }

        # 10. Database-Driven Reconciliation Ledger
        idempotent_updates = max(0, cumulative_valid - successfully_processed)
        reconciliation_ledger = {
            'total_source_records_ingested': total_records_received,
            'valid_at_ingestion': cumulative_valid,
            'rejected_at_ingestion': cumulative_quarantined,
            'ingestion_formula_balanced': total_records_received == (cumulative_valid + cumulative_quarantined),
            'unique_target_published': successfully_processed,
            'idempotent_deduplicated': idempotent_updates,
            'total_quarantined_stored': total_quarantine_records,
            'successfully_replayed_recovered': replayed_records,
            'active_quarantine_remaining': total_active_quarantine,
            'quarantine_formula_balanced': total_quarantine_records == (replayed_records + total_active_quarantine),
        }

        # 11. Filter options for dynamic UI controls
        available_files = list(PipelineRun.objects.values_list('filename', flat=True).distinct()[:25])
        available_schemas = ['generic', 'telemetry', 'ecommerce']
        available_statuses = ['COMPLETED', 'COMPLETED_WITH_ERRORS', 'FAILED']

        # 12. Canonical Record Status Distribution
        status_counts = {}
        for item in ProcessedOrder.objects.values('status', 'order_status', 'quality_flag').annotate(c=Count('order_id')):
            st = item['quality_flag'] or item['status'] or item['order_status'] or 'UNKNOWN'
            status_counts[st] = status_counts.get(st, 0) + item['c']
        status_distribution = [
            {'status': k, 'count': v}
            for k, v in sorted(status_counts.items(), key=lambda x: x[1], reverse=True)
        ]

        return Response({
            'kpis': {
                'total_records_received': total_records_received,
                'cumulative_valid': cumulative_valid,
                'cumulative_quarantined': cumulative_quarantined,
                'successfully_processed': successfully_processed,
                'idempotent_updates': idempotent_updates,
                'active_quarantine': total_active_quarantine,
                'replayed_records': replayed_records,
                'failed_records': failed_records,
                'success_rate_percent': first_pass_quality_rate,
                'unique_published_yield': unique_published_yield,
            },
            'performance': performance,
            'reconciliation_ledger': reconciliation_ledger,
            'filter_options': {
                'files': available_files,
                'schemas': available_schemas,
                'statuses': available_statuses,
            },
            'latest_run': latest_run,
            'recent_runs': recent_runs,
            'quality_trends': quality_trends,
            'error_breakdown': error_breakdown,
            'status_distribution': status_distribution,
        }, status=status.HTTP_200_OK)


class ReconciliationReportView(views.APIView):
    """
    GET /api/metrics/reconciliation/
    Generates strict data engineering reconciliation balance:
    1. Total Input = Valid Records + Invalid Records
    2. Published Records = Unique Target Records + Idempotent Updates
    3. Quarantined Records = Successfully Replayed + Active Remaining
    """
    def get(self, request, *args, **kwargs):
        runs = PipelineRun.objects.all().order_by('-start_time')

        run_reconciliations = []
        overall_input = 0
        overall_valid = 0
        overall_rejected = 0

        for r in runs:
            overall_input += r.total_records
            overall_valid += r.valid_records
            overall_rejected += r.rejected_records

            is_balanced = (r.total_records == (r.valid_records + r.rejected_records))
            schema_name = 'generic'
            if r.metadata and isinstance(r.metadata, dict):
                schema_name = r.metadata.get('schema_detected', 'generic')
            else:
                fn = (r.filename or '').lower()
                if 'telemetry' in fn:
                    schema_name = 'telemetry'
                elif 'order' in fn:
                    schema_name = 'ecommerce'

            run_reconciliations.append({
                'run_id': str(r.run_id),
                'filename': r.filename,
                'schema': schema_name,
                'start_time': r.start_time.isoformat(),
                'total_records': r.total_records,
                'valid_records': r.valid_records,
                'rejected_records': r.rejected_records,
                'is_balanced': is_balanced,
                'status': r.run_status,
            })

        total_target_published = ProcessedOrder.objects.count()
        total_quarantined_stored = QuarantineRecord.objects.count()
        total_replayed = QuarantineRecord.objects.filter(status='REPLAYED').count()
        remaining_quarantine = QuarantineRecord.objects.exclude(status='REPLAYED').count()
        idempotent_updates = max(0, overall_valid - total_target_published)

        global_balance = {
            'total_source_records_ingested': overall_input,
            'valid_at_ingestion': overall_valid,
            'rejected_at_ingestion': overall_rejected,
            'ingestion_formula_balanced': overall_input == (overall_valid + overall_rejected),
            'target_database_records': total_target_published,
            'target_database_orders': total_target_published,  # backward compatibility
            'idempotent_deduplicated': idempotent_updates,
            'total_quarantined_ever': total_quarantined_stored,
            'successfully_replayed_recovered': total_replayed,
            'active_quarantine_remaining': remaining_quarantine,
            'quarantine_formula_balanced': total_quarantined_stored == (total_replayed + remaining_quarantine),
        }

        return Response({
            'global_reconciliation': global_balance,
            'runs_reconciliation': run_reconciliations,
        }, status=status.HTTP_200_OK)
