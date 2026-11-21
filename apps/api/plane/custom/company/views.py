# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from rest_framework import status
from rest_framework.response import Response

from plane.app.views.base import BaseAPIView
from plane.custom.core.permissions import WorkspaceDirectoryPermission
from plane.db.models import Workspace

from .models import Department, DepartmentMember
from .serializers import (
    CompanySerializer,
    CompanyWriteSerializer,
    DepartmentSerializer,
    DepartmentWriteSerializer,
    MemberRoleSerializer,
    MemberWriteSerializer,
    MembershipSerializer,
)
from .services import (
    OrgError,
    add_department_member,
    annotate_departments,
    create_company,
    delete_department,
    get_company_for_workspace,
    link_workspace,
    unlink_workspace,
    validate_parent,
)


def _error(message, code=status.HTTP_400_BAD_REQUEST):
    return Response({"error": message}, status=code)


class _WorkspaceScopedEndpoint(BaseAPIView):
    permission_classes = [WorkspaceDirectoryPermission]

    def get_workspace(self, slug):
        # the permission class already proved the caller is an active member of this slug
        return Workspace.objects.get(slug=slug)


class CompanyEndpoint(_WorkspaceScopedEndpoint):
    def get(self, request, slug):
        company = get_company_for_workspace(self.get_workspace(slug))
        if company is None:
            return Response(None, status=status.HTTP_200_OK)
        return Response(CompanySerializer(company, context={"request": request}).data)

    def post(self, request, slug):
        serializer = CompanyWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            company = create_company(self.get_workspace(slug), serializer.validated_data["name"])
        except OrgError as e:
            return _error(e.message)
        return Response(CompanySerializer(company, context={"request": request}).data, status=status.HTTP_201_CREATED)

    def patch(self, request, slug):
        company = get_company_for_workspace(self.get_workspace(slug))
        if company is None:
            return _error("This workspace does not belong to a company.", status.HTTP_404_NOT_FOUND)
        serializer = CompanyWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        company.name = serializer.validated_data["name"]
        company.save(update_fields=["name", "updated_at"])
        return Response(CompanySerializer(company, context={"request": request}).data)

    def delete(self, request, slug):
        """Detach this workspace from its company (the company disappears with its last workspace)."""
        try:
            unlink_workspace(self.get_workspace(slug))
        except OrgError as e:
            return _error(e.message, status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CompanyWorkspaceEndpoint(_WorkspaceScopedEndpoint):
    def post(self, request, slug):
        company = get_company_for_workspace(self.get_workspace(slug))
        if company is None:
            return _error("This workspace does not belong to a company.", status.HTTP_404_NOT_FOUND)
        target_slug = request.data.get("workspace_slug")
        target = Workspace.objects.filter(slug=target_slug).first() if isinstance(target_slug, str) else None
        if target is None:
            return _error("You must be an admin of both workspaces to link them.")
        try:
            link_workspace(company, target, request.user)
        except OrgError as e:
            return _error(e.message)
        return Response(CompanySerializer(company, context={"request": request}).data, status=status.HTTP_201_CREATED)


def _department_queryset(workspace_slug):
    return annotate_departments(Department.objects.filter(workspace__slug=workspace_slug))


class DepartmentListEndpoint(_WorkspaceScopedEndpoint):
    def get(self, request, slug):
        return Response(DepartmentSerializer(_department_queryset(slug), many=True).data)

    def post(self, request, slug):
        workspace = self.get_workspace(slug)
        serializer = DepartmentWriteSerializer(data=request.data, context={"workspace": workspace})
        serializer.is_valid(raise_exception=True)
        try:
            validate_parent(workspace, serializer.validated_data.get("parent"))
        except OrgError as e:
            return _error(e.message)
        department = serializer.save(workspace=workspace)
        return Response(
            DepartmentSerializer(_department_queryset(slug).get(pk=department.pk)).data, status=status.HTTP_201_CREATED
        )


class DepartmentDetailEndpoint(_WorkspaceScopedEndpoint):
    def get(self, request, slug, pk):
        department = _department_queryset(slug).filter(pk=pk).first()
        if department is None:
            return _error("Department not found.", status.HTTP_404_NOT_FOUND)
        return Response(DepartmentSerializer(department).data)

    def patch(self, request, slug, pk):
        department = Department.objects.filter(pk=pk, workspace__slug=slug).first()
        if department is None:
            return _error("Department not found.", status.HTTP_404_NOT_FOUND)
        workspace = self.get_workspace(slug)
        serializer = DepartmentWriteSerializer(
            department, data=request.data, partial=True, context={"workspace": workspace}
        )
        serializer.is_valid(raise_exception=True)
        if "parent" in serializer.validated_data:
            try:
                validate_parent(workspace, serializer.validated_data["parent"], department)
            except OrgError as e:
                return _error(e.message)
        serializer.save()
        return Response(DepartmentSerializer(_department_queryset(slug).get(pk=department.pk)).data)

    def delete(self, request, slug, pk):
        department = Department.objects.filter(pk=pk, workspace__slug=slug).first()
        if department is None:
            return _error("Department not found.", status.HTTP_404_NOT_FOUND)
        try:
            delete_department(department)
        except OrgError as e:
            return _error(e.message)
        return Response(status=status.HTTP_204_NO_CONTENT)


class DepartmentMemberEndpoint(_WorkspaceScopedEndpoint):
    def _department(self, slug, pk):
        return Department.objects.filter(pk=pk, workspace__slug=slug).select_related("workspace").first()

    def get(self, request, slug, pk):
        department = self._department(slug, pk)
        if department is None:
            return _error("Department not found.", status.HTTP_404_NOT_FOUND)
        rows = (
            DepartmentMember.objects.filter(department=department)
            .select_related("member")
            .order_by("member__display_name")
        )
        return Response(MembershipSerializer(rows, many=True).data)

    def post(self, request, slug, pk):
        department = self._department(slug, pk)
        if department is None:
            return _error("Department not found.", status.HTTP_404_NOT_FOUND)
        serializer = MemberWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            row = add_department_member(
                department, serializer.validated_data["member"], serializer.validated_data["role"]
            )
        except OrgError as e:
            return _error(e.message)
        row = DepartmentMember.objects.select_related("member").get(pk=row.pk)
        return Response(MembershipSerializer(row).data, status=status.HTTP_201_CREATED)

    def patch(self, request, slug, pk, user_id):
        department = self._department(slug, pk)
        row = (
            DepartmentMember.objects.filter(department=department, member_id=user_id).select_related("member").first()
            if department
            else None
        )
        if row is None:
            return _error("Membership not found.", status.HTTP_404_NOT_FOUND)
        serializer = MemberRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        row.role = serializer.validated_data["role"]
        row.save(update_fields=["role", "updated_at"])
        return Response(MembershipSerializer(row).data)

    def delete(self, request, slug, pk, user_id):
        department = self._department(slug, pk)
        row = DepartmentMember.objects.filter(department=department, member_id=user_id).first() if department else None
        if row is None:
            return _error("Membership not found.", status.HTTP_404_NOT_FOUND)
        row.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
