# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db import transaction
from django.db.models import Count, Q

from plane.custom.company.services import OrgError, ensure_workspace_member

from .models import CustomTeam, TeamMember, TeamRole


def annotate_teams(queryset):
    return queryset.annotate(
        member_count=Count("memberships", filter=Q(memberships__deleted_at__isnull=True), distinct=True)
    )


@transaction.atomic
def add_team_member(team: CustomTeam, user_id, role: str = TeamRole.MEMBER.value) -> TeamMember:
    if role not in TeamRole.values:
        raise OrgError("Invalid role.")
    user = ensure_workspace_member(team.workspace, user_id)
    if TeamMember.objects.filter(team=team, member=user).exists():
        raise OrgError("This user is already in the team.")
    return TeamMember.objects.create(team=team, member=user, role=role)


def delete_team(team: CustomTeam) -> None:
    with transaction.atomic():
        TeamMember.objects.filter(team=team).delete()
        team.delete()
