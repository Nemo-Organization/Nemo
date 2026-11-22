"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { DotsThreeIcon } from "@phosphor-icons/react/ssr";
import { toast } from "sonner";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { EndpointItem } from "../types/endpoints.types";

export function EndpointRowActions({ endpoint }: { endpoint: EndpointItem }) {
  const t = useTranslations("endpoints.actions");
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);

  const handleCopyUrl = () => {
    void navigator.clipboard?.writeText(endpoint.url);
    toast.success(t("copied"), { description: endpoint.url });
  };

  // TODO: call the endpoints service instead of showing mock toasts.
  const handleToggleStatus = () =>
    toast.success(
      endpoint.status === "active" ? t("paused") : t("activated"),
      { description: endpoint.name },
    );

  const handleDelete = () =>
    toast.success(t("deleted"), { description: endpoint.name });

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger className="p-2" aria-label={t("open")}>
          <DotsThreeIcon weight="bold" />
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onClick={handleCopyUrl}>
            {t("copyUrl")}
          </DropdownMenuItem>
          <DropdownMenuItem onClick={handleToggleStatus}>
            {endpoint.status === "active" ? t("pause") : t("activate")}
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => setIsDeleteDialogOpen(true)}>
            {t("delete")}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <AlertDialog
        open={isDeleteDialogOpen}
        onOpenChange={setIsDeleteDialogOpen}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("deleteTitle")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("deleteDescription")}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t("cancel")}</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete}>
              {t("delete")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
