from django.db import migrations

class Migration(migrations.Migration):
    dependencies=[('control','0011_ai_output_integrity')]
    operations=[migrations.RunSQL('''
      CREATE FUNCTION control_ai_output_guard() RETURNS trigger LANGUAGE plpgsql AS $$
      BEGIN
        IF OLD.state='completed' AND
           (NEW.state,NEW.output_sha256,NEW.usage,NEW.resolved_model,NEW.provider_response_id,NEW.provider_request_id,NEW.accounted_microusd,NEW.usage_established)
           IS DISTINCT FROM
           (OLD.state,OLD.output_sha256,OLD.usage,OLD.resolved_model,OLD.provider_response_id,OLD.provider_request_id,OLD.accounted_microusd,OLD.usage_established)
        THEN RAISE EXCEPTION 'Completed AI provenance is immutable'; END IF;
        IF OLD.state='completed' AND NEW.result IS DISTINCT FROM OLD.result
           AND NOT (OLD.erased_at IS NULL AND NEW.erased_at IS NOT NULL AND NEW.result='{}'::jsonb)
        THEN RAISE EXCEPTION 'Completed AI interpretation is immutable except erasure'; END IF;
        RETURN NEW;
      END; $$;
      CREATE TRIGGER control_ai_output_immutable BEFORE UPDATE ON control_aianalysis
      FOR EACH ROW EXECUTE FUNCTION control_ai_output_guard();
    ''','DROP TRIGGER control_ai_output_immutable ON control_aianalysis; DROP FUNCTION control_ai_output_guard();')]
