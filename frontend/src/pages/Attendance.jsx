import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api";
import BottomNav from "../components/BottomNav";

function Attendance() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState("");

  const navigate = useNavigate();

  const loadData = () => {
    api
      .get("/dashboard/")
      .then((res) => {
        setData(res.data);
        setError("");
      })
      .catch((err) => {
        console.error(err);
        setError("Failed to load attendance records.");
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      navigate("/");
      return;
    }
    loadData();
  }, [navigate]);

  const handleOneClickSync = async () => {
    const savedPassword = localStorage.getItem("gems_password");
    if (!savedPassword) {
      navigate("/dashboard");
      return;
    }

    setSyncing(true);
    setSyncMessage("Syncing with GEMS...");

    try {
      const res = await api.post("/sync/", { password: savedPassword });
      setSyncMessage(res.data.message || "Attendance updated!");
      loadData();
      setTimeout(() => setSyncMessage(""), 3000);
    } catch (err) {
      setSyncMessage(err.response?.data?.message || "Failed to sync. Check credentials.");
      setTimeout(() => setSyncMessage(""), 4000);
    } finally {
      setSyncing(false);
    }
  };

  if (loading) {
    return (
      <div className="mobile-page-container flex-center">
        <div className="spinner"></div>
        <p className="loading-caption">Loading attendance...</p>
      </div>
    );
  }

  const subjects = data?.attendance || [];

  const filteredSubjects = subjects.filter((sub) => {
    const matchesSearch = sub.subject
      .toLowerCase()
      .includes(search.toLowerCase());

    if (filter === "all") return matchesSearch;
    return matchesSearch && sub.status.toLowerCase() === filter.toLowerCase();
  });

  return (
    <div className="mobile-page-container">
      {/* Toast Notification */}
      {syncMessage && (
        <div className={`sync-toast ${syncMessage.includes("updated") || syncMessage.includes("success") ? "success" : syncMessage.includes("Syncing") ? "" : "error"}`}>
          {syncing && <span className="spinner-sm"></span>}
          <span>{syncMessage}</span>
        </div>
      )}

      <header className="mobile-top-header">
        <div>
          <h1 className="user-title">Attendance Details</h1>
          <span className="sub-heading">
            {subjects.length} Total Registered Subjects
          </span>
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
        </div>
      </header>

      {/* Filter and Search Bar */}
      <div className="search-filter-section">
        <input
          type="text"
          className="search-input"
          placeholder="Search by subject code..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />

        <div className="filter-chips-row">
          {["all", "safe", "warning", "critical"].map((f) => (
            <button
              key={f}
              type="button"
              className={`filter-chip ${filter === f ? "active" : ""}`}
              onClick={() => setFilter(f)}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {error && <div className="alert-message error">{error}</div>}

      {/* Subjects Cards List */}
      <div className="attendance-cards-container">
        {filteredSubjects.length === 0 ? (
          <div className="empty-state-card mini">
            <p>No subjects match the selected criteria.</p>
          </div>
        ) : (
          filteredSubjects.map((sub) => {
            const statusClass = (sub.status || "safe").toLowerCase();
            return (
              <div
                key={sub.sno || sub.subject}
                className={`attendance-detail-card card-border-${statusClass}`}
              >
                <div className="card-top-row">
                  <div>
                    <h3 className="card-subject-name">{sub.subject}</h3>
                    <p className="attendance-metric">
                      {sub.attended} attended / {sub.total} conducted
                    </p>
                  </div>
                  <div className="perc-badge-wrap">
                    <span className={`perc-bubble bubble-${statusClass}`}>
                      {sub.percentage}%
                    </span>
                  </div>
                </div>

                <div className="progress-bar-sm">
                  <div
                    className={`progress-fill fill-${statusClass}`}
                    style={{ width: `${Math.min(sub.percentage, 100)}%` }}
                  />
                </div>

                <div className="card-calculation-grid">
                  <div className="calc-item">
                    <span className="calc-title">Status</span>
                    <span className={`status-pill-small pill-${statusClass}`}>
                      {sub.status}
                    </span>
                  </div>

                  <div className="calc-item">
                    <span className="calc-title">Required for 75%</span>
                    <span className="calc-value">
                      {sub.classes_needed_for_75 > 0 ? (
                        <span className="text-warning">
                          +{sub.classes_needed_for_75} classes
                        </span>
                      ) : (
                        <span className="text-safe">Satisfied</span>
                      )}
                    </span>
                  </div>

                  <div className="calc-item">
                    <span className="calc-title">Bunk Margin</span>
                    <span className="calc-value">
                      {sub.classes_can_miss > 0 ? (
                        <span className="text-safe">
                          {sub.classes_can_miss} classes
                        </span>
                      ) : (
                        <span className="text-muted">0 classes</span>
                      )}
                    </span>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      <BottomNav />
    </div>
  );
}

export default Attendance;
