import { RouterProvider } from "react-router-dom";
import { router } from "@/app/router/routes";

export function AppProviders() {
  return <RouterProvider router={router} />;
}
