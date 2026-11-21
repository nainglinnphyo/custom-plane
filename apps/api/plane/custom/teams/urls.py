# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.urls import path

from .views import TeamDetailEndpoint, TeamListEndpoint, TeamMemberEndpoint

_BASE = "workspaces/<str:slug>/teams"

urlpatterns = [
    path(f"{_BASE}/", TeamListEndpoint.as_view(), name="custom-teams"),
    path(f"{_BASE}/<uuid:pk>/", TeamDetailEndpoint.as_view(), name="custom-team-detail"),
    path(f"{_BASE}/<uuid:pk>/members/", TeamMemberEndpoint.as_view(), name="custom-team-members"),
    path(f"{_BASE}/<uuid:pk>/members/<uuid:user_id>/", TeamMemberEndpoint.as_view(), name="custom-team-member"),
]
