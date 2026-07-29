# -*- coding: utf-8 -*-
"""WebSocket connection manager and real-time event broadcaster."""

import asyncio
import json
from datetime import datetime
from typing import List, Dict, Set, Optional
from enum import Enum

from fastapi import WebSocket, WebSocketDisconnect


class EventType(str, Enum):
    """WebSocket event types for real-time updates."""
    CONNECTED = "connected"
    CW_SCAN_COMPLETED = "cw_scan_completed"
    ATC_SYNC_COMPLETED = "atc_sync_completed"
    MARKET_DATA_UPDATE = "market_data_update"
    PORTFOLIO_UPDATE = "portfolio_update"
    CREDIT_ALERT = "credit_alert"
    REGIME_CHANGE = "regime_change"
    DATA_FRESHNESS = "data_freshness"
    ERROR = "error"


class ConnectionManager:
    """
    Manages active WebSockets connections to stream real-time events to the SaaS Frontend.
    Supports subscription-based filtering and connection metadata.
    """

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_subscriptions: Dict[WebSocket, Set[str]] = {}
        self.connection_metadata: Dict[WebSocket, Dict] = {}

    async def connect(self, websocket: WebSocket, subscriptions: Optional[List[str]] = None):
        """Accept new WebSocket connection with optional subscriptions."""
        await websocket.accept()
        self.active_connections.append(websocket)
        
        # Initialize subscriptions
        if subscriptions:
            self.connection_subscriptions[websocket] = set(subscriptions)
        else:
            self.connection_subscriptions[websocket] = set()
        
        # Initialize metadata
        self.connection_metadata[websocket] = {
            "connected_at": datetime.now().isoformat(),
            "client_id": id(websocket),
        }
        
        print(
            f"🔌 [WebSocket] New client connected. Total connections: {len(self.active_connections)}"
        )
        
        # Send welcome message
        await websocket.send_json({
            "event": EventType.CONNECTED,
            "message": "Successfully connected to Finvista Quantitative WebSocket stream.",
            "timestamp": datetime.now().isoformat(),
            "subscriptions": list(self.connection_subscriptions[websocket]),
        })

    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection and cleanup."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        if websocket in self.connection_subscriptions:
            del self.connection_subscriptions[websocket]
        
        if websocket in self.connection_metadata:
            del self.connection_metadata[websocket]
        
        print(
            f"🔌 [WebSocket] Client disconnected. "
            f"Remaining connections: {len(self.active_connections)}"
        )

    async def broadcast(self, message: dict, event_type: Optional[str] = None):
        """
        Broadcast live updates to all connected web clients asynchronously.
        If event_type is specified, only send to subscribed clients.
        """
        if not self.active_connections:
            return

        # Add timestamp if not present
        if "timestamp" not in message:
            message["timestamp"] = datetime.now().isoformat()
        
        # Add event type if specified
        if event_type and "event" not in message:
            message["event"] = event_type

        # Filter connections based on subscriptions
        target_connections = []
        for connection in self.active_connections:
            subscriptions = self.connection_subscriptions.get(connection, set())
            if not event_type or event_type in subscriptions or not subscriptions:
                target_connections.append(connection)

        tasks = [connection.send_json(message) for connection in target_connections]
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Log any send errors
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"⚠️ [WebSocket] Send error to client {i}: {result}")

    async def send_personal(self, message: dict, websocket: WebSocket):
        """Send message to a specific WebSocket connection."""
        try:
            if "timestamp" not in message:
                message["timestamp"] = datetime.now().isoformat()
            await websocket.send_json(message)
        except Exception as e:
            print(f"⚠️ [WebSocket] Personal message error: {e}")

    def add_subscription(self, websocket: WebSocket, event_type: str):
        """Add subscription for a specific event type."""
        if websocket in self.connection_subscriptions:
            self.connection_subscriptions[websocket].add(event_type)

    def remove_subscription(self, websocket: WebSocket, event_type: str):
        """Remove subscription for a specific event type."""
        if websocket in self.connection_subscriptions:
            self.connection_subscriptions[websocket].discard(event_type)

    def get_connection_count(self) -> int:
        """Get current number of active connections."""
        return len(self.active_connections)

    def get_connection_info(self) -> Dict:
        """Get information about current connections."""
        return {
            "total_connections": len(self.active_connections),
            "connections": [
                {
                    "client_id": self.connection_metadata.get(ws, {}).get("client_id"),
                    "connected_at": self.connection_metadata.get(ws, {}).get("connected_at"),
                    "subscriptions": list(self.connection_subscriptions.get(ws, set())),
                }
                for ws in self.active_connections
            ]
        }


manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket):
    """
    Real-time WebSocket event broadcaster for portfolio NAV, market scanning states,
    and other real-time updates.
    
    Clients can:
    - Subscribe to specific event types by sending JSON: {"action": "subscribe", "events": ["cw_scan_completed"]}
    - Unsubscribe from events: {"action": "unsubscribe", "events": ["cw_scan_completed"]}
    - Send ping to keep connection alive: {"action": "ping"}
    """
    await manager.connect(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                
                # Handle subscription management
                if message.get("action") == "subscribe":
                    events = message.get("events", [])
                    for event in events:
                        manager.add_subscription(websocket, event)
                    await manager.send_personal({
                        "event": "subscription_updated",
                        "subscribed": events,
                        "timestamp": datetime.now().isoformat(),
                    }, websocket)
                
                elif message.get("action") == "unsubscribe":
                    events = message.get("events", [])
                    for event in events:
                        manager.remove_subscription(websocket, event)
                    await manager.send_personal({
                        "event": "subscription_updated",
                        "unsubscribed": events,
                        "timestamp": datetime.now().isoformat(),
                    }, websocket)
                
                elif message.get("action") == "ping":
                    await manager.send_personal({
                        "event": "pong",
                        "timestamp": datetime.now().isoformat(),
                    }, websocket)
                
                else:
                    await manager.send_personal({
                        "event": "error",
                        "message": f"Unknown action: {message.get('action')}",
                        "timestamp": datetime.now().isoformat(),
                    }, websocket)
            
            except json.JSONDecodeError:
                await manager.send_personal({
                    "event": "error",
                    "message": "Invalid JSON format",
                    "timestamp": datetime.now().isoformat(),
                }, websocket)
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"🔌 [WebSocket] Error: {e}")
        manager.disconnect(websocket)


# Convenience functions for broadcasting specific events
async def broadcast_cw_scan_completed(cache_invalidated: int):
    """Broadcast CW scan completion event."""
    await manager.broadcast({
        "event": EventType.CW_SCAN_COMPLETED,
        "cache_invalidated": cache_invalidated,
    }, EventType.CW_SCAN_COMPLETED)


async def broadcast_atc_sync_completed(trading_day: str, cache_invalidated: int):
    """Broadcast ATC sync completion event."""
    await manager.broadcast({
        "event": EventType.ATC_SYNC_COMPLETED,
        "trading_day": trading_day,
        "cache_invalidated": cache_invalidated,
    }, EventType.ATC_SYNC_COMPLETED)


async def broadcast_market_data_update(symbol: str, data: dict):
    """Broadcast market data update event."""
    await manager.broadcast({
        "event": EventType.MARKET_DATA_UPDATE,
        "symbol": symbol,
        "data": data,
    }, EventType.MARKET_DATA_UPDATE)


async def broadcast_portfolio_update(portfolio_data: dict):
    """Broadcast portfolio update event."""
    await manager.broadcast({
        "event": EventType.PORTFOLIO_UPDATE,
        "data": portfolio_data,
    }, EventType.PORTFOLIO_UPDATE)


async def broadcast_credit_alert(ticker: str, alert_data: dict):
    """Broadcast credit risk alert event."""
    await manager.broadcast({
        "event": EventType.CREDIT_ALERT,
        "ticker": ticker,
        "data": alert_data,
    }, EventType.CREDIT_ALERT)


async def broadcast_regime_change(regime_data: dict):
    """Broadcast market regime change event."""
    await manager.broadcast({
        "event": EventType.REGIME_CHANGE,
        "data": regime_data,
    }, EventType.REGIME_CHANGE)


async def broadcast_data_freshness(freshness_data: dict):
    """Broadcast data freshness status update."""
    await manager.broadcast({
        "event": EventType.DATA_FRESHNESS,
        "data": freshness_data,
    }, EventType.DATA_FRESHNESS)
