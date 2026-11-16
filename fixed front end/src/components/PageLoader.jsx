import BottleLoader from "@/components/BottleLoader";

export default function PageLoader() {
  return (
    <div role="status" className="fixed inset-0 z-[100] flex items-center justify-center bg-background">
      <BottleLoader />
      <span className="sr-only">Loading</span>
    </div>
  );
}