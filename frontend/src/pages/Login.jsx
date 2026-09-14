import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api";

function Login() {
  const [rollNumber, setRollNumber] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const response = await api.post("/token/", {
        username: rollNumber.trim(),
        password: password,
      });

      localStorage.setItem("access_token", response.data.access);
      localStorage.setItem("refresh_token", response.data.refresh);

      navigate("/dashboard");
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        "Invalid roll number or password. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-header">
          <div className="badge-pill">Academic Portal</div>
          <h1>Attendance Tracker</h1>
          <p>Sign in to monitor your attendance and streak</p>
        </div>

        <form onSubmit={handleLogin} className="auth-form">
          <div className="form-group">
            <label htmlFor="login_roll">Roll Number</label>
            <input
              id="login_roll"
              type="text"
              placeholder="Enter roll number"
              value={rollNumber}
              onChange={(e) => setRollNumber(e.target.value)}
              autoCapitalize="none"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="login_password">Password</label>
            <input
              id="login_password"
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          {error && <div className="alert-message error">{error}</div>}

          <button type="submit" className="primary-btn" disabled={loading}>
            {loading ? "Signing In..." : "Sign In"}
          </button>
        </form>

        <div className="auth-footer">
          <p>
            Don't have an account?{" "}
            <button
              type="button"
              className="text-link"
              onClick={() => navigate("/register")}
            >
              Create Account
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}

export default Login;