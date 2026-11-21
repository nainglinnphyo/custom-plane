# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.apps import AppConfig


class CustomCompanyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "plane.custom.company"
    label = "custom_company"
    verbose_name = "Custom Plane Company"
