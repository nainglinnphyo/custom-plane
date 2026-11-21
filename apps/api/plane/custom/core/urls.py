# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Custom Plane API URL Configuration"""

from django.urls import path, include

# Module URL includes will be added here as modules are implemented
# path("rbac/", include("plane.custom.rbac.urls")),
# path("timesheets/", include("plane.custom.timesheets.urls")),
# path("approvals/", include("plane.custom.approvals.urls")),

urlpatterns = [
    # Health check for custom API
    path(
        "health/",
        lambda request: __import__("django.http").http.JsonResponse({"status": "OK", "service": "custom-plane"}),
        name="custom-health",
    ),
    # Milestones & timeline
    path("", include("plane.custom.milestones.urls")),
    # Company structure
    path("", include("plane.custom.company.urls")),
    path("", include("plane.custom.teams.urls")),
]

# Module URL includes (uncomment as modules are implemented)
# urlpatterns += [
#     path("rbac/", include("plane.custom.rbac.urls")),
#     path("timesheets/", include("plane.custom.timesheets.urls")),
#     path("approvals/", include("plane.custom.approvals.urls")),
#     path("reporting/", include("plane.custom.reporting.urls")),
#     path("workload/", include("plane.custom.workload.urls")),
#     path("risks/", include("plane.custom.risks.urls")),
#     path("automation/", include("plane.custom.automation.urls")),
#     path("documents/", include("plane.custom.documents.urls")),
#     path("notifications/", include("plane.custom.notifications.urls")),
#     path("audit/", include("plane.custom.audit.urls")),
#     path("okrs/", include("plane.custom.okrs.urls")),
#     path("ai/", include("plane.custom.ai.urls")),
# ]
