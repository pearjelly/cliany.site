import click


@click.command("serve")
@click.option("--host", default="127.0.0.1", help="绑定地址")
@click.option("--port", default=8080, type=int, help="监听端口")
@click.option("--json", "json_mode", is_flag=True, default=None, help="JSON 输出模式")
@click.pass_context
def serve_cmd(ctx: click.Context, host: str, port: int, json_mode: bool | None):
    """启动 HTTP API 服务"""
    root_ctx = ctx.find_root()
    root_obj = root_ctx.obj if isinstance(root_ctx.obj, dict) else {}
    cdp_url = root_obj.get("cdp_url")
    headless = root_obj.get("headless", False)

    from cliany_site.server import APIServer

    server = APIServer(host=host, port=port, cdp_url=cdp_url, headless=headless)
    server.run()
