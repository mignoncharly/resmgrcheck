import django.db.models.deletion
import uuid
from django.db import migrations, models

SQL='''
CREATE FUNCTION control_runner_job_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Runner job provenance cannot be deleted'; END IF;
 IF (SELECT target_id FROM control_run WHERE id=NEW.run_id) IS DISTINCT FROM NEW.runner_id
 OR (NEW.intent->>'run_id') IS DISTINCT FROM NEW.run_id::text
 OR (NEW.intent->>'target_id') IS DISTINCT FROM NEW.runner_id::text
 OR (NEW.intent->>'intent_sha256') IS DISTINCT FROM (SELECT intent_sha256 FROM control_run WHERE id=NEW.run_id)
 THEN RAISE EXCEPTION 'Runner job association mismatch'; END IF;
 IF TG_OP='UPDATE' AND (
 (NEW.run_id,NEW.runner_id,NEW.ticket,NEW.intent,NEW.offered_at) IS DISTINCT FROM
 (OLD.run_id,OLD.runner_id,OLD.ticket,OLD.intent,OLD.offered_at)
 OR (OLD.launch_granted_at IS NOT NULL AND NEW.launch_granted_at IS DISTINCT FROM OLD.launch_granted_at)
 OR (OLD.state<>'offered' AND NEW.state='offered')
 OR (OLD.archive_sha256<>'' AND (NEW.archive_sha256,NEW.archive_bytes) IS DISTINCT FROM (OLD.archive_sha256,OLD.archive_bytes)))
 THEN RAISE EXCEPTION 'Runner job identity is immutable'; END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER control_runner_job BEFORE INSERT OR UPDATE OR DELETE ON control_runnerjob
FOR EACH ROW EXECUTE FUNCTION control_runner_job_guard();
CREATE FUNCTION control_runner_chunk_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='UPDATE' THEN RAISE EXCEPTION 'Runner chunk is immutable'; END IF;
 IF TG_OP='DELETE' THEN
   IF NOT EXISTS(SELECT 1 FROM control_runnerjob j JOIN control_artifact a ON a.run_id=j.run_id
       WHERE j.run_id=OLD.job_id AND j.state='completed' AND a.relative_path='web-evidence-v2.json')
   THEN RAISE EXCEPTION 'Runner upload cleanup requires sealed evidence'; END IF;
   RETURN OLD;
 END IF;
 IF NEW.index>=512 OR octet_length(NEW.data)>131072 OR octet_length(NEW.data)=0
 THEN RAISE EXCEPTION 'Runner chunk exceeds bound'; END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER control_runner_chunk BEFORE INSERT OR UPDATE OR DELETE ON control_runnerchunk
FOR EACH ROW EXECUTE FUNCTION control_runner_chunk_guard();
'''


class Migration(migrations.Migration):

    dependencies = [
        ('control', '0018_customerrunner_alter_target_kind_alter_target_state_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='RunnerJob',
            fields=[
                ('run', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, primary_key=True, serialize=False, to='control.run')),
                ('ticket', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('intent', models.JSONField()),
                ('state', models.CharField(db_index=True, default='offered', max_length=24)),
                ('offered_at', models.DateTimeField(auto_now_add=True)),
                ('launch_granted_at', models.DateTimeField(null=True)),
                ('archive_sha256', models.CharField(blank=True, max_length=64)),
                ('archive_bytes', models.PositiveIntegerField(default=0)),
                ('ingest_lease', models.DateTimeField(null=True)),
                ('ingest_token', models.UUIDField(null=True)),
                ('runner', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='control.customerrunner')),
            ],
        ),
        migrations.CreateModel(
            name='RunnerChunk',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('index', models.PositiveSmallIntegerField()),
                ('data', models.BinaryField()),
                ('sha256', models.CharField(max_length=64)),
                ('job', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='control.runnerjob')),
            ],
            options={
                'constraints': [models.UniqueConstraint(fields=('job', 'index'), name='runner_upload_chunk_once')],
            },
        ),
        migrations.RunSQL(SQL,'''DROP TRIGGER control_runner_chunk ON control_runnerchunk;
            DROP FUNCTION control_runner_chunk_guard();
            DROP TRIGGER control_runner_job ON control_runnerjob; DROP FUNCTION control_runner_job_guard();'''),
    ]
