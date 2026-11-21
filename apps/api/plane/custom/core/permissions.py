# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from rest_framework.permissions import SAFE_METHODS, BasePermission

from plane.app.permissions import ROLE
from plane.db.models import WorkspaceMember


class WorkspaceDirectoryPermission(BasePermission):
    """Workspace-level access for organisational data (departments, teams).

    * read:  active workspace ADMIN or MEMBER (guests do not see the org directory)
    * write: active workspace ADMIN
    The workspace comes from the ``slug`` URL kwarg; non-members get 403 for every verb.
    """

    def has_permission(self, request, view):
        if request.user.is_anonymous:
            return False
        membership = WorkspaceMember.objects.filter(
            workspace__slug=view.workspace_slug, member=request.user, is_active=True
        ).first()
        if membership is None:
            return False
        request.workspace_role = membership.role
        if request.method in SAFE_METHODS:
            return membership.role in (ROLE.ADMIN.value, ROLE.MEMBER.value)
        return membership.role == ROLE.ADMIN.value
