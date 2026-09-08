import { DeskNav } from "../components/DeskNav";

export default function DeskLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="desk-frame">
      <DeskNav />
      {children}
    </div>
  );
}
