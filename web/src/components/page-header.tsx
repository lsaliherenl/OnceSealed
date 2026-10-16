import { Eyebrow } from "@/components/ui/card";

export function PageHeader({
  eyebrow,
  title,
  description,
  aside,
}: {
  eyebrow: string;
  title: string;
  description: React.ReactNode;
  aside?: React.ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-4">
      <div className="flex max-w-[720px] flex-col gap-2">
        <Eyebrow>{eyebrow}</Eyebrow>
        <h1 className="text-[34px] leading-[1.15] font-semibold tracking-[-0.02em]">{title}</h1>
        <p className="text-muted-foreground">{description}</p>
      </div>
      {aside}
    </div>
  );
}
