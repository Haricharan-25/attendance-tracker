import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api";
import BottomNav from "../components/BottomNav";

function Dashboard() {
  const [dashboard, setDashboard] = useState(null);
  const [error, setError] = useState("");
  const [syncModalOpen, setSyncModalOpen] = useState(false);
  const [gemsPassword, setGemsPassword] = useState("");
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState("");

  const navigate = useNavigate();

  const fetchDashboard = () => {
    api
      .get("/dashboard/")
      .then((response) => {
        setDashboard(response.data);
        setError("");
      })
      .catch((err) => {
        console.error(err);
        if (err.response?.status === 404) {
          setError("No attendance records found yet. Sync with GEMS to load data.");
        } else {
          setError("Failed to load dashboard. Please try again.");
        }
      });
  };

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      navigate("/");
      return;
    }
    fetchDashboard();
  }, [navigate]);

  const handleSyncSubmit = async (e) => {
    e.preventDefault();
    if (!gemsPassword) return;

    setSyncing(true);
    setSyncMessage("");

    try {
      const res = await api.post("/sync/", { password: gemsPassword });
      setSyncMessage(res.data.message || "Attendance updated!");
      setGemsPassword("");
      setTimeout(() => {
        setSyncModalOpen(false);
        setSyncMessage("");
        fetchDashboard();
      }, 1500);
    } catch (err) {
      setSyncMessage(
        err.response?.data?.message || "Failed to sync. Check your password."
      );
    } finally {
      setSyncing(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    navigate("/");
  };

  if (error && !dashboard) {
    return (
      <div className="mobile-page-container">
        <header className="mobile-top-header">
          <div className="portal-badge">Attendance Tracker</div>
          <button className="icon-action-btn" onClick={handleLogout} title="Logout">
            ✕
          </button>
        </header>

        <div className="empty-state-card">
          <div className="empty-icon">📊</div>
          <h2>Welcome to Attendance Tracker</h2>
          <p>{error}</p>
          <button
            className="primary-btn sync-action-btn"
            onClick={() => setSyncModalOpen(true)}
          >
            ⚡ Sync Attendance Now
          </button>
        </div>

        {syncModalOpen && (
          <div className="modal-backdrop">
            <div className="modal-sheet">
              <h3>Sync GEMS Attendance</h3>
              <p>Enter your GEMS password to fetch your latest attendance directly from the portal.</p>
              <form onSubmit={handleSyncSubmit}>
                <input
                  type="password"
                  placeholder="GEMS Password"
                  value={gemsPassword}
                  onChange={(e) => setGemsPassword(e.target.value)}
                  required
                />
                {syncMessage && <p className="sync-status-msg">{syncMessage}</p>}
                <div className="modal-actions">
                  <button
                    type="button"
                    className="secondary-btn"
                    onClick={() => setSyncModalOpen(false)}
                    disabled={syncing}
                  >
                    Cancel
                  </button>
                  <button type="submit" className="primary-btn" disabled={syncing}>
                    {syncing ? "Fetching..." : "Fetch Records"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        <BottomNav />
      </div>
    );
  }

  if (!dashboard) {
    return (
      <div className="mobile-page-container flex-center">
        <div className="spinner"></div>
        <p className="loading-caption">Loading your attendance records...</p>
      </div>
    );
  }

  const overall = dashboard.overall;
  const statusClass = (overall.status || "safe").toLowerCase();

  return (
    <div className="mobile-page-container">
      {/* Top Header */}
      <header className="mobile-top-header">
        <div>
          <span className="sub-heading">Welcome back</span>
          <h1 className="user-title">{dashboard.username}</h1>
        </div>
        <div className="header-actions">
          <button
            className="ghost-btn sync-pill-btn"
            onClick={() => setSyncModalOpen(true)}
          >
            ↻ Sync GEMS
          </button>
          <button
            className="icon-action-btn"
            onClick={handleLogout}
            title="Sign out"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
              <polyline points="16 17 21 12 16 7"/>
              <line x1="21" y1="12" x2="9" y2="12"/>
            </svg>
          </button>
        </div>
      </header>

      {/* Main Overall Progress Card */}
      <section className={`overall-hero-card status-border-${statusClass}`}>
        <div className="overall-content">
          <div className="overall-label-row">
            <span className="card-tag">Overall Attendance</span>
            <span className={`status-pill pill-${statusClass}`}>
              {overall.status}
            </span>
          </div>
          <div className="percentage-hero">
            {overall.percentage}%
          </div>
          <div className="progress-bar-bg">
            <div
              className={`progress-fill fill-${statusClass}`}
              style={{ width: `${Math.min(overall.percentage, 100)}%` }}
            />
          </div>
          <div className="overall-stats-footer">
            <span>
              <strong>{overall.attended}</strong> / {overall.total} attended
            </span>
            <span>Target: 75%</span>
          </div>
        </div>
      </section>

      {/* Quick Gamification & Metric Grid */}
      <section className="stats-strip">
        <div className="mini-stat-card">
          <span className="mini-label">Subjects</span>
          <span className="mini-val">{dashboard.attendance?.length || 0}</span>
        </div>
        <div className="mini-stat-card">
          <span className="mini-label">XP</span>
          <span className="mini-val accent-xp">{dashboard.gamification?.xp || 0}</span>
        </div>
        <div className="mini-stat-card">
          <span className="mini-label">Level</span>
          <span className="mini-val accent-lvl">{dashboard.gamification?.level || 1}</span>
        </div>
        <div className="mini-stat-card">
          <span className="mini-label">Streak</span>
          <span className="mini-val">🔥 {dashboard.gamification?.current_streak || 0}</span>
        </div>
      </section>

      {/* Subject Summary List */}
      <section className="dashboard-section">
        <div className="section-header-row">
          <h2>Subject Breakdown</h2>
          <button
            className="text-action-link"
            onClick={() => navigate("/attendance")}
          >
            View All ({dashboard.attendance?.length || 0}) →
          </button>
        </div>

        <div className="subject-cards-list">
          {dashboard.attendance?.slice(0, 4).map((sub) => {
            const subStatusClass = (sub.status || "safe").toLowerCase();
            return (
              <div className="mobile-subject-card" key={sub.sno || sub.subject}>
                <div className="subject-card-head">
                  <div className="subject-title-box">
                    <span className="subject-code">{sub.subject}</span>
                    <span className="classes-ratio">
                      {sub.attended}/{sub.total} classes
                    </span>
                  </div>
                  <div className="subject-perc-box">
                    <span className={`perc-tag perc-${subStatusClass}`}>
                      {sub.percentage}%
                    </span>
                  </div>
                </div>

                <div className="progress-bar-sm">
                  <div
                    className={`progress-fill fill-${subStatusClass}`}
                    style={{ width: `${Math.min(sub.percentage, 100)}%` }}
                  />
                </div>

                <div className="subject-card-footer">
                  <span className={`status-text text-${subStatusClass}`}>
                    {sub.status}
                  </span>
                  {sub.classes_needed_for_75 > 0 ? (
                    <span className="target-chip alert-chip">
                      Need {sub.classes_needed_for_75} classes
                    </span>
                  ) : sub.classes_can_miss > 0 ? (
                    <span className="target-chip safe-chip">
                      Can miss {sub.classes_can_miss} classes
                    </span>
                  ) : (
                    <span className="target-chip on-track-chip">On track</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Sync Modal */}
      {syncModalOpen && (
        <div className="modal-backdrop">
          <div className="modal-sheet">
            <h3>Sync GEMS Attendance</h3>
            <p className="modal-desc">
              Enter your GEMS password to fetch live attendance from the portal. Credentials are used only for this request.
            </p>
            <form onSubmit={handleSyncSubmit}>
              <div className="form-group">
                <input
                  type="password"
                  placeholder="Enter GEMS password"
                  value={gemsPassword}
                  onChange={(e) => setGemsPassword(e.target.value)}
                  required
                />
              </div>
              {syncMessage && (
                <div className={`alert-message ${syncMessage.includes("success") ? "success" : "error"}`}>
                  {syncMessage}
                </div>
              )}
              <div className="modal-actions">
                <button
                  type="button"
                  className="secondary-btn"
                  onClick={() => setSyncModalOpen(false)}
                  disabled={syncing}
                >
                  Cancel
                </button>
                <button type="submit" className="primary-btn" disabled={syncing}>
                  {syncing ? "Connecting to GEMS..." : "Sync Now"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Bottom Navigation */}
      <BottomNav />
    </div>
  );
}

export default Dashboard;