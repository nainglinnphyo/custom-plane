# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from uuid import uuid4

import pytest

from plane.custom.company.services import OrgError
from plane.custom.teams.models import CustomTeam, TeamMember
from plane.custom.teams.services import add_team_member, annotate_teams, delete_team
from plane.db.models import User, WorkspaceMember

pytestmark = pytest.mark.unit


@pytest.fixture
def team(db, workspace):
    return CustomTeam.objects.create(name="Platform", workspace=workspace)


@pytest.mark.django_db
class TestTeamMembers:
    def test_add_and_count(self, team, create_user):
        add_team_member(team, create_user.id, "lead")
        assert annotate_teams(CustomTeam.objects.filter(pk=team.pk)).get().member_count == 1

    def test_non_workspace_member_rejected(self, team):
        uid = uuid4().hex[:8]
        stranger = User.objects.create(email=f"s-{uid}@plane.so", username=f"s_{uid}")
        with pytest.raises(OrgError):
            add_team_member(team, stranger.id)

    def test_duplicate_and_bad_role_rejected(self, team, create_user, workspace):
        add_team_member(team, create_user.id)
        with pytest.raises(OrgError):
            add_team_member(team, create_user.id)
        uid = uuid4().hex[:8]
        other = User.objects.create(email=f"o-{uid}@plane.so", username=f"o_{uid}")
        WorkspaceMember.objects.create(workspace=workspace, member=other, role=15)
        with pytest.raises(OrgError):
            add_team_member(team, other.id, "captain")

    def test_delete_team_removes_memberships(self, team, create_user):
        add_team_member(team, create_user.id)
        delete_team(team)
        assert not TeamMember.objects.filter(team=team).exists()
        assert not CustomTeam.objects.filter(pk=team.pk).exists()
