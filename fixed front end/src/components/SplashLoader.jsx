import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import PageLoader from "@/components/PageLoader";

// Shown once each time the site loads: plays the bottle animation through, then fades out.
export default function SplashLoader() {
  const [show, setShow] = useState(true);
  useEffect(() => {
    const timer = setTimeout(() => setShow(false), 2600);
    return () => clearTimeout(timer);
  }, []);
  return (
    <AnimatePresence>
      {show && (
        <motion.div exit={{ opacity: 0 }} transition={{ duration: 0.3 }} className="relative z-[100]">
          <PageLoader />
        </motion.div>
      )}
    </AnimatePresence>
  );
}