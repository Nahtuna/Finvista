import React from "react";

import { AppShell } from "./app/AppShell.jsx";
import { DataProvider } from "./app/DataContext.jsx";


export default function App() {
  return (
    <DataProvider>
      <AppShell />
    </DataProvider>
  );
}
