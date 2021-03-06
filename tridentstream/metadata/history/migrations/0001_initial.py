# Generated by Django 2.2.8 on 2019-12-13 16:29

import uuid

import django.db.models.deletion
import jsonfield.fields
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("services_listing", "0001_initial"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.CreateModel(
            name="History",
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
                ("app", models.CharField(db_index=True, max_length=30)),
                ("name", models.CharField(db_index=True, max_length=200)),
                ("listingitem_app", models.CharField(max_length=30, null=True)),
                ("listingitem_path", models.CharField(max_length=500, null=True)),
                ("last_watched", models.DateTimeField()),
                ("created", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-last_watched"],},
        ),
        migrations.CreateModel(
            name="HistoryMetadata",
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
                ("object_id", models.PositiveIntegerField()),
                ("primary_metadata", models.BooleanField(default=False)),
                (
                    "content_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="contenttypes.ContentType",
                    ),
                ),
                (
                    "history",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="metadata_history.History",
                    ),
                ),
            ],
            options={"unique_together": {("content_type", "object_id", "history")},},
        ),
        migrations.CreateModel(
            name="ViewState",
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
                ("identifier", models.UUIDField(default=uuid.uuid4, editable=False)),
                ("values", jsonfield.fields.JSONField(blank=True, default=dict)),
                ("last_update", models.DateTimeField(auto_now=True)),
                ("created", models.DateTimeField(auto_now_add=True)),
                (
                    "history",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="metadata_history.History",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"unique_together": {("identifier", "user")},},
        ),
        migrations.CreateModel(
            name="ListingItemRelation",
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
                (
                    "listingitem",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="metadata_history",
                        to="services_listing.ListingItem",
                    ),
                ),
                (
                    "metadata",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="metadata_history.HistoryMetadata",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="metadata_history",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "abstract": False,
                "unique_together": {("listingitem", "metadata", "user")},
            },
        ),
    ]
