import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api";

function Register() {
  const navigate = useNavigate();

  const [form, setForm] = useState({
    roll_number: "",
    password: "",
    nickname: "",
    participate_leaderboard: false,
  });

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm({
      ...form,
      [name]: type === "checkbox" ? checked : value,
    });
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);

    try {
      const payload = {
        roll_number: form.roll_number.trim(),
        password: form.password,
        participate_leaderboard: form.participate_leaderboard,
      };

      if (form.participate_leaderboard) {
        payload.nickname = form.nickname.trim();
      }

      await api.post("/register/", payload);
      setSuccess("Account created successfully! Redirecting to login...");

      setTimeout(() => {
        navigate("/");
      }, 1200);
    } catch (err) {
      const data = err.response?.data;
      if (typeof data === "object" && data !== null) {
        const messages = Object.entries(data)
          .map(([field, message]) => {
            const text = Array.isArray(message) ? message.join(" ") : message;
            return `${field}: ${text}`;
          })
          .join(" | ");
        setError(messages || "Registration failed. Please check your inputs.");
      } else {
        setError("Registration failed. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-header">
          <div className="badge-pill">Student Portal</div>
          <h1>Create Account</h1>
          <p>Register with your official roll number</p>
        </div>

        <form onSubmit={handleRegister} className="auth-form">
          <div className="form-group">
            <label htmlFor="roll_number">Roll Number</label>
            <input
              id="roll_number"
              type="text"
              name="roll_number"
              placeholder="Enter roll number"
              value={form.roll_number}
              onChange={handleChange}
              autoCapitalize="none"
              required
            />
            <small className="field-hint">This will be your login identifier</small>
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              name="password"
              placeholder="Minimum 6 characters"
              value={form.password}
              onChange={handleChange}
              minLength={6}
              required
            />
          </div>

          <div className="form-group checkbox-group">
            <label className="checkbox-toggle-label">
              <input
                type="checkbox"
                name="participate_leaderboard"
                checked={form.participate_leaderboard}
                onChange={handleChange}
              />
              <span className="checkbox-custom"></span>
              <span className="checkbox-text">
                Participate in public leaderboard
              </span>
            </label>
          </div>

          {form.participate_leaderboard && (
            <div className="form-group animate-slide-down">
              <label htmlFor="nickname">
                Nickname <span className="required-star">*</span>
              </label>
              <input
                id="nickname"
                type="text"
                name="nickname"
                placeholder="Choose a public display name"
                value={form.nickname}
                onChange={handleChange}
                required={form.participate_leaderboard}
              />
              <small className="field-hint">
                This public name is shown on the leaderboard instead of your roll number.
              </small>
            </div>
          )}

          {error && <div className="alert-message error">{error}</div>}
          {success && <div className="alert-message success">{success}</div>}

          <button type="submit" className="primary-btn" disabled={loading}>
            {loading ? "Creating Account..." : "Create Account"}
          </button>
        </form>

        <div className="auth-footer">
          <p>
            Already have an account?{" "}
            <button
              type="button"
              className="text-link"
              onClick={() => navigate("/")}
            >
              Sign In
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}

export default Register;