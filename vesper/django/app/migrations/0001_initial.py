# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-07-07 15:11
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AnnotationConstraint',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('description', models.TextField(blank=True)),
                ('text', models.TextField(blank=True)),
                ('creation_time', models.DateTimeField()),
            ],
            options={
                'db_table': 'vesper_annotation_constraint',
            },
        ),
        migrations.CreateModel(
            name='AnnotationInfo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('description', models.TextField(blank=True)),
                ('type', models.CharField(choices=[('String', 'String')], max_length=255)),
                ('creation_time', models.DateTimeField()),
                ('constraint', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='annotation_infos', related_query_name='annotation_info', to='vesper.AnnotationConstraint')),
            ],
            options={
                'db_table': 'vesper_annotation_info',
            },
        ),
        migrations.CreateModel(
            name='Clip',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_index', models.BigIntegerField(null=True)),
                ('length', models.BigIntegerField()),
                ('sample_rate', models.FloatField()),
                ('start_time', models.DateTimeField()),
                ('end_time', models.DateTimeField()),
                ('date', models.DateField()),
                ('creation_time', models.DateTimeField()),
            ],
            options={
                'db_table': 'vesper_clip',
            },
        ),
        migrations.CreateModel(
            name='Device',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('serial_number', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
            ],
            options={
                'db_table': 'vesper_device',
            },
        ),
        migrations.CreateModel(
            name='DeviceConnection',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_time', models.DateTimeField()),
                ('end_time', models.DateTimeField()),
            ],
            options={
                'db_table': 'vesper_device_connection',
            },
        ),
        migrations.CreateModel(
            name='DeviceInput',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('device', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='inputs', related_query_name='input', to='vesper.Device')),
            ],
            options={
                'db_table': 'vesper_device_input',
            },
        ),
        migrations.CreateModel(
            name='DeviceModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('type', models.CharField(max_length=255)),
                ('manufacturer', models.CharField(max_length=255)),
                ('model', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
            ],
            options={
                'db_table': 'vesper_device_model',
            },
        ),
        migrations.CreateModel(
            name='DeviceModelInput',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('local_name', models.CharField(max_length=255)),
                ('channel_num', models.IntegerField()),
                ('description', models.TextField(blank=True)),
                ('model', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='inputs', related_query_name='input', to='vesper.DeviceModel')),
            ],
            options={
                'db_table': 'vesper_device_model_input',
            },
        ),
        migrations.CreateModel(
            name='DeviceModelOutput',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('local_name', models.CharField(max_length=255)),
                ('channel_num', models.IntegerField()),
                ('description', models.TextField(blank=True)),
                ('model', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='outputs', related_query_name='output', to='vesper.DeviceModel')),
            ],
            options={
                'db_table': 'vesper_device_model_output',
            },
        ),
        migrations.CreateModel(
            name='DeviceOutput',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('device', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='outputs', related_query_name='output', to='vesper.Device')),
                ('model_output', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='device_outputs', related_query_name='device_output', to='vesper.DeviceModelOutput')),
            ],
            options={
                'db_table': 'vesper_device_output',
            },
        ),
        migrations.CreateModel(
            name='Job',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('command', models.TextField()),
                ('start_time', models.DateTimeField(null=True)),
                ('end_time', models.DateTimeField(null=True)),
                ('status', models.CharField(max_length=255)),
                ('creation_time', models.DateTimeField()),
                ('creating_job', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='jobs', related_query_name='job', to='vesper.Job')),
                ('creating_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='jobs', related_query_name='job', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'vesper_job',
            },
        ),
        migrations.CreateModel(
            name='Processor',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('type', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
            ],
            options={
                'db_table': 'vesper_processor',
            },
        ),
        migrations.CreateModel(
            name='Recording',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('num_channels', models.IntegerField()),
                ('length', models.BigIntegerField()),
                ('sample_rate', models.FloatField()),
                ('start_time', models.DateTimeField()),
                ('end_time', models.DateTimeField()),
                ('creation_time', models.DateTimeField()),
                ('creating_job', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='recordings', related_query_name='recording', to='vesper.Job')),
                ('recorder', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recordings', related_query_name='recording', to='vesper.Device')),
            ],
            options={
                'db_table': 'vesper_recording',
            },
        ),
        migrations.CreateModel(
            name='RecordingChannel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('channel_num', models.IntegerField()),
                ('recorder_channel_num', models.IntegerField()),
                ('mic_output', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recording_channels', related_query_name='recording_channel', to='vesper.DeviceOutput')),
                ('recording', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='channels', related_query_name='channel', to='vesper.Recording')),
            ],
            options={
                'db_table': 'vesper_recording_channel',
            },
        ),
        migrations.CreateModel(
            name='RecordingFile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file_num', models.IntegerField()),
                ('start_index', models.BigIntegerField()),
                ('length', models.BigIntegerField()),
                ('path', models.CharField(max_length=255, null=True, unique=True)),
                ('recording', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='files', related_query_name='file', to='vesper.Recording')),
            ],
            options={
                'db_table': 'vesper_recording_file',
            },
        ),
        migrations.CreateModel(
            name='Station',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('latitude', models.FloatField(null=True)),
                ('longitude', models.FloatField(null=True)),
                ('elevation', models.FloatField(null=True)),
                ('time_zone', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
            ],
            options={
                'db_table': 'vesper_station',
            },
        ),
        migrations.CreateModel(
            name='StationDevice',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_time', models.DateTimeField()),
                ('end_time', models.DateTimeField()),
                ('device', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='station_devices', related_query_name='station_device', to='vesper.Device')),
                ('station', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='station_devices', related_query_name='station_device', to='vesper.Station')),
            ],
            options={
                'db_table': 'vesper_station_device',
            },
        ),
        migrations.CreateModel(
            name='StringAnnotation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.CharField(max_length=255)),
                ('creation_time', models.DateTimeField()),
                ('clip', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='string_annotations', related_query_name='string_annotation', to='vesper.Clip')),
                ('creating_job', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='string_annotations', related_query_name='string_annotation', to='vesper.Job')),
                ('creating_processor', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='string_annotations', related_query_name='string_annotations', to='vesper.Processor')),
                ('creating_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='string_annotations', related_query_name='string_annotation', to=settings.AUTH_USER_MODEL)),
                ('info', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='string_annotations', related_query_name='string_annotation', to='vesper.AnnotationInfo')),
            ],
            options={
                'db_table': 'vesper_string_annotation',
            },
        ),
        migrations.CreateModel(
            name='StringAnnotationEdit',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('S', 'Set'), ('D', 'Delete')], max_length=1)),
                ('value', models.CharField(max_length=255, null=True)),
                ('creation_time', models.DateTimeField()),
                ('clip', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='string_annotation_edits', related_query_name='string_annotation_edit', to='vesper.Clip')),
                ('creating_job', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='string_annotation_edits', related_query_name='string_annotation_edit', to='vesper.Job')),
                ('creating_processor', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='string_annotation_edits', related_query_name='string_annotation_edits', to='vesper.Processor')),
                ('creating_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='string_annotation_edits', related_query_name='string_annotation_edit', to=settings.AUTH_USER_MODEL)),
                ('info', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='string_annotation_edits', related_query_name='string_annotation_edit', to='vesper.AnnotationInfo')),
            ],
            options={
                'db_table': 'vesper_string_annotation_edit',
            },
        ),
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('creation_time', models.DateTimeField()),
                ('clip', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tags', related_query_name='tag', to='vesper.Clip')),
                ('creating_job', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='tags', related_query_name='tag', to='vesper.Job')),
                ('creating_processor', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='tags', related_query_name='tags', to='vesper.Processor')),
                ('creating_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='tags', related_query_name='tag', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'vesper_tag',
            },
        ),
        migrations.CreateModel(
            name='TagEdit',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('S', 'Set'), ('D', 'Delete')], max_length=1)),
                ('creation_time', models.DateTimeField()),
                ('clip', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tag_edits', related_query_name='tag_edit', to='vesper.Clip')),
                ('creating_job', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='tag_edits', related_query_name='tag_edit', to='vesper.Job')),
                ('creating_processor', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='tag_edits', related_query_name='tag_edits', to='vesper.Processor')),
                ('creating_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='tag_edits', related_query_name='tag_edit', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'vesper_tag_edit',
            },
        ),
        migrations.CreateModel(
            name='TagInfo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('description', models.TextField(blank=True)),
                ('creation_time', models.DateTimeField()),
                ('creating_job', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='tag_infos', related_query_name='tag_info', to='vesper.Job')),
                ('creating_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='tag_infos', related_query_name='tag_info', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'vesper_tag_info',
            },
        ),
        migrations.AddField(
            model_name='tagedit',
            name='info',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tag_edits', related_query_name='tag_edit', to='vesper.TagInfo'),
        ),
        migrations.AddField(
            model_name='tag',
            name='info',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tags', related_query_name='tag', to='vesper.TagInfo'),
        ),
        migrations.AddField(
            model_name='station',
            name='devices',
            field=models.ManyToManyField(through='vesper.StationDevice', to='vesper.Device'),
        ),
        migrations.AddField(
            model_name='recording',
            name='station',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recordings', related_query_name='recording', to='vesper.Station'),
        ),
        migrations.AlterUniqueTogether(
            name='processor',
            unique_together=set([('name', 'type')]),
        ),
        migrations.AddField(
            model_name='job',
            name='processor',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='jobs', related_query_name='job', to='vesper.Processor'),
        ),
        migrations.AlterUniqueTogether(
            name='devicemodel',
            unique_together=set([('manufacturer', 'model')]),
        ),
        migrations.AddField(
            model_name='deviceinput',
            name='model_input',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='device_inputs', related_query_name='device_input', to='vesper.DeviceModelInput'),
        ),
        migrations.AddField(
            model_name='deviceconnection',
            name='input',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='connections', related_query_name='connection', to='vesper.DeviceInput'),
        ),
        migrations.AddField(
            model_name='deviceconnection',
            name='output',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='connections', related_query_name='connection', to='vesper.DeviceOutput'),
        ),
        migrations.AddField(
            model_name='device',
            name='model',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='devices', related_query_name='device', to='vesper.DeviceModel'),
        ),
        migrations.AddField(
            model_name='clip',
            name='creating_job',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='clips', related_query_name='clip', to='vesper.Job'),
        ),
        migrations.AddField(
            model_name='clip',
            name='creating_processor',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='clips', related_query_name='clip', to='vesper.Processor'),
        ),
        migrations.AddField(
            model_name='clip',
            name='creating_user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='clips', related_query_name='clip', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='clip',
            name='mic_output',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='clips', related_query_name='clip', to='vesper.DeviceOutput'),
        ),
        migrations.AddField(
            model_name='clip',
            name='recording_channel',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='clips', related_query_name='clip', to='vesper.RecordingChannel'),
        ),
        migrations.AddField(
            model_name='clip',
            name='station',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='clips', related_query_name='clip', to='vesper.Station'),
        ),
        migrations.AddField(
            model_name='annotationinfo',
            name='creating_job',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='annotation_infos', related_query_name='annotation_info', to='vesper.Job'),
        ),
        migrations.AddField(
            model_name='annotationinfo',
            name='creating_user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='annotation_infos', related_query_name='annotation_info', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='annotationconstraint',
            name='creating_job',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='annotation_constraints', related_query_name='annotation_constraint', to='vesper.Job'),
        ),
        migrations.AddField(
            model_name='annotationconstraint',
            name='creating_user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='annotation_constraints', related_query_name='annotation_constraint', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterUniqueTogether(
            name='tag',
            unique_together=set([('clip', 'info')]),
        ),
        migrations.AlterUniqueTogether(
            name='stringannotation',
            unique_together=set([('clip', 'info')]),
        ),
        migrations.AlterUniqueTogether(
            name='stationdevice',
            unique_together=set([('station', 'device', 'start_time', 'end_time')]),
        ),
        migrations.AlterUniqueTogether(
            name='recordingfile',
            unique_together=set([('recording', 'file_num')]),
        ),
        migrations.AlterUniqueTogether(
            name='recordingchannel',
            unique_together=set([('recording', 'channel_num')]),
        ),
        migrations.AlterUniqueTogether(
            name='recording',
            unique_together=set([('station', 'recorder', 'start_time')]),
        ),
        migrations.AlterUniqueTogether(
            name='deviceoutput',
            unique_together=set([('device', 'model_output')]),
        ),
        migrations.AlterUniqueTogether(
            name='devicemodeloutput',
            unique_together=set([('model', 'local_name'), ('model', 'channel_num')]),
        ),
        migrations.AlterUniqueTogether(
            name='devicemodelinput',
            unique_together=set([('model', 'local_name'), ('model', 'channel_num')]),
        ),
        migrations.AlterUniqueTogether(
            name='deviceinput',
            unique_together=set([('device', 'model_input')]),
        ),
        migrations.AlterUniqueTogether(
            name='deviceconnection',
            unique_together=set([('output', 'input', 'start_time', 'end_time')]),
        ),
        migrations.AlterUniqueTogether(
            name='device',
            unique_together=set([('model', 'serial_number')]),
        ),
        migrations.AlterUniqueTogether(
            name='clip',
            unique_together=set([('recording_channel', 'start_time', 'creating_processor')]),
        ),
        migrations.AlterIndexTogether(
            name='clip',
            index_together=set([('station', 'mic_output', 'date', 'creating_processor')]),
        ),
    ]
