import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api";
import BottomNav from "../components/BottomNav";
import AttendancePlanner from "../components/AttendancePlanner";

function Dashboard() {
  const [dashboard, setDashboard] = useState(null);
  const [error, setError] = useState("");
  const [syncModalOpen, setSyncModalOpen] = useState(false);
  const [gemsPassword, setGemsPassword] = useState("");
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState("");
  const [syncTrigger, setSyncTrigger] = useState(0);

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

  const handleOneClickSync = async () => {
    const savedPassword = localStorage.getItem("gems_password");
    if (!savedPassword) {
      setSyncModalOpen(true);
      return;
    }

    setSyncing(true);
    setSyncMessage("Syncing with GEMS...");

    try {
      const res = await api.post("/sync/", { password: savedPassword });
      setSyncMessage(res.data.message || "Attendance updated!");
      fetchDashboard();
      setSyncTrigger((prev) => prev + 1);
      setTimeout(() => setSyncMessage(""), 3000);
    } catch (err) {
      const errMsg = err.response?.data?.message || "Failed to sync. Please verify password.";
      setSyncMessage(errMsg);
      // If unauthorized or invalid password, open modal to let them update
      if (err.response?.status === 400 || err.response?.status === 500) {
        setSyncModalOpen(true);
      }
      setTimeout(() => setSyncMessage(""), 4000);
    } finally {
      setSyncing(false);
    }
  };

  const handleSyncSubmit = async (e) => {
    e.preventDefault();
    if (!gemsPassword) return;

    setSyncing(true);
    setSyncMessage("");

    try {
      const res = await api.post("/sync/", { password: gemsPassword });
      localStorage.setItem("gems_password", gemsPassword);
      setSyncMessage(res.data.message || "Attendance updated!");
      setGemsPassword("");
      setTimeout(() => {
        setSyncModalOpen(false);
        setSyncMessage("");
        fetchDashboard();
        setSyncTrigger((prev) => prev + 1);
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
    localStorage.removeItem("gems_password");
    navigate("/");
  };

  const [showModalPassword, setShowModalPassword] = useState(false);

  if (error && !dashboard) {
    return (
      <div className="mobile-page-container">
        {syncMessage && (
          <div className={`sync-toast ${syncMessage.includes("updated") || syncMessage.includes("success") ? "success" : syncMessage.includes("Syncing") ? "" : "error"}`}>
            {syncing && <span className="spinner-sm"></span>}
            <span>{syncMessage}</span>
          </div>
        )}

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
            onClick={handleOneClickSync}
            disabled={syncing}
          >
            {syncing ? "⚡ Syncing..." : "⚡ Sync Attendance Now"}
          </button>
        </div>

        {syncModalOpen && (
          <div className="modal-backdrop">
            <div className="modal-sheet">
              <h3>Sync GEMS Attendance</h3>
              <p>Enter your GEMS password to fetch your latest attendance directly from the portal. It will be remembered for 1-click syncs.</p>
              <form onSubmit={handleSyncSubmit}>
                <div className="form-group">
                  <div className="password-input-wrapper">
                    <input
                      type={showModalPassword ? "text" : "password"}
                      placeholder="GEMS Password"
                      value={gemsPassword}
                      onChange={(e) => setGemsPassword(e.target.value)}
                      required
                    />
                    <button
                      type="button"
                      className="password-toggle-btn"
                      onClick={() => setShowModalPassword(!showModalPassword)}
                      title={showModalPassword ? "Hide password" : "Show password"}
                    >
                      {showModalPassword ? (
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                          <line x1="1" y1="1" x2="23" y2="23"/>
                        </svg>
                      ) : (
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                          <circle cx="12" cy="12" r="3"/>
                        </svg>
                      )}
                    </button>
                  </div>
                </div>
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
      {/* Toast Notification */}
      {syncMessage && (
        <div className={`sync-toast ${syncMessage.includes("updated") || syncMessage.includes("success") ? "success" : syncMessage.includes("Syncing") ? "" : "error"}`}>
          {syncing && <span className="spinner-sm"></span>}
          <span>{syncMessage}</span>
        </div>
      )}

      {/* Top Header */}
      <header className="mobile-top-header">
        <div>
          <span className="sub-heading">Welcome back</span>
          <h1 className="user-title">{dashboard.username}</h1>
        </div>
        <div className="header-actions">
          <button
            className="ghost-btn sync-pill-btn"
            onClick={handleOneClickSync}
            disabled={syncing}
            title="Sync Attendance"
          >
            {syncing ? "↻ Syncing..." : "↻ Sync"}
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

      {/* Attendance Planner Simulator */}
      <AttendancePlanner
        syncTrigger={syncTrigger}
        onSyncRequest={handleOneClickSync}
      />

      {/* Sync Modal */}
      {syncModalOpen && (
        <div className="modal-backdrop">
          <div className="modal-sheet">
            <h3>Sync GEMS Attendance</h3>
            <p className="modal-desc">
              Enter your GEMS password to fetch live attendance from the portal. It will be stored securely on your device for future 1-click syncs.
            </p>
            <form onSubmit={handleSyncSubmit}>
              <div className="form-group">
                <div className="password-input-wrapper">
                  <input
                    type={showModalPassword ? "text" : "password"}
                    placeholder="Enter GEMS password"
                    value={gemsPassword}
                    onChange={(e) => setGemsPassword(e.target.value)}
                    required
                  />
                  <button
                    type="button"
                    className="password-toggle-btn"
                    onClick={() => setShowModalPassword(!showModalPassword)}
                    title={showModalPassword ? "Hide password" : "Show password"}
                  >
                    {showModalPassword ? (
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                        <line x1="1" y1="1" x2="23" y2="23"/>
                      </svg>
                    ) : (
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                        <circle cx="12" cy="12" r="3"/>
                      </svg>
                    )}
                  </button>
                </div>
              </div>
              {syncMessage && (
                <div className={`alert-message ${syncMessage.includes("success") || syncMessage.includes("updated") ? "success" : "error"}`}>
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