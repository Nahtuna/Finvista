import React, { useState } from "react";
import { LogIn, UserPlus } from "lucide-react";
import { getLoginMessages } from "../i18n/index.js";

export function LoginPage({ auth, language = "en", colorMode = "light" }) {
  const messages = getLoginMessages(language);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isRegisterMode, setIsRegisterMode] = useState(false);

  async function submitLogin(event) {
    event.preventDefault();
    await auth.signIn({ username, password });
  }

  async function submitRegister(event) {
    event.preventDefault();
    // Use the backend API to register
    try {
      const response = await fetch('http://127.0.0.1:8008/api/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      });
      
      if (response.ok) {
        // After successful registration, login
        await auth.signIn({ username, password });
      } else {
        const data = await response.json();
        alert(data.detail || 'Registration failed');
      }
    } catch (error) {
      alert('Registration failed: ' + error.message);
    }
  }

  return (
    <main className={`login-shell color-${colorMode}`}>
      <div className="login-atmosphere" aria-hidden="true">
        <span className="login-grid-plane" />
        <span className="login-flow-line login-flow-one" />
        <span className="login-flow-line login-flow-two" />
        <span className="login-orbit-ring login-orbit-one" />
        <span className="login-orbit-ring login-orbit-two" />
        <span className="login-market-chip login-chip-one">VN30</span>
        <span className="login-market-chip login-chip-two">CW</span>
        <span className="login-market-chip login-chip-three">Z</span>
      </div>

      <section className="login-panel">
        <img src="/logo.svg" alt="Finvista Logo" className="brand-mark" style={{ width: "48px", height: "48px", borderRadius: "0.75rem", objectFit: "cover" }} />
        <div>
          <p className="eyebrow">Private beta</p>
          <h1>Finvista</h1>
          <p className="intro-text">{messages.intro}</p>
        </div>

        {auth.error ? <div className="notice error">{auth.error}</div> : null}

        <form className="login-form" onSubmit={isRegisterMode ? submitRegister : submitLogin} autoComplete="off">
          <label>
            <span>{messages.username}</span>
            <input
              autoComplete="off"
              name="username"
              type="text"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              required
            />
          </label>
          <label>
            <span>{messages.password}</span>
            <input
              autoComplete="off"
              name="password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </label>
          {isRegisterMode && (
            <div style={{ fontSize: "0.75rem", color: "#6b7280", marginTop: "0.5rem" }}>
              Password must be at least 12 characters with uppercase, lowercase, numbers, and special characters.
            </div>
          )}
          <button
            className="primary-button login-button"
            type="submit"
            disabled={auth.loading || auth.profileLoading || auth.signInLoading}
          >
            {isRegisterMode ? <UserPlus size={18} /> : <LogIn size={18} />}
            {isRegisterMode ? "Register" : (auth.signInLoading ? messages.signingIn : messages.action)}
          </button>
        </form>

        <p className="helper-text">{messages.help}</p>
        
        <div style={{ marginTop: "1rem", textAlign: "center" }}>
          <button
            type="button"
            onClick={() => setIsRegisterMode(!isRegisterMode)}
            style={{
              background: "none",
              border: "none",
              color: isRegisterMode ? "#4ade80" : "#22d3ee",
              cursor: "pointer",
              fontSize: "0.875rem",
              textDecoration: "underline"
            }}
          >
            {isRegisterMode ? "Already have an account? Sign in" : "Need an account? Register"}
          </button>
        </div>
      </section>
    </main>
  );
}
