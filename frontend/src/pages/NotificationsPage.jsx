import React, { useState, useEffect } from 'react';

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [filter, setFilter] = useState('all');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadNotifications();
    const interval = setInterval(loadNotifications, 10000);
    return () => clearInterval(interval);
  }, []);

  const loadNotifications = async () => {
    try {
      const res = await fetch(`/api/notifications?limit=100&unread_only=${filter === 'unread'}`);
      const data = await res.json();
      setNotifications(data.notifications || []);
      setUnreadCount(data.unread_count || 0);
    } catch (err) {
      console.error('Failed to load notifications:', err);
    } finally {
      setLoading(false);
    }
  };

  const markRead = async (id) => {
    await fetch(`/api/notifications/${id}/read`, { method: 'POST' });
    loadNotifications();
  };

  const markAllRead = async () => {
    await fetch('/api/notifications/read-all', { method: 'POST' });
    loadNotifications();
  };

  const clearAll = async () => {
    await fetch('/api/notifications', { method: 'DELETE' });
    loadNotifications();
  };

  const levelIcon = (level) => {
    switch (level) {
      case 'info': return 'ℹ️';
      case 'warning': return '⚠️';
      case 'error': return '❌';
      case 'success': return '✅';
      default: return '📋';
    }
  };

  if (loading) return <p style={{ color: 'var(--text-muted)' }}>Loading notifications...</p>;

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1>Notifications</h1>
          <p>{unreadCount} unread notification{unreadCount !== 1 ? 's' : ''}</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <div style={{ display: 'flex', gap: 4 }}>
            <button className={`btn btn-sm ${filter === 'all' ? 'btn-primary' : ''}`} onClick={() => setFilter('all')}>All</button>
            <button className={`btn btn-sm ${filter === 'unread' ? 'btn-primary' : ''}`} onClick={() => setFilter('unread')}>Unread</button>
          </div>
          <button className="btn btn-sm" onClick={markAllRead}>Mark All Read</button>
          <button className="btn btn-sm btn-danger" onClick={clearAll}>Clear</button>
        </div>
      </div>

      {notifications.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: 40 }}>
          <p style={{ color: 'var(--text-muted)', fontSize: 16 }}>No notifications</p>
        </div>
      ) : (
        notifications.map((n) => (
          <div
            key={n.id}
            className="card"
            style={{
              marginBottom: 8,
              padding: 12,
              opacity: n.read ? 0.6 : 1,
              display: 'flex',
              alignItems: 'flex-start',
              gap: 12,
            }}
            onClick={() => !n.read && markRead(n.id)}
          >
            <span style={{ fontSize: 20 }}>{levelIcon(n.level)}</span>
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h4 style={{ fontSize: 14, fontWeight: 600 }}>{n.title}</h4>
                <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                  {new Date(n.created_at * 1000).toLocaleString()}
                </span>
              </div>
              {n.message && <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>{n.message}</p>}
              <div style={{ display: 'flex', gap: 8, marginTop: 4, fontSize: 11 }}>
                <span style={{ color: 'var(--accent-primary)' }}>{n.source}</span>
                <span style={{
                  color: n.level === 'error' ? 'var(--danger)' :
                         n.level === 'warning' ? 'var(--warning)' :
                         n.level === 'success' ? 'var(--success)' : 'var(--text-muted)',
                }}>{n.level}</span>
                {!n.read && <span style={{ color: 'var(--accent-primary)' }}>● New</span>}
              </div>
            </div>
          </div>
        ))
      )}
    </div>
  );
}
