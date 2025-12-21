from fastmcp import FastMCP
from fastmcp.server.auth.providers.google import GoogleProvider
from app.config.settings import settings


auth_provider = GoogleProvider(
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    base_url="http://localhost:8000",
    required_scopes=[
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
    ],
)

mcp = FastMCP(name="Google Secured App", auth=auth_provider)


@mcp.tool
async def get_user_info() -> dict:
    """Returns information about the authenticated Google user."""
    from fastmcp.server.dependencies import get_access_token
    
    token = get_access_token()
    return {
        "google_id": token.claims.get("sub"),
        "email": token.claims.get("email"),
        "name": token.claims.get("name"),
        "picture": token.claims.get("picture"),
        "locale": token.claims.get("locale"),
    }


if __name__ == "__main__":
    mcp.run(transport="http", port=8000)





