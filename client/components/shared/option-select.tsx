"use client";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

export type Option = { value: string; label: string };

type OptionSelectProps = {
  value: string;
  onChange: (value: string) => void;
  options: Option[];
  id?: string;
  ariaLabel?: string;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
};

export function OptionSelect({
  value,
  onChange,
  options,
  id,
  ariaLabel,
  placeholder,
  disabled,
  className,
}: OptionSelectProps) {
  return (
    <Select
      items={options}
      value={value}
      disabled={disabled}
      onValueChange={(next) => {
        if (typeof next === "string") onChange(next);
      }}
    >
      <SelectTrigger
        id={id}
        aria-label={ariaLabel}
        className={cn("w-full min-w-40", className)}
      >
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent alignItemWithTrigger={false}>
        {options.map((option) => (
          <SelectItem key={option.value} value={option.value}>
            {option.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
