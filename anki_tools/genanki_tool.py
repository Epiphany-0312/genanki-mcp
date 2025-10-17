import genanki
import random
import os
from pathlib import Path
from typing import List, Dict, Optional, Set

class AnkiDeckCreator:
    """
    一个用于通过编程创建 Anki 牌组的工具类。
    它封装了 genanki 库，提供更高级别的接口来定义模型、添加笔记和打包媒体文件。
    """
    def __init__(self, deck_name: str, model_name: str, field_names: List[str],
                 card_templates: List[Dict], model_css: str = "",
                 sandbox_root: Optional[Path] = None):
        """
        初始化 Anki 牌组创建器。
        """
        self.deck_name = deck_name
        self.model_name = model_name
        self.field_names = field_names
        self.card_templates = card_templates
        self.model_css = model_css
        self.sandbox_root = Path(sandbox_root).resolve() if sandbox_root else None

        self._model_id = random.randrange(1 << 30, 1 << 31)
        self._deck_id = random.randrange(1 << 30, 1 << 31)

        self.model = genanki.Model(
            self._model_id,
            self.model_name,
            fields=[{'name': field} for field in self.field_names],
            templates=self.card_templates,
            css=self.model_css
        )

        self.deck = genanki.Deck(self._deck_id, self.deck_name)
        self.media_files: Set[str] = set()

    def _resolve_media_path(self, raw_path: str) -> Optional[Path]:
        """
        将媒体文件路径解析为绝对路径，并在启用沙盒时校验其不越界。
        """
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            base = self.sandbox_root or Path.cwd()
            candidate = base / candidate

        candidate = candidate.resolve(strict=False)

        if self.sandbox_root:
            try:
                candidate.relative_to(self.sandbox_root)
            except ValueError as exc:
                raise ValueError(f"媒体文件路径越过沙盒目录: {raw_path}") from exc

        if not candidate.exists():
            print(f"--> 警告: 媒体文件 '{raw_path}' 不存在，将不会被包含在内。")
            return None

        return candidate

    def add_note(self, field_data: List[str], media_paths: List[str] = None):
        """
        向牌组添加一张笔记。
        """
        if len(field_data) != len(self.field_names):
            raise ValueError(
                f"Field data length mismatch. Expected {len(self.field_names)} fields, "
                f"got {len(field_data)}. Data: {field_data}"
            )

        note = genanki.Note(model=self.model, fields=field_data)
        self.deck.add_note(note)

        if media_paths:
            for path in media_paths:
                # 关键的检查点：服务器/脚本能否找到这个路径
                print(f"正在检查媒体文件路径: '{path}'")
                resolved = self._resolve_media_path(path)
                if not resolved:
                    continue
                print(f"--> 成功: 找到文件 '{resolved}'，将添加到卡组包。")
                self.media_files.add(str(resolved))

    def finalize_and_save(self, output_filename: str) -> str:
        """
        完成牌组创建并将牌组及其媒体文件保存为 .apkg 文件。
        """
        package = genanki.Package(self.deck)
        package.media_files = list(self.media_files)

        try:
            package.write_to_file(output_filename)
            return os.path.abspath(output_filename)
        except Exception as e:
            raise IOError(f"Failed to save Anki package to {output_filename}: {e}")


def create_anki_deck_package(
    deck_name: str,
    model_name: str,
    field_names: List[str],
    card_templates: List[Dict],
    notes_data: List[Dict],
    output_filename: str,
    model_css: str = "",
    sandbox_root: Optional[Path] = None
) -> str:
    """
    创建一个 Anki 牌组，添加多张笔记，并将其保存为 .apkg 文件。
    """
    creator = AnkiDeckCreator(
        deck_name,
        model_name,
        field_names,
        card_templates,
        model_css,
        sandbox_root=sandbox_root,
    )

    for note_item in notes_data:
        field_data = note_item.get("field_data")
        media_paths = note_item.get("media_paths", [])
        creator.add_note(field_data, media_paths)

    return creator.finalize_and_save(output_filename)


