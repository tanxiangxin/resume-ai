"""PDF 解析器。"""

import pymupdf

from chiren_backend.platform.exceptions import ParseError


class PDFParser:
    """PDF 文档解析器。"""

    @property
    def name(self) -> str:
        return "pdf"

    async def parse(self, file_path: str) -> dict:
        """
        提取 PDF 文本内容。

        Args:
            file_path: PDF 文件绝对路径。

        Returns:
            包含页数和提取文本的字典。

        Raises:
            ParseError: 解析失败时抛出。
        """
        try:
            with pymupdf.open(file_path) as doc:
                if doc.page_count > 100:
                    raise ParseError(
                        f"PDF 页数过多（{doc.page_count} 页），最大支持 100 页"
                    )

                text_parts = []
                for page in doc:
                    text_parts.append(page.get_text())

                return {
                    "pages": doc.page_count,
                    "text": "\n".join(text_parts),
                }
        except ParseError:
            raise
        except Exception as e:
            raise ParseError(f"PDF 解析失败: {str(e)}")


# 全局解析器实例
pdf_parser = PDFParser()
