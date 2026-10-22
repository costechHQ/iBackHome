import type { Metadata } from "next";

import { Contact } from "@/features/public/contact";

export const metadata: Metadata = {
  title: "Contact · iBackHome",
  description:
    "Talk to iBackHome about a build, joining as a contractor or supervisor, or partnering with us.",
};

export default function Page() {
  return <Contact />;
}
