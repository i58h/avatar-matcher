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

# كل كم إطار نحلل في الـ GIF (كل 5 إطارات = متوازن)
GIF_FRAME_STEP = 5


def extract_gif_frames(image: Image.Image) -> list:
    """
    استخراج إطارات الـ GIF بخطوة GIF_FRAME_STEP.
    الإرجاع: قائمة من الإطارات كـ RGB images.
    """
    frames = []
    try:
        frame_index = 0
        while True:
            try:
                image.seek(frame_index)
                frames.append(image.copy().convert("RGB"))
                frame_index += GIF_FRAME_STEP
            except EOFError:
                break
    except Exception:
        pass

    # لو ما استخرجنا شيء، نرجع الإطار الأول
    if not frames:
        try:
            image.seek(0)
            frames = [image.copy().convert("RGB")]
        except Exception:
            pass

    return frames


def handle_animated_image(image: Image.Image) -> tuple:
    """
    معالجة الصور المتحركة (GIF وما شابهها).
    - لو متحركة: نرجع قائمة الإطارات للتحليل الشامل
    - لو ثابتة: نرجع الصورة مباشرة

    الإرجاع: (الصورة أو قائمة الإطارات، هل كانت متحركة)
    """
    is_animated = False
    try:
        if hasattr(image, "is_animated") and image.is_animated:
            is_animated = True
            frames = extract_gif_frames(image)
            return frames, True
    except Exception:
        pass

    try:
        return image.convert("RGB"), False
    except Exception:
        return image, False


def get_palette(image, n_colors: int = N_COLORS) -> list:
    """
    استخراج الباليتة اللونية من الصورة أو قائمة إطارات GIF.
    - صورة عادية: تحليل مباشر
    - قائمة إطارات GIF: دمج pixels من كل الإطارات ثم تحليل موحد

    الإرجاع: [(rgb_array, weight), ...] مرتبة تنازلياً حسب الانتشار.
    """
    try:
        # لو GIF (قائمة إطارات)
        if isinstance(image, list):
            return _get_palette_from_frames(image, n_colors)

        # صورة عادية
        return _get_palette_single(image, n_colors)

    except Exception:
        if isinstance(image, list) and image:
            return _get_palette_fallback(image[0], n_colors)
        elif not isinstance(image, list):
            return _get_palette_fallback(image, n_colors)
        return []


def _get_palette_from_frames(frames: list, n_colors: int = N_COLORS) -> list:
    """
    تحليل باليتة من قائمة إطارات GIF — يدمج الـ pixels من كل الإطارات.
    يعطي صورة أشمل للألوان المستخدمة في الـ GIF كامله.
    """
    all_pixels = []

    for frame in frames:
        img    = frame.resize(RESIZE_FOR_PALETTE, Image.LANCZOS)
        pixels = np.array(img).reshape(-1, 3).astype(np.float32)
        all_pixels.append(pixels)

    if not all_pixels:
        return []

    # دمج كل الإطارات في مصفوفة واحدة
    combined = np.vstack(all_pixels)

    # تقليل حجم البيانات لو كثيرة (أكثر من 50k pixel)
    if len(combined) > 50000:
        indices = np.random.choice(len(combined), 50000, replace=False)
        combined = combined[indices]

    k      = min(n_colors, len(combined))
    kmeans = MiniBatchKMeans(
        n_clusters=k,
        n_init=5,
        random_state=42,
        batch_size=2048,
    )
    kmeans.fit(combined)

    colors  = kmeans.cluster_centers_.astype(int)
    labels  = kmeans.labels_
    counts  = np.bincount(labels, minlength=k)
    weights = counts / counts.sum()

    return sorted(zip(colors, weights), key=lambda x: x[1], reverse=True)


def _get_palette_single(image: Image.Image, n_colors: int = N_COLORS) -> list:
    """استخراج باليتة من صورة واحدة باستخدام MiniBatchKMeans"""
    image  = image.convert("RGB")
    img    = image.resize(RESIZE_FOR_PALETTE, Image.LANCZOS)
    pixels = np.array(img).reshape(-1, 3).astype(np.float32)

    k      = min(n_colors, len(pixels))
    kmeans = MiniBatchKMeans(
        n_clusters=k,
        n_init=5,
        random_state=42,
        batch_size=1024,
    )
    kmeans.fit(pixels)

    colors  = kmeans.cluster_centers_.astype(int)
    labels  = kmeans.labels_
    counts  = np.bincount(labels, minlength=k)
    weights = counts / counts.sum()

    return sorted(zip(colors, weights), key=lambda x: x[1], reverse=True)


def _get_palette_fallback(image: Image.Image, n_colors: int = N_COLORS) -> list:
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
