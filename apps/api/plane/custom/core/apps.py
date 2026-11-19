# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.apps import AppConfig


class CustomCoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "plane.custom.core"
    label = "custom_core"
    verbose_name = "Custom Plane Core"

    def ready(self):
        # Import signals if any
        pass