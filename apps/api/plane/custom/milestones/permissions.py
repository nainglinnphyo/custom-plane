# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from rest_framework.permissions import SAFE_METHODS, BasePermission

from plane.db.models import ProjectMember
from plane.db.models.project import ROLE


class MilestonePermission(BasePermission):
    """Project-scoped access to milestones.

    * read:  any active project member; guests only when the project lets guests see all features
    * write: active project ADMIN or MEMBER
    The workspace/project come from the URL; non-members get 403 for every verb.
    """

    def has_permission(self, request, view):
        if request.user.is_anonymous:
            return False

        member = (
            ProjectMember.objects.filter(
                workspace__slug=view.workspace_slug,
                project_id=view.project_id,
                member=request.user,
                is_active=True,
            )
            .select_related("project")
            .first()
        )
        if member is None:
            return False

        request.milestone_role = member.role
        if request.method in SAFE_METHODS:
            return member.role != ROLE.GUEST.value or member.project.guest_view_all_features
        return member.role in (ROLE.ADMIN.value, ROLE.MEMBER.value)
