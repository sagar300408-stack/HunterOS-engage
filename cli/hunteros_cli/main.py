import typer
import httpx
import os
from typing import Optional

app = typer.Typer(help="HunterOS Command Line Interface")

def get_base_url():
    return os.getenv("HUNTEROS_URL", "http://localhost:8000")

def get_token():
    return os.getenv("HUNTEROS_TOKEN")

@app.command()
def login(username: str, password: str = typer.Option(..., prompt=True, hide_input=True)):
    """Authenticate with HunterOS"""
    url = f"{get_base_url()}/api/v1/auth/login"
    try:
        response = httpx.post(url, data={"username": username, "password": password})
        if response.status_code == 200:
            token = response.json().get("access_token")
            typer.echo(f"Success! Export this token:\nexport HUNTEROS_TOKEN={token}")
        else:
            typer.echo(f"Login failed: {response.text}", err=True)
    except Exception as e:
        typer.echo(f"Error connecting to HunterOS: {e}", err=True)

@app.command()
def health():
    """Check platform health"""
    url = f"{get_base_url()}/api/v1/system/version"
    try:
        response = httpx.get(url)
        if response.status_code == 200:
            typer.echo(f"Platform is healthy: {response.json()}")
        else:
            typer.echo("Platform is degraded.", err=True)
    except Exception as e:
        typer.echo(f"Failed to connect: {e}", err=True)

@app.command("integration-list")
def integration_list():
    """List all integrations"""
    token = get_token()
    if not token:
        typer.echo("Please login first or set HUNTEROS_TOKEN.", err=True)
        raise typer.Exit(1)
        
    url = f"{get_base_url()}/api/v1/integrations"
    headers = {"Authorization": f"Bearer {token}"}
    
    response = httpx.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        for item in data:
            typer.echo(f"- {item['provider']} ({item['status']})")
    else:
        typer.echo(f"Failed: {response.status_code}", err=True)

if __name__ == "__main__":
    app()
