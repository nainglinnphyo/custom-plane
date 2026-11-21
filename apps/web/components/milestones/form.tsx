/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Controller, useForm } from "react-hook-form";
// plane imports
import { Button } from "@makeplane/propel/components/button";
import {
  DialogActions,
  DialogBody,
  DialogHeader,
  DialogHeading,
  DialogMain,
  DialogTitle,
} from "@makeplane/propel/components/dialog";
import { InputField } from "@makeplane/propel/components/input-field";
import { TextAreaField } from "@makeplane/propel/components/text-area-field";
import { CalendarOutline } from "@makeplane/propel/icons";
import { DateRangeSelect } from "@plane/blocks/property-select";
import { useTranslation } from "@plane/i18n";
import { getDate, renderFormattedPayloadDate } from "@plane/utils";
// hooks
import { useUserProfile } from "@/hooks/store/user";
// local imports
import type { TMilestone, TMilestoneFormValues } from "./types";

type Props = {
  data?: TMilestone | null;
  handleFormSubmit: (values: TMilestoneFormValues) => Promise<void>;
  handleClose: () => void;
};

export function MilestoneForm(props: Props) {
  const { data, handleFormSubmit, handleClose } = props;
  // plane hooks
  const { t } = useTranslation();
  // store hooks
  const { data: userProfile } = useUserProfile();
  // form
  const {
    control,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<TMilestoneFormValues>({
    defaultValues: {
      name: data?.name ?? "",
      description: data?.description ?? "",
      start_date: data?.start_date ?? null,
      due_date: data?.due_date ?? null,
    },
  });
  // a milestone cannot be saved without a due date
  const hasDueDate = !!watch("due_date");

  return (
    <form className="flex min-h-0 flex-1 flex-col" onSubmit={handleSubmit((values) => handleFormSubmit(values))}>
      <DialogMain>
        <DialogHeader>
          <DialogHeading>
            <DialogTitle>{data ? t("milestone.edit_title") : t("milestone.create_title")}</DialogTitle>
          </DialogHeading>
        </DialogHeader>
        <DialogBody tabIndex={0}>
          <div className="space-y-3">
            <Controller
              name="name"
              control={control}
              rules={{
                required: t("title_is_required"),
                maxLength: { value: 255, message: t("title_should_be_less_than_255_characters") },
              }}
              render={({ field: { value, onChange } }) => (
                <InputField
                  size="xl"
                  orientation="vertical"
                  error={errors?.name?.message}
                  name="name"
                  type="text"
                  placeholder={t("milestone.name_placeholder")}
                  aria-label={t("milestone.name_placeholder")}
                  value={value}
                  onChange={onChange}
                />
              )}
            />
            <Controller
              name="description"
              control={control}
              render={({ field: { value, onChange } }) => (
                <TextAreaField
                  size="xl"
                  autoResize
                  maxRows={8}
                  name="description"
                  placeholder={t("description")}
                  aria-label={t("description")}
                  value={value}
                  onChange={onChange}
                />
              )}
            />
            <Controller
              control={control}
              name="start_date"
              render={({ field: { value: startValue, onChange: onChangeStart } }) => (
                <Controller
                  control={control}
                  name="due_date"
                  render={({ field: { value: dueValue, onChange: onChangeDue } }) => (
                    <DateRangeSelect
                      variant="pill-sm"
                      className="max-w-none"
                      value={{ from: getDate(startValue) ?? null, to: getDate(dueValue) ?? null }}
                      onChange={(val) => {
                        onChangeStart(val.from ? renderFormattedPayloadDate(val.from) : null);
                        onChangeDue(val.to ? renderFormattedPayloadDate(val.to) : null);
                      }}
                      icon={<CalendarOutline />}
                      placeholder={`${t("start_date")} - ${t("due_date")}`}
                      weekStartsOn={userProfile?.start_of_the_week}
                    />
                  )}
                />
              )}
            />
          </div>
        </DialogBody>
      </DialogMain>
      <DialogActions>
        <Button variant="secondary" size="md" stretch="auto" onClick={handleClose} label={t("cancel")} />
        <Button
          variant="primary"
          size="md"
          stretch="auto"
          type="submit"
          disabled={!hasDueDate}
          loading={isSubmitting}
          label={isSubmitting ? t("saving") : t("save")}
        />
      </DialogActions>
    </form>
  );
}
