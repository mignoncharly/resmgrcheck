from django.db import migrations

class Migration(migrations.Migration):
    dependencies=[('control','0005_run_intent_guard')]
    operations=[migrations.RunSQL('''
      CREATE FUNCTION control_artifact_guard() RETURNS trigger LANGUAGE plpgsql AS $$
      BEGIN RAISE EXCEPTION 'Sealed artifact inventory is immutable'; END; $$;
      CREATE TRIGGER control_artifact_immutable BEFORE UPDATE OR DELETE ON control_artifact
      FOR EACH ROW EXECUTE FUNCTION control_artifact_guard();
    ''','DROP TRIGGER control_artifact_immutable ON control_artifact; DROP FUNCTION control_artifact_guard();')]
