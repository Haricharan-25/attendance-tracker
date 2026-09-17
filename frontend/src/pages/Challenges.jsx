import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api";
import BottomNav from "../components/BottomNav";

function Challenges() {
  const [challengesData, setChallengesData] = useState({
    user_progress: {
      level: 1,
      xp: 0,
      min_xp: 0,
      next_level_xp: 100,
      streak: 0,
      best_streak: 0,
    },
    active: [],
    completed: [],
  });
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
        if (chalRes.data) {
          // Check if format is new object or legacy array
          if (chalRes.data.active !== undefined) {
            setChallengesData(chalRes.data);
          } else if (Array.isArray(chalRes.data)) {
            setChallengesData({
              user_progress: {
                level: 1,
                xp: 0,
                min_xp: 0,
                next_level_xp: 100,
                streak: 0,
                best_streak: 0,
              },
              active: chalRes.data.filter((c) => !c.completed),
              completed: chalRes.data.filter((c) => c.completed),
            });
          }
        }
        setBadges(badgeRes.data || []);
        setError("");
      })
      .catch((err) => {
        console.error("Error loading challenges:", err);
        setError("Unable to load challenges. Please try again.");
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

  const { user_progress, active, completed } = challengesData;

  // Calculate XP progress bar percentage
  const currentXp = user_progress?.xp || 0;
  const minXp = user_progress?.min_xp || 0;
  const maxXp = user_progress?.next_level_xp || 100;
  const xpInLevel = Math.max(0, currentXp - minXp);
  const xpSpan = Math.max(1, maxXp - minXp);
  const xpPercentage = Math.min(Math.round((xpInLevel / xpSpan) * 100), 100);

  const getChallengeIcon = (type, isDone) => {
    if (isDone) return "✅";
    switch (type) {
      case "streak_3":
      case "streak_7":
        return "🔥";
      case "overall_75":
      case "overall_80":
        return "🎯";
      case "perfect_week":
        return "⚡";
      case "subject_saver":
        return "📚";
      default:
        return "🎯";
    }
  };

  const formatProgressDisplay = (c) => {
    if (c.challenge_type === "overall_75" || c.challenge_type === "overall_80") {
      return `${c.progress}% / ${c.target}%`;
    }
    if (c.challenge_type === "streak_3" || c.challenge_type === "streak_7") {
      return `${Math.round(c.progress)} / ${Math.round(c.target)} days`;
    }
    if (c.challenge_type === "perfect_week") {
      return c.progress >= 1.0 ? "1 / 1 week" : "In progress";
    }
    return `${Math.round(c.progress)} / ${Math.round(c.target)}`;
  };

  return (
    <div className="mobile-page-container">
      <header className="mobile-top-header">
        <div>
          <h1 className="user-title">Challenges</h1>
          <span className="sub-heading">Level up with attendance milestones</span>
        </div>
      </header>

      {/* Your Progress Card */}
      <div className="user-progress-hero-card">
        <div className="progress-hero-header">
          <span className="hero-level-pill">Level {user_progress?.level || 1}</span>
          <span className="hero-streak-pill">🔥 {user_progress?.streak || 0} Day Streak</span>
        </div>
        <div className="hero-xp-row">
          <span>{currentXp} / {maxXp} XP</span>
          <span>{xpPercentage}%</span>
        </div>
        <div className="hero-progress-bar-bg">
          <div
            className="hero-progress-bar-fill"
            style={{ width: `${xpPercentage}%` }}
          ></div>
        </div>
      </div>

      {/* Tab Switcher */}
      <div className="tab-pill-switcher">
        <button
          className={`tab-pill-btn ${activeTab === "challenges" ? "active" : ""}`}
          onClick={() => setActiveTab("challenges")}
        >
          Active ({active?.length || 0})
        </button>
        <button
          className={`tab-pill-btn ${activeTab === "completed" ? "active" : ""}`}
          onClick={() => setActiveTab("completed")}
        >
          Completed ({completed?.length || 0})
        </button>
        <button
          className={`tab-pill-btn ${activeTab === "badges" ? "active" : ""}`}
          onClick={() => setActiveTab("badges")}
        >
          Badges ({badges.filter((b) => b.earned).length}/{badges.length})
        </button>
      </div>

      {error && <div className="alert-message error">{error}</div>}

      {/* Active Challenges */}
      {activeTab === "challenges" && (
        <section>
          <div className="challenges-section-title">Active Challenges</div>
          <div className="quest-items-list">
            {(!active || active.length === 0) ? (
              <div className="empty-state-card mini">
                <p>No active challenges right now. Keep your attendance high!</p>
              </div>
            ) : (
              active.map((c) => (
                <div key={c.id} className="quest-card">
                  <div className="quest-icon-col">
                    {getChallengeIcon(c.challenge_type, false)}
                  </div>
                  <div className="quest-info-col">
                    <div className="quest-header-row">
                      <h3 className="quest-title">{c.name || c.title}</h3>
                    </div>

                    {c.subject && (
                      <span className="subject-badge-tag">{c.subject}</span>
                    )}

                    <p className="quest-desc">{c.description}</p>

                    <div className="quest-progress-block">
                      <div className="quest-progress-header">
                        <span>Progress</span>
                        <strong>{formatProgressDisplay(c)}</strong>
                      </div>
                      <div className="quest-progress-bar-bg">
                        <div
                          className="quest-progress-bar-fill"
                          style={{
                            width: `${Math.min(c.progress_percentage || 0, 100)}%`,
                          }}
                        ></div>
                      </div>
                    </div>

                    <div className="quest-footer">
                      <span className="reward-tag">+{c.reward_xp} XP</span>
                      <span className="quest-status text-pending">In Progress</span>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>
      )}

      {/* Completed Challenges */}
      {activeTab === "completed" && (
        <section>
          <div className="challenges-section-title">Completed Challenges</div>
          <div className="quest-items-list">
            {(!completed || completed.length === 0) ? (
              <div className="empty-state-card mini">
                <p>No challenges completed yet. Sync your attendance to start unlocking rewards!</p>
              </div>
            ) : (
              completed.map((c) => (
                <div key={c.id} className="quest-card quest-completed">
                  <div className="quest-icon-col">✅</div>
                  <div className="quest-info-col">
                    <div className="quest-header-row">
                      <h3 className="quest-title">{c.name || c.title}</h3>
                    </div>

                    {c.subject && (
                      <span className="subject-badge-tag">{c.subject}</span>
                    )}

                    <p className="quest-desc">{c.description}</p>

                    <div className="quest-progress-block">
                      <div className="quest-progress-bar-bg">
                        <div
                          className="quest-progress-bar-fill fill-completed"
                          style={{ width: "100%" }}
                        ></div>
                      </div>
                    </div>

                    <div className="quest-footer">
                      <span className="completed-reward-tag">+{c.reward_xp} XP earned</span>
                      <span className="quest-status text-safe">✓ Completed</span>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>
      )}

      {/* Badges / Achievements */}
      {activeTab === "badges" && (
        <section>
          <div className="challenges-section-title">Achievements</div>
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
        </section>
      )}

      <BottomNav />
    </div>
  );
}

export default Challenges;
