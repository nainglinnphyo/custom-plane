# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from rest_framework import status
from rest_framework.response import Response

from plane.custom.company.serializers import MemberRoleSerializer, MemberWriteSerializer, MembershipSerializer
from plane.custom.company.services import OrgError
from plane.custom.company.views import _error, _WorkspaceScopedEndpoint
from plane.db.models import Workspace

from .models import CustomTeam, TeamMember
from .serializers import TeamSerializer, TeamWriteSerializer
from .services import add_team_member, annotate_teams, delete_team


def _team_queryset(slug):
    return annotate_teams(CustomTeam.objects.filter(workspace__slug=slug))


class TeamListEndpoint(_WorkspaceScopedEndpoint):
    def get(self, request, slug):
        return Response(TeamSerializer(_team_queryset(slug), many=True).data)

    def post(self, request, slug):
        workspace = Workspace.objects.get(slug=slug)
        serializer = TeamWriteSerializer(data=request.data, context={"workspace": workspace})
        serializer.is_valid(raise_exception=True)
        team = serializer.save(workspace=workspace)
        return Response(TeamSerializer(_team_queryset(slug).get(pk=team.pk)).data, status=status.HTTP_201_CREATED)


class TeamDetailEndpoint(_WorkspaceScopedEndpoint):
    def get(self, request, slug, pk):
        team = _team_queryset(slug).filter(pk=pk).first()
        if team is None:
            return _error("Team not found.", status.HTTP_404_NOT_FOUND)
        return Response(TeamSerializer(team).data)

    def patch(self, request, slug, pk):
        team = CustomTeam.objects.filter(pk=pk, workspace__slug=slug).first()
        if team is None:
            return _error("Team not found.", status.HTTP_404_NOT_FOUND)
        serializer = TeamWriteSerializer(
            team, data=request.data, partial=True, context={"workspace": Workspace.objects.get(slug=slug)}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(TeamSerializer(_team_queryset(slug).get(pk=team.pk)).data)

    def delete(self, request, slug, pk):
        team = CustomTeam.objects.filter(pk=pk, workspace__slug=slug).first()
        if team is None:
            return _error("Team not found.", status.HTTP_404_NOT_FOUND)
        delete_team(team)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TeamMemberEndpoint(_WorkspaceScopedEndpoint):
    def _team(self, slug, pk):
        return CustomTeam.objects.filter(pk=pk, workspace__slug=slug).select_related("workspace").first()

    def get(self, request, slug, pk):
        team = self._team(slug, pk)
        if team is None:
            return _error("Team not found.", status.HTTP_404_NOT_FOUND)
        rows = TeamMember.objects.filter(team=team).select_related("member").order_by("member__display_name")
        return Response(MembershipSerializer(rows, many=True).data)

    def post(self, request, slug, pk):
        team = self._team(slug, pk)
        if team is None:
            return _error("Team not found.", status.HTTP_404_NOT_FOUND)
        serializer = MemberWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            row = add_team_member(team, serializer.validated_data["member"], serializer.validated_data["role"])
        except OrgError as e:
            return _error(e.message)
        return Response(
            MembershipSerializer(TeamMember.objects.select_related("member").get(pk=row.pk)).data,
            status=status.HTTP_201_CREATED,
        )

    def patch(self, request, slug, pk, user_id):
        team = self._team(slug, pk)
        row = TeamMember.objects.filter(team=team, member_id=user_id).select_related("member").first() if team else None
        if row is None:
            return _error("Membership not found.", status.HTTP_404_NOT_FOUND)
        serializer = MemberRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        row.role = serializer.validated_data["role"]
        row.save(update_fields=["role", "updated_at"])
        return Response(MembershipSerializer(row).data)

    def delete(self, request, slug, pk, user_id):
        team = self._team(slug, pk)
        row = TeamMember.objects.filter(team=team, member_id=user_id).first() if team else None
        if row is None:
            return _error("Membership not found.", status.HTTP_404_NOT_FOUND)
        row.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
