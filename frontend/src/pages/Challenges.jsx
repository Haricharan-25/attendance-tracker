import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api";
import BottomNav from "../components/BottomNav";

function Challenges() {
  const [challenges, setChallenges] = useState([]);
  const [badges, setBadges] = useState([]);
  const [activeTab, setActiveTab] = useState("challenges");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      navigate("/");
      return;
    }

    Promise.all([api.get("/challenges/"), api.get("/badges/")])
      .then(([chalRes, badgeRes]) => {
        setChallenges(chalRes.data || []);
        setBadges(badgeRes.data || []);
        setError("");
      })
      .catch((err) => {
        console.error(err);
        setError("Failed to load challenges and badges.");
      })
      .finally(() => setLoading(false));
  }, [navigate]);

  if (loading) {
    return (
      <div className="mobile-page-container flex-center">
        <div className="spinner"></div>
        <p className="loading-caption">Loading quest board...</p>
      </div>
    );
  }

  return (
    <div className="mobile-page-container">
      <header className="mobile-top-header">
        <div>
          <h1 className="user-title">Quests & Badges</h1>
          <span className="sub-heading">Earn XP and level up your status</span>
        </div>
      </header>

      {/* Tab Switcher */}
      <div className="tab-pill-switcher">
        <button
          className={`tab-pill-btn ${activeTab === "challenges" ? "active" : ""}`}
          onClick={() => setActiveTab("challenges")}
        >
          Active Quests ({challenges.length})
        </button>
        <button
          className={`tab-pill-btn ${activeTab === "badges" ? "active" : ""}`}
          onClick={() => setActiveTab("badges")}
        >
          Badges ({badges.filter((b) => b.earned).length}/{badges.length})
        </button>
      </div>

      {error && <div className="alert-message error">{error}</div>}

      {/* Challenges List */}
      {activeTab === "challenges" && (
        <div className="quest-items-list">
          {challenges.length === 0 ? (
            <div className="empty-state-card mini">
              <p>No active challenges at the moment. Keep your attendance high!</p>
            </div>
          ) : (
            challenges.map((c) => (
              <div
                key={c.id}
                className={`quest-card ${c.completed ? "quest-completed" : ""}`}
              >
                <div className="quest-icon-col">
                  {c.completed ? "✅" : "🎯"}
                </div>
                <div className="quest-info-col">
                  <h3 className="quest-title">{c.title}</h3>
                  <p className="quest-desc">{c.description}</p>
                  <div className="quest-footer">
                    <span className="reward-tag">+{c.xp_reward} XP</span>
                    <span className={`quest-status ${c.completed ? "text-safe" : "text-pending"}`}>
                      {c.completed ? "Completed" : "In Progress"}
                    </span>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Badges Grid */}
      {activeTab === "badges" && (
        <div className="badges-grid-layout">
          {badges.length === 0 ? (
            <div className="empty-state-card mini">
              <p>No badges unlocked yet. Keep attending classes!</p>
            </div>
          ) : (
            badges.map((b) => (
              <div
                key={b.id}
                className={`badge-item-card ${b.earned ? "badge-unlocked" : "badge-locked"}`}
              >
                <div className="badge-icon-bubble">
                  {b.earned ? "🏆" : "🔒"}
                </div>
                <h4 className="badge-name">{b.name}</h4>
                <p className="badge-desc">{b.description}</p>
                <span className="badge-xp-reward">+{b.xp_reward} XP</span>
              </div>
            ))
          )}
        </div>
      )}

      <BottomNav />
    </div>
  );
}

export default Challenges;
