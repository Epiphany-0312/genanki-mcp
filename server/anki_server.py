import os
import uuid
import asyncio
from pathlib import Path
from typing import Any
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP, Context
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles
import uvicorn

from .anki_models import CreateDeckRequest, CreateDeckResult
from anki_tools.genanki_tool import create_anki_deck_package

from dotenv import load_dotenv
load_dotenv()

# --- 配置 ---
PORT = int(os.environ.get('PORT', 10093))
SREVERIP = os.environ.get('SREVERIP', "127.0.0.1")
HOST = "0.0.0.0"
SANDBOX_ROOT = Path(__file__).resolve().parents[1]
TEMP_DOWNLOAD_DIR = SANDBOX_ROOT / "temp_anki_decks"
DOWNLOAD_PATH = "/downloads"
DOWNLOAD_EXPIRATION_SECONDS = 600
API_TOKEN = os.environ.get('TOKEN', '')  # 从环境变量加载TOKEN

# --- MCP-Server-Initialisierung ---
mcp = FastMCP(
    name="Anki Deck Server",
    streamable_http_path="/anki",
    host=HOST,
    port=PORT
)

# --- Starlette 应用生命周期管理 ---
@asynccontextmanager
async def lifespan(app: Starlette):
    """
    管理 MCP 服务器的生命周期。
    这对于初始化 MCP 的后台任务至关重要。
    """
    async with mcp.session_manager.run():
        print("MCP Session Manager started.")
        yield
    print("MCP Session Manager stopped.")


# --- 辅助函数 ---
def verify_token(ctx: Context) -> bool:
    """
    验证请求的Authorization头中的令牌是否有效
    """
    if not API_TOKEN:  # 如果未设置API_TOKEN，则不进行验证
        return True
    
    # 获取请求头信息 - 尝试不同的方式获取Authorization头
    headers = {}
    
    # 1. 尝试从meta中获取
    meta = ctx.request_context.meta
    if meta and hasattr(meta, 'get'):
        # 尝试小写和大写版本
        auth_header = meta.get('authorization', '') or meta.get('Authorization', '')
        if auth_header:
            headers['Authorization'] = auth_header
    
    # 2. 尝试从request的headers属性获取
    if not headers.get('Authorization') and hasattr(ctx.request_context, 'request'):
        request = ctx.request_context.request
        if hasattr(request, 'headers'):
            # 尝试小写和大写版本
            auth_header = request.headers.get('authorization', '') or request.headers.get('Authorization', '')
            if auth_header:
                headers['Authorization'] = auth_header
    
    # 检查是否找到Authorization头
    auth_header = headers.get('Authorization', '')
    
    # 检查格式为 "Bearer <token>"
    if not auth_header.startswith('Bearer '):
        print(f"认证失败: 无效的Authorization头格式 - {auth_header[:10]}...")
        return False
    
    token = auth_header.split('Bearer ')[1].strip()
    result = token == API_TOKEN
    
    if not result:
        print(f"认证失败: 令牌不匹配 - 收到的令牌前几位: {token[:3]}...")
    
    return result


def _resolve_within_sandbox(raw_path: str | Path, *, require_exists: bool = True) -> Path:
    """
    将传入路径解析为沙盒内的绝对路径，默认要求该路径存在。
    """
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = SANDBOX_ROOT / candidate
    candidate = candidate.resolve(strict=False)

    try:
        candidate.relative_to(SANDBOX_ROOT)
    except ValueError as exc:
        raise ValueError(f"路径不允许越过沙盒目录: {raw_path}") from exc

    if require_exists and not candidate.exists():
        raise ValueError(f"路径不存在或不可访问: {raw_path}")

    return candidate


@mcp.tool()
def health() -> dict[str, Any]:
    """
    健康检查工具。
    """
    return {
        "ok": True,
        "service": "mcp-anki-server",
        "cwd": os.getcwd(),
    }


@mcp.tool()
async def create_anki_deck(req: CreateDeckRequest, ctx: Context) -> CreateDeckResult:
    """
    基于传入参数创建 Anki 牌组并返回一个临时下载链接。
    下载链接有效期为 10 分钟。
    """
    # 验证请求的令牌
    if not verify_token(ctx):
        raise ValueError("认证失败：无效的访问令牌")
    
    # 1. 生成唯一的文件名和路径
    unique_filename = f"{uuid.uuid4()}.apkg"
    # 确保临时目录存在
    TEMP_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    output_filepath = TEMP_DOWNLOAD_DIR / unique_filename
    
    # 2. 转换模型以适应工具函数
    templates = [t.model_dump() for t in req.card_templates]
    sanitized_notes = []
    for note in req.notes_data:
        sanitized_media = [
            str(_resolve_within_sandbox(path))
            for path in (note.media_paths or [])
        ]
        sanitized_notes.append(
            {
                "field_data": note.field_data,
                "media_paths": sanitized_media,
            }
        )

    # 3. 创建牌组包
    create_anki_deck_package(
        deck_name=req.deck_name,
        model_name=req.model_name,
        field_names=req.field_names,
        card_templates=templates,
        notes_data=sanitized_notes,
        output_filename=str(output_filepath),
        model_css=req.model_css or "",
        sandbox_root=SANDBOX_ROOT,
    )

    # 4. 创建下载链接
    server_port = ctx.fastmcp.settings.port
    download_url = f"http://{SREVERIP}:{server_port}{DOWNLOAD_PATH}/{unique_filename}"

    # 5. 定义并调度清理任务
    async def delete_file_after_delay(path: Path | str, delay: int):
        await asyncio.sleep(delay)
        try:
            path = _resolve_within_sandbox(path, require_exists=False)
            if path.exists():
                path.unlink()
            print(f"成功删除临时文件: {path}")
        except (OSError, ValueError) as e:
            print(f"删除临时文件 {path} 时出错: {e}")

    asyncio.create_task(delete_file_after_delay(output_filepath, DOWNLOAD_EXPIRATION_SECONDS))

    # 6. 返回结果
    return CreateDeckResult(status="success", download_url=download_url)


# --- 主应用设置 ---
app = Starlette(
    routes=[
        Mount(DOWNLOAD_PATH, app=StaticFiles(directory=str(TEMP_DOWNLOAD_DIR)), name="downloads"),
        Mount("/", app=mcp.streamable_http_app()),
    ],
    lifespan=lifespan  # <-- 关键：将生命周期管理器附加到应用
)

def main() -> None:
    """启动组合的 ASGI 服务器。"""
    uvicorn.run(app, host=HOST, port=PORT)


if __name__ == "__main__":
    main()
