import { useState, useEffect, useCallback } from 'react';
import { api } from '../utils/api';

export function useSettings() {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      const data = await api.getConfig();
      setConfig(data);
    } catch (err) {
      console.error('Failed to load config:', err);
    } finally {
      setLoading(false);
    }
  };

  const updateSetting = useCallback(async (key, value) => {
    try {
      await api.updateConfig(key, value);
      setConfig(prev => {
        if (!prev) return prev;
        const parts = key.split('.');
        const newConfig = { ...prev };
        let obj = newConfig;
        for (let i = 0; i < parts.length - 1; i++) {
          if (!obj[parts[i]]) obj[parts[i]] = {};
          obj = obj[parts[i]];
        }
        obj[parts[parts.length - 1]] = value;
        return newConfig;
      });
    } catch (err) {
      console.error('Failed to update config:', err);
    }
  }, []);

  return { config, loading, updateSetting, reload: loadConfig };
}
