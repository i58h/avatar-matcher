"""
app.py
------
واجهة Streamlit — تستورد من color_engine و image_utils فقط.
لا يوجد أي منطق خوارزمي هنا.
"""

import streamlit as st
from PIL import Image

from color_engine import match_palettes
from image_utils import get_palette, handle_animated_image, rgb_to_hex

# ============= إعدادات =============

MAX_BANNERS = 50

st.set_page_config(
    layout="wide",
    page_title="مطابقة الأفاتار مع البنرات",
    page_icon="🎨",
)

# ============= تهيئة الجلسة =============

if 'uploader_key' not in st.session_state:
    st.session_state.uploader_key = 0

if 'gif_count' not in st.session_state:
    st.session_state.gif_count = 0

# ============= دوال المعالجة =============

def process_banners(
    avatar_palette: list,
    uploaded_banners: list,
    progress_bar,
    status_text,
) -> list[dict]:
    """
    تحليل كل بنر ومقارنته بباليتة الأفاتار.
    الإرجاع: قائمة من {'filename', 'score', 'image'}
    """
    matches = []
    total   = len(uploaded_banners)

    for i, file in enumerate(uploaded_banners):
        status_text.text(f"جاري تحليل البنر {i + 1} من {total}: {file.name}")
        progress_bar.progress((i + 1) / total)

        try:
            banner, is_animated = handle_animated_image(Image.open(file))

            if is_animated:
                st.session_state.gif_count += 1

            banner_palette = get_palette(banner)
            if not banner_palette:
                continue

            score = match_palettes(avatar_palette, banner_palette)
            matches.append({
                'filename': file.name,
                'score':    score,
                'image':    banner.copy(),
            })
            banner.close()

        except Exception as e:
            st.warning(f"تعذر معالجة '{file.name}': {e}")

    return matches


def show_palette(palette: list) -> None:
    """عرض الباليتة اللونية كمربعات ملونة"""
    for color, pct in palette:
        hex_color = rgb_to_hex(color)
        st.markdown(
            f'<div style="background:{hex_color}; height:30px; border-radius:5px; margin-bottom:5px;"></div>'
            f'{hex_color} — {pct * 100:.1f}%',
            unsafe_allow_html=True,
        )


def show_results(matches: list) -> None:
    """عرض نتائج المطابقة مع pagination"""
    if not matches:
        st.error("❌ لم يتم العثور على بنرات")
        return

    matches.sort(key=lambda x: x['score'], reverse=True)

    st.markdown("### 🏆 أفضل البنرات المتناسقة")

    top   = matches[:6]
    rest  = matches[6:]

    _show_grid(top)

    if rest:
        with st.expander(f"عرض باقي النتائج ({len(rest)} بنر)"):
            _show_grid(rest)


def _show_grid(items: list) -> None:
    """عرض قائمة بنرات في شبكة 3 أعمدة"""
    cols = st.columns(3)
    for i, match in enumerate(items):
        with cols[i % 3]:
            st.image(match['image'], use_container_width=True)
            st.caption(f"📄 {match['filename']}")
            st.caption(f"⭐ التناسق: {match['score']:.1f}%")

# ============= واجهة المستخدم =============

st.title("🎨 مطابقة الأفاتار مع البنرات")

# --- رفع الأفاتار ---
st.markdown("### 📤 1. ارفع أفاتارك")

uploaded_avatar = st.file_uploader(
    "أضف الأفاتار",
    type=["png", "jpg", "jpeg", "webp", "jfif"],
    label_visibility="collapsed",
    key=f"avatar_{st.session_state.uploader_key}",
)

if uploaded_avatar:
    avatar, _ = handle_animated_image(Image.open(uploaded_avatar))
    avatar_palette = get_palette(avatar)

    col1, col2 = st.columns([1, 1])
    with col1:
        st.image(avatar, width=200)
    with col2:
        st.markdown("**🎨 ألوان الأفاتار:**")
        show_palette(avatar_palette)

    if st.button("🗑️ حذف الأفاتار", use_container_width=True):
        st.session_state.uploader_key += 1
        st.rerun()

    st.markdown("---")

    # --- رفع البنرات ---
    st.markdown("### 📤 2. اختر البنرات")

    uploaded_banners = st.file_uploader(
        "اختر البنرات",
        type=["png", "jpg", "jpeg", "webp", "gif"],
        accept_multiple_files=True,
        label_visibility="collapsed",
        key=f"banners_{st.session_state.uploader_key}",
    )

    if uploaded_banners:
        if len(uploaded_banners) > MAX_BANNERS:
            st.warning(f"⚠️ الحد الأقصى {MAX_BANNERS} بنر — سيتم تحليل أول {MAX_BANNERS} فقط")
            uploaded_banners = uploaded_banners[:MAX_BANNERS]

        st.success(f"✅ تم إضافة {len(uploaded_banners)} بنر")
        st.markdown("---")

        if st.button("🔍 ابدأ البحث", use_container_width=True, type="primary"):
            st.session_state.gif_count = 0

            progress_bar = st.progress(0)
            status_text  = st.empty()

            with st.spinner("جاري المقارنة..."):
                results = process_banners(
                    avatar_palette,
                    uploaded_banners,
                    progress_bar,
                    status_text,
                )

            progress_bar.empty()
            status_text.empty()

            if st.session_state.gif_count > 0:
                st.info(
                    f"ℹ️ تم العثور على {st.session_state.gif_count} صورة متحركة (GIF) "
                    f"— تم استخدام أول إطار فقط"
                )

            show_results(results)
