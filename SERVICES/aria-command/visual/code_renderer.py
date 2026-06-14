"""
Code Renderer - Generate beautiful syntax-highlighted code images.

Uses Pygments for syntax highlighting and Pillow for image generation.
Creates visual diffs, code snippets, and architecture diagrams.
"""

import io
import os
import hashlib
from typing import Optional, Tuple, List
from dataclasses import dataclass
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    from pygments import highlight
    from pygments.lexers import get_lexer_by_name, get_lexer_for_filename, guess_lexer
    from pygments.formatters import HtmlFormatter
    from pygments.styles import get_style_by_name
    HAS_PYGMENTS = True
except ImportError:
    HAS_PYGMENTS = False


# Color schemes
THEMES = {
    "dark": {
        "background": "#0d1117",
        "text": "#c9d1d9",
        "line_numbers": "#6e7681",
        "selection": "#264f78",
        "addition": "#2ea043",
        "addition_bg": "#1a4721",
        "deletion": "#f85149",
        "deletion_bg": "#5d2321",
        "header": "#58a6ff",
        "border": "#30363d"
    },
    "light": {
        "background": "#ffffff",
        "text": "#24292f",
        "line_numbers": "#57606a",
        "selection": "#ddf4ff",
        "addition": "#1a7f37",
        "addition_bg": "#d1fadf",
        "deletion": "#cf222e",
        "deletion_bg": "#ffcecb",
        "header": "#0969da",
        "border": "#d0d7de"
    }
}


@dataclass
class CodeBlock:
    """Represents a block of code to render."""
    content: str
    language: str
    filename: Optional[str] = None
    start_line: int = 1
    highlight_lines: Optional[List[int]] = None


@dataclass
class DiffBlock:
    """Represents a diff to render."""
    original: str
    modified: str
    filename: str
    context_lines: int = 3


