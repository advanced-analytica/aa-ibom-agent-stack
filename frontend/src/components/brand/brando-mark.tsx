import Image from "next/image";

import { cn } from "@/lib/utils";

interface BrandoMarkProps {
  className?: string;
}

export function BrandoMark({ className }: BrandoMarkProps) {
  return (
    <span
      aria-hidden
      className={cn(
        "bg-foreground inline-flex h-6 w-6 shrink-0 items-center justify-center overflow-hidden rounded-md",
        className,
      )}
    >
      <Image
        src="/images/brand/brando-avatar.svg"
        alt=""
        width={24}
        height={24}
        className="h-full w-full object-cover"
      />
    </span>
  );
}
