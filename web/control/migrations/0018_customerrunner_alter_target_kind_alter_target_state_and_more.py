import django.db.models.deletion
import uuid
from django.db import migrations, models

SQL='''
CREATE FUNCTION control_runner_identity_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='INSERT' AND (SELECT kind FROM control_target WHERE id=NEW.target_id) IS DISTINCT FROM 'customer-runner'
 THEN RAISE EXCEPTION 'Runner target mode mismatch'; END IF;
 IF TG_OP='UPDATE' AND (
 (NEW.target_id,NEW.public_key,NEW.inventory,NEW.inventory_sha256,NEW.created_at) IS DISTINCT FROM
 (OLD.target_id,OLD.public_key,OLD.inventory,OLD.inventory_sha256,OLD.created_at)
 OR (OLD.revoked_at IS NOT NULL AND NEW.revoked_at IS DISTINCT FROM OLD.revoked_at)
 OR (OLD.quarantined AND NOT NEW.quarantined))
 THEN RAISE EXCEPTION 'Runner identity is immutable'; END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER control_runner_identity BEFORE INSERT OR UPDATE ON control_customerrunner
FOR EACH ROW EXECUTE FUNCTION control_runner_identity_guard();
CREATE FUNCTION control_runner_target_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF (NEW.project_id,NEW.kind) IS DISTINCT FROM (OLD.project_id,OLD.kind)
 AND (EXISTS(SELECT 1 FROM control_customerrunner WHERE target_id=OLD.id)
 OR EXISTS(SELECT 1 FROM control_runnerenrollment WHERE target_id=OLD.id))
 THEN RAISE EXCEPTION 'Runner target association is immutable'; END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER control_runner_target BEFORE UPDATE ON control_target
FOR EACH ROW EXECUTE FUNCTION control_runner_target_guard();
CREATE FUNCTION control_runner_project_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.organization_id IS DISTINCT FROM OLD.organization_id
 AND EXISTS(SELECT 1 FROM control_target WHERE project_id=OLD.id AND kind='customer-runner')
 THEN RAISE EXCEPTION 'Runner organization association is immutable'; END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER control_runner_project BEFORE UPDATE ON control_project
FOR EACH ROW EXECUTE FUNCTION control_runner_project_guard();
'''


class Migration(migrations.Migration):

    dependencies = [
        ('control', '0017_session_and_scope_integrity'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomerRunner',
            fields=[
                ('target', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, primary_key=True, serialize=False, to='control.target')),
                ('public_key', models.CharField(max_length=64, unique=True)),
                ('inventory', models.JSONField(default=dict)),
                ('inventory_sha256', models.CharField(max_length=64)),
                ('approved_at', models.DateTimeField(null=True)),
                ('revoked_at', models.DateTimeField(null=True)),
                ('last_seen', models.DateTimeField(null=True)),
                ('quarantined', models.BooleanField(default=False)),
                ('daily_limit', models.PositiveSmallIntegerField(default=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.AlterField(
            model_name='target',
            name='kind',
            field=models.CharField(choices=[('managed-lab', 'Approved managed fixtures'), ('external-health', 'External read-only health'), ('customer-request', 'Legacy customer runner request'), ('customer-runner', 'Customer-owned outbound runner')], default='customer-request', max_length=24),
        ),
        migrations.AlterField(
            model_name='target',
            name='state',
            field=models.CharField(choices=[('unknown', 'unknown'), ('available', 'available'), ('unavailable', 'unavailable'), ('unsupported', 'unsupported'), ('quarantined', 'quarantined'), ('pending-approval', 'pending-approval'), ('connected', 'connected'), ('disconnected', 'disconnected'), ('incompatible', 'incompatible')], default='unknown', max_length=20),
        ),
        migrations.CreateModel(
            name='RunnerEnrollment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('verifier', models.CharField(max_length=64)),
                ('expires_at', models.DateTimeField()),
                ('used_at', models.DateTimeField(null=True)),
                ('revoked_at', models.DateTimeField(null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('target', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='control.target')),
            ],
        ),
        migrations.CreateModel(
            name='RunnerNonce',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nonce', models.CharField(max_length=32)),
                ('expires_at', models.DateTimeField(db_index=True)),
                ('runner', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='control.customerrunner')),
            ],
            options={
                'constraints': [models.UniqueConstraint(fields=('runner', 'nonce'), name='runner_nonce_once')],
            },
        ),
        migrations.RunSQL(SQL,'''DROP TRIGGER control_runner_project ON control_project;
            DROP FUNCTION control_runner_project_guard();
            DROP TRIGGER control_runner_target ON control_target; DROP FUNCTION control_runner_target_guard();
            DROP TRIGGER control_runner_identity ON control_customerrunner; DROP FUNCTION control_runner_identity_guard();'''),
    ]
