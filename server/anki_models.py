from typing import List, Optional
from pydantic import BaseModel, Field, AnyHttpUrl
import platform


host_os = platform.system()
class CardTemplate(BaseModel):
    name: str = Field(description="模板名称")
    qfmt: str = Field(description="正面 HTML 模板")
    afmt: str = Field(description="背面 HTML 模板")


class NoteData(BaseModel):
    field_data: List[str] = Field(description="与 field_names 顺序一致的字段值")
    media_paths: Optional[List[str]] = Field(
        default_factory=list,
        description=(
    "该笔记的媒体文件本地路径列表（会被打包进 .apkg）。所有路径必须位于服务器项目根目录内（默认即 MCP 服务当前工作目录），"
    "推荐使用相对路径；工具会在沙盒内解析并校验后自动打包这些资源。"
    f"本地路径必须符合当前系统的合法格式，当前服务器系统为: {host_os}"
),
    )


class CreateDeckRequest(BaseModel):
    deck_name: str = Field(description="Anki 牌组的名称")
    model_name: str = Field(description="Anki 模板（笔记类型）的名称")
    field_names: List[str] = Field(description="模板中字段的名称列表，例如 ['Question', 'Answer', 'Image']。这些字段的顺序将决定 'notes_data' 中 'field_data' 的顺序。")
    card_templates: List[CardTemplate] = Field(description='''卡片模板的列表。每个字典应包含 'name'、'qfmt' (正面 HTML) 和 'afmt' (背面 HTML)。例如：[{'name': 'Card 1', 'qfmt': '{{Question}}', 'afmt': '{{FrontSide}}<hr>{{Answer}}'}]''')
    notes_data: List[NoteData] = Field(description='''包含所有要添加到牌组的笔记数据的列表。
                                  每个字典必须包含一个 'field_data' 列表，其元素对应于 field_names 的顺序。
                                  它还可以包含一个可选的 'media_paths' 列表，指定该笔记所需的本地媒体文件路径。
                                  media_paths 中的每个文件路径必须位于服务器项目根目录内（推荐使用相对路径），否则请求会被拒绝。
                                  field_data 字段中导入媒体文件时,必须直接在媒体标签中填入媒体文件的本身名称,然后再在 media_paths 中填入实际路径
                                  示例：
                                  [
                                      {"field_data": ["What is gravity?", "A fundamental force...", "<img src='gravity.png'>"], "media_paths": ["./media/gravity.png"]},
                                      {"field_data": ["Capital of France?", "Paris", ""], "media_paths": []}
                                  ]''')
    model_css: Optional[str] = Field(default="",description="应用于所有卡片的 CSS 样式。默认为空字符串") 


class CreateDeckResult(BaseModel):
    status: str
    download_url: AnyHttpUrl
