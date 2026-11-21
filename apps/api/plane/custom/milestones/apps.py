# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.apps import AppConfig


class CustomMilestonesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "plane.custom.milestones"
    label = "custom_milestones"
    verbose_name = "Custom Plane Milestones"

    def ready(self):
        # Register the nightly status refresh on the shared Celery beat schedule.
        # Beat uses DatabaseScheduler, which syncs app.conf.beat_schedule into the DB at start-up.
        from celery.schedules import crontab

        from plane.celery import app

        app.conf.beat_schedule["custom-milestones-refresh-statuses"] = {
            "task": "plane.custom.milestones.tasks.refresh_milestone_statuses",
            "schedule": crontab(hour=4, minute=0),  # UTC 04:00
        }
