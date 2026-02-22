import SchematicBackground from "@/components/SchematicBackground";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0a0a0a]">
      <div className="opacity-40">
        <SchematicBackground />
      </div>
      <div className="relative z-10">
        {children}
      </div>
    </div>
  );
}