# ==============================================================================
# 当此脚本作为主程序直接运行时，执行以下代码块
# ==============================================================================
if __name__ == "__main__":
    
    print("--- 开始直接运行 Anki 卡组创建脚本 ---")
    
    # --- 1. 定义卡组的全部参数 ---
    
    # 从 "Agent 调用工具" 中提取的参数
    deck_name_param = "IP数据报知识卡片"
    model_name_param = "高级IP知识点模型"
    field_names_param = [
        "问题",
        "答案",
        "图片"
    ]
    card_templates_param = [
        {
          "name": "知识卡",
          "qfmt": "<div class=\"question-block\">\n  {{问题}}\n</div>",
          "afmt": "{{FrontSide}}\n<hr>\n<div class=\"answer-block\">\n  {{答案}}\n</div>\n<br>\n<img src=\"{{图片}}\" class=\"answer-image\">"
        }
    ]
    
    # 路径使用 r'' (raw string) 来避免反斜杠转义问题，这是最佳实践
    media_file_path = r"H:\output\deer.png"

    # 在运行前，先检查一下作为示例的媒体文件是否存在
    if not os.path.exists(media_file_path):
        print("\n" + "*"*50)
        print(f"错误：测试所需的媒体文件 '{media_file_path}' 不存在。")
        print("请确保该文件确实存在于指定路径，或者修改下面的 `media_file_path` 变量。")
        print("脚本将继续运行，但媒体文件将无法被打包。")
        print("*"*50 + "\n")


    notes_data_param = [
        {
          "field_data": [
            "IP数据报的报头中,哪个字段用于防止数据报在网络中无限循环?<br><div class=\"options-grid\"><div class=\"option\">A. 版本 (Version)</div><div class=\"option\">B. 头部长度 (Header Length)</div><div class=\"option\">C. 服务类型 (Type of Service)</div><div class=\"option\">D. 生存时间 (TTL)</div></div>",
            "<b>D. 生存时间 (TTL)</b><br>TTL (Time To Live) 字段是一个8位的计数器。每经过一个路由器,TTL的值就会减1。当TTL减到0时,路由器会丢弃该数据报,从而防止了数据报在网络中被无限转发。",
            "deer.png"  # 在 Anki 笔记字段中，我们通常只使用文件名
          ],
          "media_paths": [media_file_path]
        },
        {
          "field_data": [
            "当一个IP数据报的长度超过了链路的MTU(最大传输单元)时,会发生什么?<br><div class=\"options-grid\"><div class=\"option\">A. 数据报被丢弃</div><div class=\"option\">B. 数据报被分片</div><div class=\"option\">C. 数据报被拒绝</div><div class=\"option\">D. 数据报返回源主机</div></div>",
            "<b>B. 数据报被分片 (Fragmentation)</b><br>如果一个IP数据报的大小超过了下一跳链路的MTU,并且数据报的DF(Don't Fragment)标志位为0,那么路由器就会将该数据报分割成多个更小的数据报（即分片）进行传输。",
            "deer.png"
          ],
          "media_paths": [media_file_path]
        },
        {
          "field_data": [
            "在IPv4中,源IP地址和目的IP地址字段各占 ______ 位。",
            "在IPv4中,源IP地址和目的IP地址字段各占 <span class=\"fill-in-the-blank\">32</span> 位。<br>IPv4地址由32位二进制数组成,通常用点分十进制表示法书写,例如 192.168.1.1。",
            "deer.png"
          ],
          "media_paths": [media_file_path]
        },
        {
          "field_data": [
            "IP协议是一个 ______ 的协议,它不保证数据报的可靠交付。",
            "IP协议是一个 <span class=\"fill-in-the-blank\">无连接</span> 的协议,它不保证数据报的可靠交付。<br>IP协议提供的是“尽力而为”的服务,它不保证数据报一定能到达目的地,也不保证到达的顺序和发送顺序一致。可靠性由上层协议(如TCP)来保障。",
            "deer.png"
          ],
          "media_paths": [media_file_path]
        }
    ]
    model_css_param = ".card {\n    font-family: Arial, sans-serif;\n    font-size: 20px;\n    text-align: center;\n    color: #333;\n    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);\n    border-radius: 15px;\n    padding: 20px;\n    box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);\n}\n\n.question-block {\n    margin-bottom: 20px;\n    font-size: 24px;\n    font-weight: bold;\n    color: #2c3e50;\n}\n\n.options-grid {\n    display: grid;\n    grid-template-columns: 1fr 1fr;\n    gap: 10px;\n    margin: 20px auto;\n    max-width: 80%;\n    text-align: left;\n    font-weight: normal;\n}\n\n.option {\n    background-color: #ffffff;\n    border: 2px solid #bdc3c7;\n    border-radius: 10px;\n    padding: 15px;\n}\n\n.fill-in-the-blank {\n    font-weight: bold;\n    color: #c0392b;\n    background-color: #f9e5e3;\n    padding: 2px 8px;\n    border-radius: 5px;\n}\n\n.answer-block {\n    margin-top: 25px;\n    padding: 15px;\n    background-color: #e8f6f3;\n    border-left: 5px solid #1abc9c;\n    font-size: 20px;\n    color: #333;\n    text-align: left;\n}\n\n.answer-image {\n    margin-top: 15px;\n    max-width: 60%;\n    height: auto;\n    border-radius: 10px;\n    box-shadow: 0 2px 4px rgba(0,0,0,0.15);\n}"
    
    # --- 2. 调用核心函数 ---
    
    # 定义输出文件的名称
    output_file = "ip_knowledge_deck.apkg"
    
    try:
        # 调用函数创建卡组
        final_path = create_anki_deck_package(
            deck_name=deck_name_param,
            model_name=model_name_param,
            field_names=field_names_param,
            card_templates=card_templates_param,
            notes_data=notes_data_param,
            output_filename=output_file,
            model_css=model_css_param
        )
        print("\n--- 脚本执行完毕 ---")
        print(f"🎉 Anki 卡组包已成功创建！")
        print(f"   文件保存在: {final_path}")
        print("你可以将此 .apkg 文件直接导入到 Anki 中。")

    except Exception as e:
        print("\n--- 脚本执行出错 ---")
        print(f"创建 Anki 卡组时发生错误: {e}")