class CodeRenderer:
    """Renders code as beautiful images."""
    
    def __init__(self, theme: str = "dark", font_size: int = 14):
        self.theme = THEMES.get(theme, THEMES["dark"])
        self.font_size = font_size
        self.line_height = int(font_size * 1.5)
        self.padding = 20
        self.line_number_width = 50
        
        # Try to load a monospace font
        self.font = None
        self.font_bold = None
        if HAS_PIL:
            font_paths = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
                "/System/Library/Fonts/Monaco.ttf",
                "/System/Library/Fonts/SFMono-Regular.otf",
                "C:/Windows/Fonts/consola.ttf"
            ]
            for path in font_paths:
                if os.path.exists(path):
                    try:
                        self.font = ImageFont.truetype(path, font_size)
                        self.font_bold = ImageFont.truetype(path, font_size)
                        break
                    except:
                        pass
            
            if not self.font:
                self.font = ImageFont.load_default()
                self.font_bold = self.font
    
    def render_code(self, block: CodeBlock, max_width: int = 800) -> bytes:
        """Render a code block as a PNG image."""
        if not HAS_PIL:
            raise RuntimeError("Pillow is required for image rendering")
        
        lines = block.content.split('\n')
        
        # Calculate dimensions
        max_line_length = max(len(line) for line in lines) if lines else 0
        char_width = self.font_size * 0.6  # Approximate monospace width
        
        content_width = int(max_line_length * char_width)
        total_width = min(max_width, self.line_number_width + content_width + self.padding * 2)
        
        header_height = 40 if block.filename else 0
        content_height = len(lines) * self.line_height
        total_height = header_height + content_height + self.padding * 2
        
        # Create image
        img = Image.new('RGB', (total_width, total_height), self.theme["background"])
        draw = ImageDraw.Draw(img)
        
        y = self.padding
        
        # Draw header with filename
        if block.filename:
            draw.rectangle(
                [0, 0, total_width, header_height],
                fill=self._darken(self.theme["background"], 0.1)
            )
            draw.text(
                (self.padding, 10),
                block.filename,
                fill=self.theme["header"],
                font=self.font_bold
            )
            y = header_height + self.padding
        
        # Draw code lines
        for i, line in enumerate(lines):
            line_num = block.start_line + i
            
            # Highlight background if needed
            if block.highlight_lines and line_num in block.highlight_lines:
                draw.rectangle(
                    [0, y - 2, total_width, y + self.line_height - 2],
                    fill=self.theme["selection"]
                )
            
            # Line number
            draw.text(
                (self.padding, y),
                str(line_num).rjust(4),
                fill=self.theme["line_numbers"],
                font=self.font
            )
            
            # Code content
            draw.text(
                (self.line_number_width + self.padding, y),
                line[:100],  # Truncate long lines
                fill=self.theme["text"],
                font=self.font
            )
            
            y += self.line_height
        
        # Save to bytes
        buffer = io.BytesIO()
        img.save(buffer, format='PNG', optimize=True)
        return buffer.getvalue()
    
    def render_diff(self, diff: DiffBlock, max_width: int = 900) -> bytes:
        """Render a diff as a PNG image."""
        if not HAS_PIL:
            raise RuntimeError("Pillow is required for image rendering")
        
        # Parse diff
        import difflib
        original_lines = diff.original.split('\n')
        modified_lines = diff.modified.split('\n')
        
        differ = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=f"a/{diff.filename}",
            tofile=f"b/{diff.filename}",
            lineterm=""
        )
        diff_lines = list(differ)
        
        if not diff_lines:
            diff_lines = ["No changes"]
        
        # Calculate dimensions
        header_height = 60
        content_height = len(diff_lines) * self.line_height
        total_height = header_height + content_height + self.padding * 2
        
        # Create image
        img = Image.new('RGB', (max_width, total_height), self.theme["background"])
        draw = ImageDraw.Draw(img)
        
        # Draw header
        draw.rectangle([0, 0, max_width, header_height], fill=self._darken(self.theme["background"], 0.1))
        draw.text((self.padding, 15), f"Changes: {diff.filename}", fill=self.theme["header"], font=self.font_bold)
        
        # Count changes
        additions = sum(1 for l in diff_lines if l.startswith('+') and not l.startswith('+++'))
        deletions = sum(1 for l in diff_lines if l.startswith('-') and not l.startswith('---'))
        
        stats_text = f"+{additions} -{deletions}"
        draw.text((max_width - 100, 15), stats_text, fill=self.theme["text"], font=self.font)
        
        # Draw diff lines
        y = header_height + self.padding
        
        for line in diff_lines:
            bg_color = None
            text_color = self.theme["text"]
            
            if line.startswith('+++') or line.startswith('---') or line.startswith('@@'):
                text_color = self.theme["header"]
            elif line.startswith('+'):
                bg_color = self.theme["addition_bg"]
                text_color = self.theme["addition"]
            elif line.startswith('-'):
                bg_color = self.theme["deletion_bg"]
                text_color = self.theme["deletion"]
            
            if bg_color:
                draw.rectangle(
                    [0, y - 2, max_width, y + self.line_height - 2],
                    fill=bg_color
                )
            
            # Truncate line if too long
            display_line = line[:120] + "..." if len(line) > 120 else line
            draw.text((self.padding, y), display_line, fill=text_color, font=self.font)
            
            y += self.line_height
        
        # Save to bytes
        buffer = io.BytesIO()
        img.save(buffer, format='PNG', optimize=True)
        return buffer.getvalue()
    
    def render_file_tree(self, tree: dict, title: str = "Project Structure", max_width: int = 600) -> bytes:
        """Render a file tree as a PNG image."""
        if not HAS_PIL:
            raise RuntimeError("Pillow is required for image rendering")
        
        # Flatten tree to lines
        lines = []
        
        def traverse(node, prefix=""):
            for i, (name, value) in enumerate(node.items()):
                is_last = i == len(node) - 1
                connector = "└── " if is_last else "├── "
                icon = "📁 " if isinstance(value, dict) else "📄 "
                lines.append(f"{prefix}{connector}{icon}{name}")
                
                if isinstance(value, dict):
                    new_prefix = prefix + ("    " if is_last else "│   ")
                    traverse(value, new_prefix)
        
        traverse(tree)
        
        # Calculate dimensions
        header_height = 50
        content_height = len(lines) * self.line_height
        total_height = header_height + content_height + self.padding * 2
        
        # Create image
        img = Image.new('RGB', (max_width, total_height), self.theme["background"])
        draw = ImageDraw.Draw(img)
        
        # Draw header
        draw.rectangle([0, 0, max_width, header_height], fill=self._darken(self.theme["background"], 0.1))
        draw.text((self.padding, 12), title, fill=self.theme["header"], font=self.font_bold)
        
        # Draw tree
        y = header_height + self.padding
        for line in lines:
            draw.text((self.padding, y), line, fill=self.theme["text"], font=self.font)
            y += self.line_height
        
        # Save to bytes
        buffer = io.BytesIO()
        img.save(buffer, format='PNG', optimize=True)
        return buffer.getvalue()
    
    def _darken(self, hex_color: str, factor: float) -> str:
        """Darken a hex color by a factor."""
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        darkened = tuple(int(c * (1 - factor)) for c in rgb)
        return '#' + ''.join(f'{c:02x}' for c in darkened)
    
    def get_html_highlighted(self, code: str, language: str) -> str:
        """Get HTML with syntax highlighting (for web display)."""
        if not HAS_PYGMENTS:
            return f"<pre><code>{code}</code></pre>"
        
        try:
            lexer = get_lexer_by_name(language)
        except:
            lexer = guess_lexer(code)
        
        formatter = HtmlFormatter(
            style='monokai',
            noclasses=True,
            linenos=True,
            linenostart=1
        )
        
        return highlight(code, lexer, formatter)


# Singleton instance
_renderer = None

def get_renderer(theme: str = "dark") -> CodeRenderer:
    """Get or create a code renderer instance."""
    global _renderer
    if _renderer is None:
        _renderer = CodeRenderer(theme=theme)
    return _renderer


async def render_code_to_image(
    code: str,
    language: str = "python",
    filename: Optional[str] = None,
    highlight_lines: Optional[List[int]] = None
) -> bytes:
    """Convenience function to render code to an image."""
    renderer = get_renderer()
    block = CodeBlock(
        content=code,
        language=language,
        filename=filename,
        highlight_lines=highlight_lines
    )
    return renderer.render_code(block)


async def render_diff_to_image(
    original: str,
    modified: str,
    filename: str
) -> bytes:
    """Convenience function to render a diff to an image."""
    renderer = get_renderer()
    diff = DiffBlock(
        original=original,
        modified=modified,
        filename=filename
    )
    return renderer.render_diff(diff)


