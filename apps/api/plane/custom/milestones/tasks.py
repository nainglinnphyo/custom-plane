# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from celery import shared_task

from plane.utils.exception_logger import log_exception

from .models import Milestone
from .services import refresh_status


@shared_task
def refresh_milestone_statuses():
    """Nightly: re-derive the cached status of every milestone that is not manually overridden."""
    try:
        ids = Milestone.objects.filter(status_override=False).values_list("id", flat=True)
        for milestone_id in ids.iterator():
            refresh_status(milestone_id)
    except Exception as e:
        log_exception(e)
