"""FastAPI local network server and mobile dashboard."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


class BreakRequest(BaseModel):
    reason: str


class UnfairBreakRequest(BaseModel):
    reason: str
    secret_code_1: str
    secret_code_2: str


class PlayerBreakRequest(BaseModel):
    reason: str
    secret_code: str


class PlayerBreakStopRequest(BaseModel):
    secret_code: str


class SecretCodeRequest(BaseModel):
    code: str


def create_app(state_manager) -> FastAPI:
    app = FastAPI(title="PC Rotation Manager Pro API", version="1.0.0")

    def _check_admin(authorization: str | None) -> None:
        token = state_manager.admin_token
        if not token:
            raise HTTPException(
                status_code=403,
                detail="Admin token not configured. POST actions disabled.",
            )
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing admin token.")
        if authorization[7:] != token:
            raise HTTPException(status_code=403, detail="Invalid admin token.")

    @app.get("/status")
    def get_status():
        return state_manager.get_status()

    @app.get("/logs")
    def get_logs():
        return {"logs": state_manager.logger.get_recent(50)}

    @app.post("/switch_player")
    def switch_player(authorization: str | None = Header(default=None)):
        _check_admin(authorization)
        ok, msg = state_manager.switch_player()
        if not ok:
            raise HTTPException(status_code=400, detail=msg)
        return {"ok": True, "message": msg, "status": state_manager.get_status()}

    @app.post("/start_break")
    def start_break(body: BreakRequest, authorization: str | None = Header(default=None)):
        _check_admin(authorization)
        ok, msg = state_manager.start_break(body.reason)
        if not ok:
            raise HTTPException(status_code=400, detail=msg)
        return {"ok": True, "message": msg, "status": state_manager.get_status()}

    @app.post("/start_unfair_break")
    def start_unfair_break(body: UnfairBreakRequest, authorization: str | None = Header(default=None)):
        _check_admin(authorization)
        ok, msg = state_manager.start_unfair_break(body.reason, body.secret_code_1, body.secret_code_2)
        if not ok:
            raise HTTPException(status_code=400, detail=msg)
        return {"ok": True, "message": msg, "status": state_manager.get_status()}

    @app.post("/start_player_break")
    def start_player_break(body: PlayerBreakRequest):
        """Start a break from mobile using the active player's secret code."""
        active = state_manager.state.active_player
        if not state_manager.verify_secret_code(active, body.secret_code):
            raise HTTPException(status_code=403, detail="Invalid secret code for the active player.")
        ok, msg = state_manager.start_break(body.reason)
        if not ok:
            raise HTTPException(status_code=400, detail=msg)
        return {"ok": True, "message": msg, "status": state_manager.get_status()}

    @app.post("/stop_player_break")
    def stop_player_break(body: PlayerBreakStopRequest):
        """Stop a break from mobile using the active player's secret code."""
        active = state_manager.state.active_player
        if not state_manager.verify_secret_code(active, body.secret_code):
            raise HTTPException(status_code=403, detail="Invalid secret code for the active player.")
        ok, msg = state_manager.stop_break()
        if not ok:
            raise HTTPException(status_code=400, detail=msg)
        return {"ok": True, "message": msg, "status": state_manager.get_status()}

    @app.post("/stop_break")
    def stop_break(authorization: str | None = Header(default=None)):
        _check_admin(authorization)
        ok, msg = state_manager.stop_break()
        if not ok:
            raise HTTPException(status_code=400, detail=msg)
        return {"ok": True, "message": msg, "status": state_manager.get_status()}

    @app.post("/set_secret_code/{player}")
    def set_secret_code(player: int, body: SecretCodeRequest, authorization: str | None = Header(default=None)):
        _check_admin(authorization)
        if player not in (1, 2):
            raise HTTPException(status_code=400, detail="Player must be 1 or 2.")
        import base64
        try:
            encoded = base64.b64encode(body.code.encode("utf-8")).decode("utf-8")
            state_manager.set_secret_code(player, encoded)
            return {"ok": True, "message": f"Secret code set for Player {player}"}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.get("/")
    def mobile_dashboard():
        dashboard = WEB_DIR / "dashboard.html"
        if dashboard.exists():
            return HTMLResponse(dashboard.read_text(encoding="utf-8"))
        return HTMLResponse("<h1>Dashboard not found</h1>", status_code=404)

    @app.get("/health")
    def health():
        return {
            "ok": True,
            "url": f"http://{state_manager.advertised_ip}:{state_manager.server_port}",
        }

    return app

