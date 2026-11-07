from django.db import migrations

class Migration(migrations.Migration):
    dependencies=[('control','0007_retention_metadata')]
    operations=[migrations.RunSQL('''
      CREATE FUNCTION control_artifact_insert_guard() RETURNS trigger LANGUAGE plpgsql AS $$
      BEGIN
        IF EXISTS(SELECT 1 FROM control_artifact WHERE run_id=NEW.run_id AND relative_path='web-evidence-v2.json')
        THEN RAISE EXCEPTION 'Sealed artifact graph cannot be extended'; END IF;
        RETURN NEW;
      END; $$;
      CREATE TRIGGER control_artifact_closed BEFORE INSERT ON control_artifact
      FOR EACH ROW EXECUTE FUNCTION control_artifact_insert_guard();
    ''','DROP TRIGGER control_artifact_closed ON control_artifact; DROP FUNCTION control_artifact_insert_guard();')]
