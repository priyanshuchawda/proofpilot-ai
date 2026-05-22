import { render, screen } from "@testing-library/react";

import Home from "./page";

test("renders the API health check status", () => {
  render(<Home />);

  expect(screen.getByRole("heading", { name: "ProofPilot AI" })).toBeInTheDocument();
  expect(screen.getByText("API health")).toBeInTheDocument();
  expect(screen.getByText("Not checked yet")).toBeInTheDocument();
  expect(screen.getByText("Gemini mode")).toBeInTheDocument();
  expect(screen.getByText("gemini-2.5-flash-lite only")).toBeInTheDocument();
});
