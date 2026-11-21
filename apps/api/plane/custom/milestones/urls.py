# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.urls import path

from .views import (
    MilestoneDependencyEndpoint,
    MilestoneIssueEndpoint,
    MilestoneViewSet,
    TimelineEndpoint,
)

_BASE = "workspaces/<str:slug>/projects/<uuid:project_id>"

urlpatterns = [
    path(
        f"{_BASE}/milestones/",
        MilestoneViewSet.as_view({"get": "list", "post": "create"}),
        name="custom-milestones",
    ),
    path(
        f"{_BASE}/milestones/<uuid:pk>/",
        MilestoneViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}),
        name="custom-milestone-detail",
    ),
    path(
        f"{_BASE}/milestones/<uuid:pk>/issues/",
        MilestoneIssueEndpoint.as_view(),
        name="custom-milestone-issues",
    ),
    path(
        f"{_BASE}/milestones/<uuid:pk>/issues/<uuid:issue_id>/",
        MilestoneIssueEndpoint.as_view(),
        name="custom-milestone-issue",
    ),
    path(
        f"{_BASE}/milestones/<uuid:pk>/dependencies/",
        MilestoneDependencyEndpoint.as_view(),
        name="custom-milestone-dependencies",
    ),
    path(
        f"{_BASE}/milestones/<uuid:pk>/dependencies/<uuid:dependency_id>/",
        MilestoneDependencyEndpoint.as_view(),
        name="custom-milestone-dependency",
    ),
    path(f"{_BASE}/timeline/", TimelineEndpoint.as_view(), name="custom-milestone-timeline"),
]
