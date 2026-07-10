import { useEffect, useRef } from "react";
import { useAuth } from "../context/AuthContext";
import { useNavigate } from "react-router-dom";

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

export default function GoogleButton() {
  const ref = useRef(null);
  const { loginWithGoogle } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID || !window.google || !ref.current) return;

    window.google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback: async (response) => {
        try {
          await loginWithGoogle(response.credential);
          navigate("/");
        } catch (err) {
          console.error(err);
          alert(err.message || "Google sign-in failed.");
        }
      },
    });

    window.google.accounts.id.renderButton(ref.current, {
      theme: "filled_black",
      size: "large",
      width: 316,
      shape: "rectangular",
    });
  }, [loginWithGoogle, navigate]);

  if (!GOOGLE_CLIENT_ID) {
    return (
      <div style={{ fontSize: 12, color: "var(--text-faint)", textAlign: "center" }}>
        Google sign-in isn't configured (set VITE_GOOGLE_CLIENT_ID).
      </div>
    );
  }

  return <div className="auth-google-btn" ref={ref} />;
}
