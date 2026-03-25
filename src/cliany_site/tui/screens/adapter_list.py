import os
import shutil
import tarfile
from pathlib import Path

from textual.app import ComposeResult
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Header,
    Footer,
    DataTable,
    Static,
    Button,
    Input,
    TabbedContent,
    TabPane,
)
from textual.containers import Container, Horizontal, Vertical
from textual.widgets.data_table import CellDoesNotExist

from cliany_site.loader import discover_adapters, ADAPTERS_DIR
from cliany_site.atoms.storage import list_atoms
from cliany_site.tui.screens.adapter_detail import AdapterDetailScreen
from cliany_site.browser.launcher import find_chrome_binary
from cliany_site.explorer.engine import _load_dotenv
from cliany_site.activity_log import read_recent_logs


class ConfirmScreen(ModalScreen[bool]):
    def __init__(self, message: str):
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-dialog"):
            yield Static(self.message, id="confirm-message")
            with Horizontal(id="confirm-buttons"):
                yield Button("确认", variant="error", id="confirm")
                yield Button("取消", variant="primary", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm":
            self.dismiss(True)
        else:
            self.dismiss(False)


class InputPathScreen(ModalScreen[str]):
    def __init__(self, prompt: str):
        super().__init__()
        self.prompt = prompt

    def compose(self) -> ComposeResult:
        with Vertical(id="input-dialog"):
            yield Static(self.prompt, id="input-message")
            yield Input(placeholder="/path/to/archive.tar.gz", id="path-input")
            with Horizontal(id="input-buttons"):
                yield Button("确认", variant="primary", id="confirm")
                yield Button("取消", variant="default", id="cancel")

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm":
            self.dismiss(self.query_one(Input).value)
        else:
            self.dismiss("")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)


