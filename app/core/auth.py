from starlette.authentication import (
    AuthenticationBackend,
    AuthCredentials,
    SimpleUser
)

class BasicAuthBackend(AuthenticationBackend):
    async def authenticate(self, conn):
        # Aquí luego metes JWT o DB
        return AuthCredentials(["authenticated"]), SimpleUser("admin")