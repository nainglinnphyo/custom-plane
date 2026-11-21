# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest
from django.apps import apps
from django.conf import settings

from plane.custom.apps_list import CUSTOM_INSTALLED_APPS

pytestmark = pytest.mark.unit


def test_every_custom_app_is_installed():
    for dotted in CUSTOM_INSTALLED_APPS:
        assert dotted in settings.INSTALLED_APPS


def test_custom_apps_use_distinct_custom_labels():
    labels = [label for _, label in _labels()]
    assert len(labels) == len(set(labels)) >= len(CUSTOM_INSTALLED_APPS)
    assert all(label.startswith("custom_") for label in labels)


def _labels():
    return [(c.name, c.label) for c in apps.get_app_configs() if c.name.startswith("plane.custom.")]


def test_milestone_refresh_is_on_the_beat_schedule():
    from plane.celery import app

    entry = app.conf.beat_schedule["custom-milestones-refresh-statuses"]
    assert entry["task"] == "plane.custom.milestones.tasks.refresh_milestone_statuses"


def test_custom_health_route_is_public_and_ok(client):
    response = client.get("/api/custom/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "OK", "service": "custom-plane"}
