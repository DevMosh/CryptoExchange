from aiogram import Router


def setup_routers() -> Router:
    from . import start
    from . import buy_usdt
    from . import sell_usdt

    router = Router()
    router.include_router(start.router)
    router.include_router(buy_usdt.router)
    router.include_router(sell_usdt.router)

    return router

# def setup_routers_other() -> Router:
#     from . import start
#
#     router_other = Router()
#     router_other.include_router(start.router_other)
#
#     return router_other