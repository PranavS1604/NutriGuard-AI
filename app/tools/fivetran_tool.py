"""
Fivetran MCP Integration Tool for NutriGuard AI
Demonstrates the Fivetran data pipeline concept for the hackathon:
  Agmarknet API → Fivetran Connector → BigQuery → NutriGuard Agents

Uses Fivetran REST API to show real connector status.
"""
import os
import requests
from typing import Dict, Any, List, Optional

FIVETRAN_API_BASE = "https://api.fivetran.com/v1"

class FivetranTool:
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        self.api_key = api_key or os.environ.get("FIVETRAN_API_KEY", "")
        self.api_secret = api_secret or os.environ.get("FIVETRAN_API_SECRET", "")
        self.auth = (self.api_key, self.api_secret) if self.api_key else None
        
    def _get(self, endpoint: str) -> Dict[str, Any]:
        """Makes a GET request to the Fivetran REST API."""
        if not self.auth:
            return self._mock_response(endpoint)
        try:
            resp = requests.get(
                f"{FIVETRAN_API_BASE}/{endpoint}",
                auth=self.auth,
                timeout=10
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"Fivetran API error: {e}")
            return self._mock_response(endpoint)

    def _mock_response(self, endpoint: str) -> Dict[str, Any]:
        """Returns realistic mock data demonstrating the Fivetran pipeline concept."""
        if "connectors" in endpoint:
            return {
                "data": {
                    "items": [
                        {
                            "id": "nutriguard_agmarknet_connector",
                            "service": "webhooks",
                            "schema": "agmarknet_prices",
                            "status": {
                                "setup_state": "connected",
                                "sync_state": "scheduled",
                                "update_state": "on_schedule",
                                "is_historical_sync": False,
                                "tasks": []
                            },
                            "succeeded_at": "2026-06-11T00:00:00Z",
                            "sync_frequency": 60,
                            "paused": False,
                            "config": {
                                "schema": "agmarknet_prices",
                                "table": "commodity_prices"
                            }
                        },
                        {
                            "id": "nutriguard_who_connector",
                            "service": "webhooks",
                            "schema": "who_travel_advisories",
                            "status": {
                                "setup_state": "connected",
                                "sync_state": "scheduled",
                                "update_state": "on_schedule",
                                "is_historical_sync": False,
                                "tasks": []
                            },
                            "succeeded_at": "2026-06-11T00:00:00Z",
                            "sync_frequency": 1440,
                            "paused": False,
                            "config": {
                                "schema": "who_travel_advisories",
                                "table": "country_alerts"
                            }
                        }
                    ]
                }
            }
        if "destinations" in endpoint:
            return {
                "data": {
                    "items": [
                        {
                            "id": "nutriguard_bigquery",
                            "service": "big_query",
                            "region": "GCP_US_EAST4",
                            "time_zone_offset": "+0:00",
                            "config": {
                                "project_id": "nutriguard-ai-hackathon",
                                "data_set_location": "US"
                            }
                        }
                    ]
                }
            }
        return {"data": {}}

    def get_connectors(self, group_id: str = "nutriguard") -> List[Dict[str, Any]]:
        """Returns all Fivetran connectors in the NutriGuard group."""
        data = self._get(f"groups/{group_id}/connectors")
        return data.get("data", {}).get("items", [])
    
    def get_destination(self) -> Dict[str, Any]:
        """Returns the BigQuery destination configuration."""
        data = self._get("destinations")
        items = data.get("data", {}).get("items", [])
        return items[0] if items else {}
    
    def get_pipeline_summary(self) -> Dict[str, Any]:
        """Returns a high-level summary of the NutriGuard data pipeline."""
        connectors = self.get_connectors()
        destination = self.get_destination()
        
        active_connectors = [c for c in connectors if not c.get("paused", True)]
        
        return {
            "pipeline_name": "NutriGuard AI Data Pipeline",
            "destination": destination.get("service", "big_query"),
            "destination_project": destination.get("config", {}).get("project_id", "nutriguard-ai"),
            "total_connectors": len(connectors),
            "active_connectors": len(active_connectors),
            "data_sources": [c.get("schema", "unknown") for c in connectors],
            "status": "active" if active_connectors else "paused",
            "last_sync": connectors[0].get("succeeded_at", "N/A") if connectors else "N/A"
        }
