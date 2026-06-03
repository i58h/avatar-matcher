"""
image_utils.py
--------------
دوال معالجة الصور — استخراج الباليتة، التعامل مع GIF، تحويل الألوان.
منفصلة عن الخوارزمية وعن واجهة Streamlit.
"""

import numpy as np
from PIL import Image
from sklearn.cluster import KMeans, MiniBatchKMeans

# عدد الألوان المستخرجة من كل صورة
N_COLORS = 8

# حجم تصغير الصورة قبل التحليل (توازن بين الدقة والسرعة)
RESIZE_FOR_PALETTE = (250, 250)
RESIZE_FALLBACK    = (150, 150)


def handle_animated_image(image: Image.Image) -> tuple[Image.Image, bool]:
    """
    معالجة الصور المتحركة (GIF وما شابهها).
    الإرجاع: (الصورة بعد المعالجة، هل كانت متحركة)
    """
    is_animated = False
    try:
        if hasattr(image, "is_animated") and image.is_animated:
            is_animated = True
            image.seek(0)
            image = image.copy()
    except Exception:
        pass
    return image.convert("RGB"), is_animated


def get_palette(image: Image.Image, n_colors: int = N_COLORS) -> list[tuple]:
    """
    استخراج الباليتة اللونية من الصورة باستخدام KMeans.
    يستخدم MiniBatchKMeans للسرعة عند الصور الكبيرة.
    الإرجاع: [(rgb_array, weight), ...] مرتبة تنازلياً حسب الانتشار.
    """
    try:
        image = image.convert("RGB")
        img   = image.resize(RESIZE_FOR_PALETTE, Image.LANCZOS)
        pixels = np.array(img).reshape(-1, 3).astype(np.float32)

        k = min(n_colors, len(pixels))

        # MiniBatchKMeans أسرع بـ 3-5x من KMeans العادي مع نفس الدقة تقريباً
        kmeans = MiniBatchKMeans(
            n_clusters=k,
            n_init=5,
            random_state=42,
            batch_size=1024,
        )
        kmeans.fit(pixels)

        colors     = kmeans.cluster_centers_.astype(int)
        labels     = kmeans.labels_
        counts     = np.bincount(labels, minlength=k)
        weights    = counts / counts.sum()

        palette = sorted(zip(colors, weights), key=lambda x: x[1], reverse=True)
        return palette

    except Exception:
        return _get_palette_fallback(image, n_colors)


def _get_palette_fallback(image: Image.Image, n_colors: int = N_COLORS) -> list[tuple]:
    """
    طريقة بديلة أبطأ لكن أكثر استقراراً — تُستدعى فقط عند فشل الطريقة الأساسية.
    """
    try:
        image  = image.convert("RGB")
        img    = image.resize(RESIZE_FALLBACK, Image.LANCZOS)
        pixels = np.array(img).reshape(-1, 3)

        k      = min(n_colors, len(pixels))
        kmeans = KMeans(n_clusters=k, n_init=10, random_state=42)
        kmeans.fit(pixels)

        colors  = kmeans.cluster_centers_.astype(int)
        labels  = kmeans.labels_
        counts  = np.bincount(labels, minlength=k)
        weights = counts / counts.sum()

        return sorted(zip(colors, weights), key=lambda x: x[1], reverse=True)

    except Exception:
        return []


def rgb_to_hex(color) -> str:
    """تحويل RGB إلى Hex string"""
    return '#%02x%02x%02x' % tuple(int(c) for c in color)
