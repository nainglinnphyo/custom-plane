# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.urls import path

from .views import (
    CompanyEndpoint,
    CompanyWorkspaceEndpoint,
    DepartmentDetailEndpoint,
    DepartmentListEndpoint,
    DepartmentMemberEndpoint,
)

_BASE = "workspaces/<str:slug>"

urlpatterns = [
    path(f"{_BASE}/company/", CompanyEndpoint.as_view(), name="custom-company"),
    path(f"{_BASE}/company/workspaces/", CompanyWorkspaceEndpoint.as_view(), name="custom-company-workspaces"),
    path(f"{_BASE}/departments/", DepartmentListEndpoint.as_view(), name="custom-departments"),
    path(f"{_BASE}/departments/<uuid:pk>/", DepartmentDetailEndpoint.as_view(), name="custom-department-detail"),
    path(
        f"{_BASE}/departments/<uuid:pk>/members/", DepartmentMemberEndpoint.as_view(), name="custom-department-members"
    ),
    path(
        f"{_BASE}/departments/<uuid:pk>/members/<uuid:user_id>/",
        DepartmentMemberEndpoint.as_view(),
        name="custom-department-member",
    ),
]
