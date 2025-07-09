# crawler/cli.py
"""開發與維運工具箱 (Dev & Ops Toolbox)。

提供一個基於 Typer 的強大命令行界面，作為與爬蟲系統交互的主要手動入口。
它封裝了資料庫初始化、手動觸發各平台 pipeline、以及針對單個 URL 進行
快速診斷等核心維運功能。
"""
import typer
import logging
from typing import List, Optional
import json
from pathlib import Path # 新增導入

from typing_extensions import Annotated
from crawler.enums import SourcePlatform
from crawler.factory import create_crawler

# 配置日誌，以便在 CLI 中看到詳細輸出
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger = logging.getLogger(__name__)

app = typer.Typer(name="crawler", help="多平台職缺爬蟲數據管道 CLI", add_completion=False)
db_app = typer.Typer(name="db", help="資料庫相關指令")
task_app = typer.Typer(name="task", help="手動任務執行器")
app.add_typer(db_app, name="db")
app.add_typer(task_app, name="task")


@db_app.command("init", help="初始化資料庫，創建所有表結構。")
def initialize_db_command() -> None:
    """初始化資料庫並創建所有在 schema.py 中定義的表。"""
    try:
        from crawler.database.connection import initialize_database
        typer.echo("正在初始化資料庫...")
        initialize_database()
        typer.secho("資料庫初始化成功。", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"資料庫初始化失敗: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

def _get_orchestrator(platform: SourcePlatform, category_ids: Optional[List[str]] = None) -> "CrawlerOrchestrator":
    """輔助函數，用於獲取配置好的 Orchestrator 實例。"""
    return create_crawler(platform, category_ids)

@task_app.command("urls", help="為指定平台執行 URL 獲取流程。")
def run_urls_pipeline_command(
    platform: Annotated[SourcePlatform, typer.Argument(help="要運行的平台。")],
    category_id: Annotated[Optional[List[str]], typer.Option("--category-id", "-c", help="指定要運行的分類 ID (可多次使用)。")] = None,
):
    """手動觸發 URL 獲取流程。"""
    typer.echo(f"正在為平台 {platform.value} 執行 URL pipeline...")
    if category_id:
        typer.echo(f"限定分類 IDs: {category_id}")
    else:
        typer.echo("未指定分類 ID，將抓取該平台所有分類。")

    try:
        orchestrator = _get_orchestrator(platform, category_ids=category_id)
        orchestrator.run_urls_pipeline()
        typer.secho(f"平台 {platform.value} 的 URL pipeline 執行完畢。", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"執行 URL pipeline 時發生錯誤: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

@task_app.command("details", help="為指定平台執行職缺詳情抓取流程。")
def run_details_pipeline_command(
    platform: Annotated[SourcePlatform, typer.Argument(help="要運行的平台。")],
    limit: Annotated[int, typer.Option(help="本次要處理的最大 URL 數量。")] = 100,
):
    """手動觸發職缺詳情抓取流程。"""
    typer.echo(f"正在為平台 {platform.value} 執行 Details pipeline，上限為 {limit} 筆...")
    try:
        orchestrator = _get_orchestrator(platform)
        orchestrator.run_details_pipeline(limit=limit)
        typer.secho(f"平台 {platform.value} 的 Details pipeline 執行完畢。", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"執行 Details pipeline 時發生錯誤: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

@task_app.command("debug-url", help="處理單一 URL 以進行偵錯，不會寫入資料庫。")
def debug_single_url(
    url: Annotated[str, typer.Argument(help="要偵錯的完整 URL。")],
    platform: Annotated[SourcePlatform, typer.Option(help="該 URL 所屬的平台。")],
    # [關鍵修正] 新增一個選項來保存 HTML
    save_html: Annotated[bool, typer.Option("--save-html", help="將抓取到的 HTML 內容保存到 debug.html 文件。")] = False
):
    """
    對單一 URL 執行 fetch -> parse 流程，並將結果打印到控制台。
    此功能是維運和開發新 Parser 時的強力工具。
    """
    typer.echo(f"正在為平台 {platform.value} 偵錯 URL: {url}")
    try:
        orchestrator = _get_orchestrator(platform)
        
        typer.echo("\n--- 1. 抓取內容 (Fetching) ---")
        raw_content = orchestrator.detail_fetcher(url)
        typer.echo(f"內容抓取成功，大小: {len(raw_content)} bytes。")
        
        # 如果用戶指定，則保存 HTML
        if save_html:
            debug_file = Path("debug.html")
            debug_file.write_text(raw_content, encoding='utf-8')
            typer.secho(f"已將抓取內容保存至專案根目錄下的 '{debug_file}' 文件。", fg=typer.colors.CYAN)

        typer.echo("\n--- 2. 解析內容 (Parsing) ---")
        job = orchestrator.detail_parser(raw_content, url, None)
        
        typer.echo("\n--- 3. 解析結果 (Parsed Job Object) ---")
        if job:
            job_json = json.dumps(json.loads(job.model_dump_json()), indent=2, ensure_ascii=False)
            typer.echo(job_json)
            typer.secho("\n偵錯成功！", fg=typer.colors.GREEN)
        else:
            typer.secho("\n解析器返回 None。", fg=typer.colors.YELLOW)

    except Exception as e:
        typer.secho(f"\n偵錯過程中發生錯誤: {e}", fg=typer.colors.RED, err=True)
        import traceback
        traceback.print_exc()
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()