# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db.models import Prefetch
from rest_framework import status
from rest_framework.response import Response

from plane.app.views.base import BaseAPIView, BaseViewSet
from plane.db.models import Issue

from .models import Milestone, MilestoneDependency, MilestoneIssue
from .permissions import MilestonePermission
from .serializers import (
    MilestoneDependencySerializer,
    MilestoneSerializer,
    MilestoneWriteSerializer,
)
from .services import MilestoneError, add_dependency, annotate_progress, link_issues, refresh_status, unlink_issue

MAX_LINK_BATCH = 500


def _milestone_queryset(slug, project_id):
    """Annotated, project-scoped queryset. Scoping by both slug and project id keeps lookups tenant-safe."""
    return annotate_progress(
        Milestone.objects.filter(workspace__slug=slug, project_id=project_id).prefetch_related(
            Prefetch("dependencies", queryset=MilestoneDependency.objects.only("id", "milestone_id", "depends_on_id"))
        )
    )


def _error(message, code=status.HTTP_400_BAD_REQUEST):
    return Response({"error": message}, status=code)


class MilestoneViewSet(BaseViewSet):
    model = Milestone
    permission_classes = [MilestonePermission]
    # Per-project milestone lists are small; no pagination (see docs/05-API-SPECIFICATION.md).

    def get_queryset(self):
        return _milestone_queryset(self.workspace_slug, self.project_id)

    def _context(self, request):
        return {"project_id": self.project_id, "role": getattr(request, "milestone_role", None)}

    def list(self, request, slug, project_id):
        return Response(MilestoneSerializer(self.get_queryset(), many=True).data, status=status.HTTP_200_OK)

    def retrieve(self, request, slug, project_id, pk):
        milestone = self.get_queryset().filter(pk=pk).first()
        if milestone is None:
            return _error("Milestone not found.", status.HTTP_404_NOT_FOUND)
        return Response(MilestoneSerializer(milestone).data, status=status.HTTP_200_OK)

    def create(self, request, slug, project_id):
        serializer = MilestoneWriteSerializer(data=request.data, context=self._context(request))
        serializer.is_valid(raise_exception=True)
        milestone = serializer.save(project_id=project_id)
        refresh_status(milestone.pk)
        return Response(
            MilestoneSerializer(self.get_queryset().get(pk=milestone.pk)).data, status=status.HTTP_201_CREATED
        )

    def partial_update(self, request, slug, project_id, pk):
        milestone = Milestone.objects.filter(pk=pk, workspace__slug=slug, project_id=project_id).first()
        if milestone is None:
            return _error("Milestone not found.", status.HTTP_404_NOT_FOUND)
        serializer = MilestoneWriteSerializer(
            milestone, data=request.data, partial=True, context=self._context(request)
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        refresh_status(milestone.pk)
        return Response(MilestoneSerializer(self.get_queryset().get(pk=milestone.pk)).data, status=status.HTTP_200_OK)

    def destroy(self, request, slug, project_id, pk):
        milestone = Milestone.objects.filter(pk=pk, workspace__slug=slug, project_id=project_id).first()
        if milestone is None:
            return _error("Milestone not found.", status.HTTP_404_NOT_FOUND)
        milestone.delete()  # soft delete; related links/dependencies are cascaded by the core task
        return Response(status=status.HTTP_204_NO_CONTENT)


class _MilestoneScopedEndpoint(BaseAPIView):
    permission_classes = [MilestonePermission]

    def _get_milestone(self, slug, project_id, pk):
        return Milestone.objects.filter(pk=pk, workspace__slug=slug, project_id=project_id).first()


class MilestoneIssueEndpoint(_MilestoneScopedEndpoint):
    def get(self, request, slug, project_id, pk):
        milestone = self._get_milestone(slug, project_id, pk)
        if milestone is None:
            return _error("Milestone not found.", status.HTTP_404_NOT_FOUND)
        issue_ids = MilestoneIssue.objects.filter(milestone=milestone).values_list("issue_id", flat=True)
        issues = (
            Issue.issue_objects.filter(id__in=issue_ids, project_id=project_id)
            .select_related("state")
            .values("id", "sequence_id", "name", "priority", "state_id", "state__group", "start_date", "target_date")
            .order_by("sequence_id")
        )
        return Response(
            [{**{k: v for k, v in i.items() if k != "state__group"}, "state_group": i["state__group"]} for i in issues],
            status=status.HTTP_200_OK,
        )

    def post(self, request, slug, project_id, pk):
        milestone = self._get_milestone(slug, project_id, pk)
        if milestone is None:
            return _error("Milestone not found.", status.HTTP_404_NOT_FOUND)
        issue_ids = request.data.get("issue_ids")
        if not isinstance(issue_ids, list) or not issue_ids or len(issue_ids) > MAX_LINK_BATCH:
            return _error(f"issue_ids must be a list of 1 to {MAX_LINK_BATCH} work item ids.")
        try:
            added = link_issues(milestone, issue_ids)
        except MilestoneError as e:
            return _error(e.message)
        except (ValueError, TypeError):
            return _error("issue_ids must contain valid UUIDs.")
        return Response({"added": added}, status=status.HTTP_201_CREATED)

    def delete(self, request, slug, project_id, pk, issue_id):
        milestone = self._get_milestone(slug, project_id, pk)
        if milestone is None or not unlink_issue(milestone, issue_id):
            return _error("Milestone link not found.", status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MilestoneDependencyEndpoint(_MilestoneScopedEndpoint):
    def post(self, request, slug, project_id, pk):
        milestone = self._get_milestone(slug, project_id, pk)
        if milestone is None:
            return _error("Milestone not found.", status.HTTP_404_NOT_FOUND)
        depends_on = (
            Milestone.objects.filter(
                pk=request.data.get("depends_on"), workspace__slug=slug, project_id=project_id
            ).first()
            if request.data.get("depends_on")
            else None
        )
        if depends_on is None:
            return _error("depends_on must be a milestone of this project.")
        try:
            dependency = add_dependency(milestone, depends_on)
        except MilestoneError as e:
            return _error(e.message)
        return Response(MilestoneDependencySerializer(dependency).data, status=status.HTTP_201_CREATED)

    def delete(self, request, slug, project_id, pk, dependency_id):
        milestone = self._get_milestone(slug, project_id, pk)
        dependency = (
            MilestoneDependency.objects.filter(pk=dependency_id, milestone=milestone).first() if milestone else None
        )
        if dependency is None:
            return _error("Dependency not found.", status.HTTP_404_NOT_FOUND)
        dependency.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TimelineEndpoint(_MilestoneScopedEndpoint):
    """Read model for the timeline: milestones plus their dependency edges, in one response."""

    def get(self, request, slug, project_id):
        milestones = list(_milestone_queryset(slug, project_id))
        edges = MilestoneDependency.objects.filter(
            milestone__in=[m.pk for m in milestones], workspace__slug=slug, project_id=project_id
        )
        return Response(
            {
                "milestones": MilestoneSerializer(milestones, many=True).data,
                "dependencies": MilestoneDependencySerializer(edges, many=True).data,
            },
            status=status.HTTP_200_OK,
        )
