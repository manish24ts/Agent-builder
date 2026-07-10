import { createContext, useContext, useEffect, useState } from "react";
import { api } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const stored = localStorage.getItem("user");
    return stored ? JSON.parse(stored) : null;
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      setLoading(false);
      return;
    }
    api
      .me()
      .then((u) => {
        setUser(u);
        localStorage.setItem("user", JSON.stringify(u));
      })
      .catch(() => {
        localStorage.removeItem("token");
        localStorage.removeItem("user");
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  function applyAuth(tokenOut) {
    localStorage.setItem("token", tokenOut.access_token);
    localStorage.setItem("user", JSON.stringify(tokenOut.user));
    setUser(tokenOut.user);
  }

  async function login(email, password) {
    const tokenOut = await api.login(email, password);
    applyAuth(tokenOut);
  }

  async function register(email, password, name) {
    const tokenOut = await api.register(email, password, name);
    applyAuth(tokenOut);
  }

  async function loginWithGoogle(idToken) {
    const tokenOut = await api.loginWithGoogle(idToken);
    applyAuth(tokenOut);
  }

  function logout() {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, loginWithGoogle, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
