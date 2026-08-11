import { useState, useEffect } from "react";

const STRATEGIES_STORAGE_KEY = "finvista-custom-strategies";

export function useStrategies() {
  const [strategies, setStrategies] = useState([]);

  // Load strategies from localStorage on mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem(STRATEGIES_STORAGE_KEY);
      if (saved) {
        setStrategies(JSON.parse(saved));
      }
    } catch (error) {
      console.error("Failed to load strategies:", error);
    }
  }, []);

  // Save strategies to localStorage whenever they change
  useEffect(() => {
    try {
      localStorage.setItem(STRATEGIES_STORAGE_KEY, JSON.stringify(strategies));
    } catch (error) {
      console.error("Failed to save strategies:", error);
    }
  }, [strategies]);

  const saveStrategy = (strategy) => {
    setStrategies(prev => [...prev, strategy]);
  };

  const deleteStrategy = (id) => {
    setStrategies(prev => prev.filter(s => s.id !== id));
  };

  const updateStrategy = (id, updatedStrategy) => {
    setStrategies(prev => prev.map(s => s.id === id ? { ...s, ...updatedStrategy } : s));
  };

  const getStrategy = (id) => {
    return strategies.find(s => s.id === id);
  };

  return {
    strategies,
    saveStrategy,
    deleteStrategy,
    updateStrategy,
    getStrategy
  };
}