class AdapterListScreen(Screen):
    BINDINGS = [
        ("q", "app.quit", "退出"),
        ("r", "refresh_data", "刷新"),
        ("d", "delete_adapter", "删除"),
        ("e", "export_adapter", "导出"),
        ("i", "import_adapter", "导入"),
        ("l", "toggle_logs", "查看日志"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()

        with Container(id="env-status-panel", classes="panel"):
            yield Static("正在检测环境...", id="env-status-text")

        with TabbedContent(initial="tab-adapters"):
            with TabPane("适配器", id="tab-adapters"):
                yield Container(
                    DataTable(id="adapter-table"),
                    Static("暂无适配器", id="empty-state", classes="hidden"),
                )
            with TabPane("活动日志", id="tab-logs"):
                yield Container(
                    Static("暂无日志", id="logs-content"), id="logs-container"
                )

        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("域名", "命令数", "原子数", "创建时间")
        table.cursor_type = "row"
        self._load_data()
        self._update_env_status()
        self._load_logs()

    def _update_env_status(self) -> None:
        _load_dotenv()

        chrome_binary = find_chrome_binary()
        chrome_status = "可用" if chrome_binary else "未找到"

        has_llm = bool(
            os.environ.get("CLIANY_ANTHROPIC_API_KEY")
            or os.environ.get("CLIANY_OPENAI_API_KEY")
            or os.environ.get("ANTHROPIC_API_KEY")
            or os.environ.get("OPENAI_API_KEY")
        )
        llm_status = "已配置" if has_llm else "未配置"

        adapters = discover_adapters()
        adapter_count = len(adapters)

        atom_count = sum(len(list_atoms(a.get("domain", ""))) for a in adapters)

        status_text = f"🌐 Chrome: {chrome_status} | 🧠 LLM: {llm_status} | 🔌 适配器: {adapter_count} | 🧱 原子: {atom_count}"
        self.query_one("#env-status-text", Static).update(status_text)

    def _load_logs(self) -> None:
        logs = read_recent_logs(50)
        log_text = "\n".join(logs) if logs else "暂无日志"
        self.query_one("#logs-content", Static).update(log_text)

    def action_refresh_data(self) -> None:
        self._load_data()
        self._update_env_status()
        self._load_logs()

    def action_toggle_logs(self) -> None:
        tabs = self.query_one(TabbedContent)
        if tabs.active == "tab-adapters":
            tabs.active = "tab-logs"
            self._load_logs()
        else:
            tabs.active = "tab-adapters"

    def _load_data(self) -> None:
        table = self.query_one(DataTable)
        empty_state = self.query_one("#empty-state", Static)

        table.clear()

        adapters = discover_adapters()
        if not adapters:
            table.add_class("hidden")
            empty_state.remove_class("hidden")
            return

        table.remove_class("hidden")
        empty_state.add_class("hidden")

        for adapter in adapters:
            domain = adapter.get("domain", "")
            cmd_count = adapter.get("command_count", 0)
            atoms = list_atoms(domain)
            atom_count = len(atoms)

            metadata = adapter.get("metadata", {})
            created_at = metadata.get("created_at", "-")

            table.add_row(
                domain, str(cmd_count), str(atom_count), created_at, key=domain
            )

    def action_delete_adapter(self) -> None:
        table = self.query_one(DataTable)
        try:
            row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
            if not row_key or not row_key.value:
                return
            domain = str(row_key.value)
        except CellDoesNotExist:
            self.app.notify("请先选择一个适配器", severity="warning")
            return

        def check_delete(confirm: bool | None) -> None:
            if confirm:
                target_dir = ADAPTERS_DIR / domain
                if target_dir.exists():
                    try:
                        shutil.rmtree(target_dir)
                        self.app.notify(f"已删除: {domain}")
                        self._load_data()
                        self._update_env_status()
                    except OSError as e:
                        self.app.notify(f"删除失败: {e}", severity="error")

        self.app.push_screen(
            ConfirmScreen(f"确定要删除适配器 '{domain}' 吗？"), check_delete
        )

    def action_export_adapter(self) -> None:
        table = self.query_one(DataTable)
        try:
            row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
            if not row_key or not row_key.value:
                return
            domain = str(row_key.value)
        except CellDoesNotExist:
            self.app.notify("请先选择一个适配器", severity="warning")
            return

        target_dir = ADAPTERS_DIR / domain
        if not target_dir.exists():
            self.app.notify(f"目录不存在: {domain}", severity="error")
            return

        out_path = Path.cwd() / f"{domain}.tar.gz"
        try:
            with tarfile.open(out_path, "w:gz") as tar:
                tar.add(target_dir, arcname=domain)
            self.app.notify(f"导出成功: {out_path.name}")
        except (OSError, tarfile.TarError) as e:
            self.app.notify(f"导出失败: {e}", severity="error")

    def action_import_adapter(self) -> None:
        def do_import(path_str: str | None) -> None:
            if not path_str:
                return

            tar_path = Path(path_str).expanduser().resolve()
            if not tar_path.exists() or not tarfile.is_tarfile(tar_path):
                self.app.notify("无效的归档文件", severity="error")
                return

            try:
                with tarfile.open(tar_path, "r:gz") as tar:
                    members = tar.getmembers()
                    if not members:
                        self.app.notify("空归档文件", severity="error")
                        return

                    domains = {
                        m.name.split("/")[0]
                        for m in members
                        if "/" in m.name or m.isdir()
                    }
                    if not domains:
                        domains = {members[0].name}

                    domain = list(domains)[0]
                    target_dir = ADAPTERS_DIR / domain
                    if target_dir.exists():
                        self.app.notify(
                            f"适配器已存在，将被覆盖: {domain}", severity="warning"
                        )

                    ADAPTERS_DIR.mkdir(parents=True, exist_ok=True)
                    tar.extractall(path=ADAPTERS_DIR)
                    self.app.notify("导入成功")
                    self._load_data()
                    self._update_env_status()
            except (OSError, tarfile.TarError) as e:
                self.app.notify(f"导入失败: {e}", severity="error")

        self.app.push_screen(
            InputPathScreen("请输入要导入的 .tar.gz 文件路径:"), do_import
        )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        row_key = event.row_key
        if row_key and row_key.value:
            self.app.push_screen(AdapterDetailScreen(row_key.value))
