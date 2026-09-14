import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api";
import BottomNav from "../components/BottomNav";

function Profile() {
  const [profile, setProfile] = useState(null);
  const [nickname, setNickname] = useState("");
  const [participate, setParticipate] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      navigate("/");
      return;
    }

    api
      .get("/profile/")
      .then((res) => {
        setProfile(res.data);
        setNickname(res.data.nickname || "");
        setParticipate(res.data.participate_leaderboard || false);
        setError("");
      })
      .catch((err) => {
        console.error(err);
        setError("Failed to load profile.");
      })
      .finally(() => setLoading(false));
  }, [navigate]);

  const handleUpdate = async (e) => {
    e.preventDefault();
    setSaving(true);
    setMessage("");
    setError("");

    if (participate && !nickname.trim()) {
      setError("Nickname is required when leaderboard participation is enabled.");
      setSaving(false);
      return;
    }

    try {
      const res = await api.patch("/profile/", {
        nickname: nickname.trim(),
        participate_leaderboard: participate,
      });

      setProfile(res.data);
      setMessage("Profile preferences saved successfully!");
      setTimeout(() => setMessage(""), 3000);
    } catch (err) {
      setError("Failed to update profile.");
    } finally {
      setSaving(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    navigate("/");
  };

  if (loading) {
    return (
      <div className="mobile-page-container flex-center">
        <div className="spinner"></div>
        <p className="loading-caption">Loading account settings...</p>
      </div>
    );
  }

  return (
    <div className="mobile-page-container">
      <header className="mobile-top-header">
        <div>
          <h1 className="user-title">Account Settings</h1>
          <span className="sub-heading">Roll Number & Privacy Settings</span>
        </div>
      </header>

      {/* Account Badge Card */}
      <div className="profile-hero-card">
        <div className="avatar-circle">
          {(profile?.nickname || profile?.username || "U").charAt(0).toUpperCase()}
        </div>
        <div className="profile-identity">
          <h2 className="profile-name">{profile?.nickname || profile?.username}</h2>
          <span className="profile-roll">Roll No: {profile?.username}</span>
        </div>

        <div className="profile-level-badge">
          <span>Level {profile?.level}</span>
        </div>
      </div>

      {/* Gamification Stats */}
      <div className="profile-stats-row">
        <div className="profile-stat-box">
          <span className="stat-label">Total XP</span>
          <span className="stat-val accent-xp">{profile?.xp}</span>
        </div>
        <div className="profile-stat-box">
          <span className="stat-label">Current Streak</span>
          <span className="stat-val">🔥 {profile?.current_streak} days</span>
        </div>
        <div className="profile-stat-box">
          <span className="stat-label">Best Streak</span>
          <span className="stat-val">⭐ {profile?.best_streak} days</span>
        </div>
      </div>

      {/* Preferences Form */}
      <div className="profile-settings-card">
        <h3>Public Display & Privacy</h3>
        <p className="settings-desc">
          Configure how your attendance metrics appear to peers. Private attendance records are never revealed on the leaderboard.
        </p>

        <form onSubmit={handleUpdate} className="profile-form">
          <div className="form-group checkbox-group">
            <label className="checkbox-toggle-label">
              <input
                type="checkbox"
                checked={participate}
                onChange={(e) => setParticipate(e.target.checked)}
              />
              <span className="checkbox-custom"></span>
              <span className="checkbox-text">
                Participate in public leaderboard
              </span>
            </label>
          </div>

          <div className="form-group">
            <label htmlFor="prof_nickname">
              Public Nickname {participate && <span className="required-star">*</span>}
            </label>
            <input
              id="prof_nickname"
              type="text"
              placeholder="e.g. Hari"
              value={nickname}
              onChange={(e) => setNickname(e.target.value)}
              required={participate}
            />
            <small className="field-hint">
              {participate
                ? "This name represents you on the leaderboard."
                : "Enter a nickname if you decide to join the leaderboard later."}
            </small>
          </div>

          {error && <div className="alert-message error">{error}</div>}
          {message && <div className="alert-message success">{message}</div>}

          <button type="submit" className="primary-btn" disabled={saving}>
            {saving ? "Saving Changes..." : "Save Preferences"}
          </button>
        </form>
      </div>

      {/* Danger / Logout Zone */}
      <div className="logout-zone">
        <button className="logout-full-btn" onClick={handleLogout}>
          Sign Out of Account
        </button>
      </div>

      <BottomNav />
    </div>
  );
}

export default Profile;
