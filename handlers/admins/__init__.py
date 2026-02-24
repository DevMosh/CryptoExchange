from aiogram import Router


def setup_admin_routers() -> Router:
    from . import admin

    router = Router()
    router.include_router(admin.admin_router)

    return router
