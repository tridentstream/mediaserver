# Generated by Django 2.2.8 on 2019-12-13 16:29

import django.db.models.deletion
import jsonfield.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ListingItem",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("app", models.CharField(max_length=30)),
                ("name", models.CharField(db_index=True, default="", max_length=200)),
                ("path", models.CharField(max_length=500)),
                ("datetime", models.DateTimeField()),
                ("config", jsonfield.fields.JSONField(default=dict)),
                ("attributes", jsonfield.fields.JSONField(default=dict)),
                (
                    "item_type",
                    models.CharField(
                        choices=[("file", "File"), ("folder", "Folder")], max_length=10
                    ),
                ),
                ("is_root", models.BooleanField(default=False)),
                ("last_updated", models.DateTimeField(null=True)),
                ("last_checked", models.DateTimeField(null=True)),
                (
                    "parent",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="services_listing.ListingItem",
                    ),
                ),
            ],
            options={"ordering": ("datetime",), "unique_together": {("app", "path")},},
        ),
    ]
