"""Screen Understanding — 屏幕理解模块 (Desktop Automation)

功能:
- 截取屏幕截图
- OCR文字检测(识别按钮/标签)
- 元素定位(按钮/输入框/链接的坐标)
"""

import io
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple
from pathlib import Path
from loguru import logger


@dataclass
class ScreenElement:
    """屏幕元素"""
    element_type: str  # button / text / input / link / icon
    text: str = ""
    bbox: Tuple[int, int, int, int] = (0, 0, 0, 0)  # x1,y1,x2,y2
    center: Tuple[int, int] = (0, 0)
    confidence: float = 0.0

    @property
    def width(self) -> int:
        return self.bbox[2] - self.bbox[0]
    
    @property
    def height(self) -> int:
        return self.bbox[3] - self.bbox[1]


@dataclass
class Screenshot:
    """屏幕截图数据"""
    image: bytes = b""
    width: int = 0
    height: int = 0
    timestamp: float = 0.0
    elements: List[ScreenElement] = None

    def __post_init__(self):
        if self.elements is None:
            self.elements = []


class ScreenCapture:
    """屏幕截图捕获"""
    
    def __init__(self):
        self._last_screenshot: Optional[Screenshot] = None
    
    def capture(self) -> Screenshot:
        """截取当前屏幕"""
        try:
            import pyautogui
            img = pyautogui.screenshot()
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            shot = Screenshot(
                image=buf.getvalue(),
                width=img.width,
                height=img.height,
                timestamp=time.time(),
            )
            self._last_screenshot = shot
            logger.debug(f"[screen] 截图 {img.width}x{img.height}")
            return shot
        except ImportError:
            logger.warning("[screen] pyautogui 未安装,使用模拟截图")
            return Screenshot(width=1920, height=1080, timestamp=time.time())


class ElementDetector:
    """屏幕元素检测(OCR + 视觉)
    
    使用策略:
    1. 优先用 pytesseract OCR 提取文字
    2. 通过文字匹配定位按钮/输入框
    3. 返回元素坐标供后续点击
    """
    
    def __init__(self):
        self._ocr_available = False
        self._check_ocr()
    
    def _check_ocr(self):
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            self._ocr_available = True
        except Exception:
            self._ocr_available = False
    
    def detect(self, screenshot: Screenshot, target_text: str = "") -> List[ScreenElement]:
        """检测屏幕中的文本元素"""
        elements = []
        
        if self._ocr_available and screenshot.image:
            elements = self._ocr_detect(screenshot, target_text)
        
        # OCR不可用时的降级: 返回模拟元素
        if not elements:
            elements = self._fallback_detect(screenshot, target_text)
        
        # 计算中心点
        for el in elements:
            el.center = (
                (el.bbox[0] + el.bbox[2]) // 2,
                (el.bbox[1] + el.bbox[3]) // 2,
            )
        
        return elements
    
    def _ocr_detect(self, screenshot: Screenshot, target: str) -> List[ScreenElement]:
        """OCR 检测"""
        try:
            import pytesseract
            from PIL import Image
            img = Image.open(io.BytesIO(screenshot.image))
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            elements = []
            for i, text in enumerate(data["text"]):
                if text.strip():
                    el = ScreenElement(
                        element_type="text",
                        text=text.strip(),
                        bbox=(data["left"][i], data["top"][i],
                              data["left"][i] + data["width"][i],
                              data["top"][i] + data["height"][i]),
                        confidence=data["conf"][i] / 100.0 if data["conf"][i] > 0 else 0.5,
                    )
                    if not target or target.lower() in text.lower():
                        elements.append(el)
            return elements
        except Exception as e:
            logger.warning(f"[screen] OCR失败: {e}")
            return []
    
    def _fallback_detect(self, screenshot: Screenshot, target: str) -> List[ScreenElement]:
        """降级: 无OCR时的占位检测"""
        if not target:
            return []
        # 假设目标在屏幕中央区域
        cx, cy = screenshot.width // 2, screenshot.height // 2
        return [ScreenElement(
            element_type="text",
            text=target,
            bbox=(cx - 100, cy - 20, cx + 100, cy + 20),
            confidence=0.3,
        )]
