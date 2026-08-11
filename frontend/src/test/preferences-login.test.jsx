import React from "react";
import { act, fireEvent, render, renderHook, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { usePreferences } from "../app/usePreferences.js";
import { LoginPage } from "../pages/LoginPage.jsx";

describe("language preferences", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("defaults to Vietnamese and persists a later language choice", () => {
    const { result } = renderHook(() => usePreferences());
    expect(result.current.language).toBe("vi");

    act(() => result.current.setLanguage("en"));
    expect(localStorage.getItem("finvista-language")).toBe("en");
  });

  it("renders and submits the password login form using the selected language", () => {
    const auth = {
      error: "",
      loading: false,
      profileLoading: false,
      signInLoading: false,
      signIn: vi.fn()
    };
    const { rerender } = render(<LoginPage auth={auth} language="en" />);
    expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.getByLabelText("Username or email")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();

    rerender(<LoginPage auth={auth} language="vi" />);
    fireEvent.change(screen.getByLabelText("Username hoac email"), {
      target: { value: "tester@example.com" }
    });
    fireEvent.change(screen.getByLabelText("Mat khau"), {
      target: { value: "secret" }
    });
    fireEvent.click(screen.getByRole("button", { name: "Dang nhap" }));
    expect(auth.signIn).toHaveBeenCalledWith({
      username: "tester@example.com",
      password: "secret"
    });
  });
});
