import React, { createContext, useContext, useState, useCallback, useEffect } from "react";
import { getOpportunities, getPortfolio, getUnderlyingMarket, getMarketRegime, getFireantArticles } from "../api.js";
import { useAuth } from "../auth/AuthProvider.jsx";

const DataContext = createContext(null);

export function DataProvider({ children }) {
  const { profile } = useAuth(); // profile = null until backend verifies token
  const [marketData, setMarketData] = useState(null);
  const [portfolioData, setPortfolioData] = useState(null);
  const [opportunitiesData, setOpportunitiesData] = useState(null);
  const [regimeData, setRegimeData] = useState(null);
  const [newsData, setNewsData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Data freshness tracking
  const [dataFreshness, setDataFreshness] = useState({
    market: null,
    portfolio: null,
    opportunities: null,
    regime: null,
    news: null
  });

  // Refresh all data
  const refreshAllData = useCallback(async (forceRefresh = false) => {
    setLoading(true);
    setError(null);
    
    try {
      const [oppRes, portRes, mktRes, regRes, newsRes] = await Promise.allSettled([
        getOpportunities({ strategy: "balanced", limit: 5000, forceRefresh }),
        profile ? getPortfolio() : Promise.resolve(null),
        getUnderlyingMarket({ forceRefresh }),
        getMarketRegime(),
        getFireantArticles(null, 5)
      ]);

      if (oppRes.status === "fulfilled") {
        setOpportunitiesData(oppRes.value);
        setDataFreshness(prev => ({ ...prev, opportunities: new Date().toISOString() }));
      }
      if (portRes.status === "fulfilled") {
        setPortfolioData(portRes.value);
        setDataFreshness(prev => ({ ...prev, portfolio: new Date().toISOString() }));
      } else if (portRes.reason?.message?.includes('Not authenticated') || portRes.reason?.message?.includes('401')) {
        console.warn('Portfolio data requires authentication');
        setPortfolioData(null);
      }
      if (mktRes.status === "fulfilled") {
        setMarketData(mktRes.value);
        setDataFreshness(prev => ({ ...prev, market: new Date().toISOString() }));
      }
      if (regRes.status === "fulfilled") {
        setRegimeData(regRes.value);
        setDataFreshness(prev => ({ ...prev, regime: new Date().toISOString() }));
      }
      if (newsRes.status === "fulfilled") {
        setNewsData(newsRes.value?.articles || []);
        setDataFreshness(prev => ({ ...prev, news: new Date().toISOString() }));
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [profile]); // Re-create when profile changes: null→user triggers portfolio fetch

  // Refresh specific data type
  const refreshDataType = useCallback(async (type, forceRefresh = false) => {
    try {
      const now = new Date().toISOString();
      
      switch (type) {
        case "market": {
          const mktRes = await getUnderlyingMarket({ forceRefresh });
          setMarketData(mktRes);
          setDataFreshness(prev => ({ ...prev, market: now }));
          break;
        }
        case "portfolio": {
          if (!profile) break;
          try {
            const portRes = await getPortfolio();
            setPortfolioData(portRes);
            setDataFreshness(prev => ({ ...prev, portfolio: now }));
          } catch (err) {
            if (err.message?.includes('Not authenticated') || err.message?.includes('401')) {
              setPortfolioData(null);
            } else {
              throw err;
            }
          }
          break;
        }
        case "opportunities": {
          const oppRes = await getOpportunities({ strategy: "balanced", limit: 5000, forceRefresh });
          setOpportunitiesData(oppRes);
          setDataFreshness(prev => ({ ...prev, opportunities: now }));
          break;
        }
        case "regime": {
          const regRes = await getMarketRegime();
          setRegimeData(regRes);
          setDataFreshness(prev => ({ ...prev, regime: now }));
          break;
        }
        case "news": {
          const newsRes = await getFireantArticles(null, 5);
          setNewsData(newsRes?.articles || []);
          setDataFreshness(prev => ({ ...prev, news: now }));
          break;
        }
      }
    } catch (err) {
      console.error(`Error refreshing ${type}:`, err);
    }
  }, [profile]); // Re-create when profile changes for portfolio guard

  // Initial data load
  useEffect(() => {
    refreshAllData(false);
  }, [refreshAllData]);

  // (No custom event needed: profile dep on refreshAllData handles post-login fetch automatically)

  // Auto-refresh during trading hours (every 30 seconds)
  useEffect(() => {
    const isTradingHours = () => {
      const now = new Date();
      const hours = now.getHours();
      const day = now.getDay();
      
      // Weekdays only (1-5, Monday-Friday)
      if (day === 0 || day === 6) return false;
      
      // Trading hours: 9:00-11:30 and 13:00-15:00 (Vietnam time UTC+7)
      return (hours >= 9 && hours < 12) || (hours >= 13 && hours < 15);
    };

    if (!isTradingHours()) return;

    const interval = setInterval(() => {
      refreshDataType("market", true);
      refreshDataType("opportunities", true);
    }, 30000); // 30 seconds

    return () => clearInterval(interval);
  }, [refreshDataType]);

  const value = {
    marketData,
    portfolioData,
    opportunitiesData,
    regimeData,
    newsData,
    loading,
    error,
    dataFreshness,
    refreshAllData,
    refreshDataType
  };

  return (
    <DataContext.Provider value={value}>
      {children}
    </DataContext.Provider>
  );
}

export function useData() {
  const context = useContext(DataContext);
  if (!context) {
    throw new Error("useData must be used within a DataProvider");
  }
  return context;
}
