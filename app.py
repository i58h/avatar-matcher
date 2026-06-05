"""
app.py
------
واجهة Streamlit — تستورد من color_engine و image_utils فقط.
الكاشينج: البنرات تتحلل مرة وحدة وتبقى حتى لو تغير الأفاتار.
"""

import streamlit as st
from PIL import Image

from color_engine import match_palettes, get_harmony_colors
from image_utils import get_palette, handle_animated_image, rgb_to_hex

# ============= إعدادات =============

MAX_BANNERS = 400

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

if 'gif_frames' not in st.session_state:
    st.session_state.gif_frames = 0

# الكاش: باليتات البنرات المحللة مسبقاً
# { filename: { 'palette': [...], 'image': Image, 'is_gif': bool } }
if 'banners_cache' not in st.session_state:
    st.session_state.banners_cache = {}

# ============= دوال المعالجة =============

def analyze_banners(uploaded_banners: list, progress_bar, status_text) -> None:
    """
    تحليل البنرات الجديدة فقط (غير الموجودة في الكاش) وحفظ باليتاتها.
    البنرات المحللة مسبقاً تُتجاهل.
    """
    cache    = st.session_state.banners_cache
    new_only = [f for f in uploaded_banners if f.name not in cache]
    total    = len(new_only)

    if total == 0:
        status_text.text("✅ كل البنرات محللة مسبقاً")
        progress_bar.progress(1.0)
        return

    for i, file in enumerate(new_only):
        status_text.text(f"جاري تحليل البنر {i+1} من {total}: {file.name}")
        progress_bar.progress((i+1) / total)

        try:
            banner, is_animated = handle_animated_image(Image.open(file))

            if is_animated:
                frames = len(banner) if isinstance(banner, list) else 1
                st.session_state.gif_count  += 1
                st.session_state.gif_frames += frames

            banner_palette = get_palette(banner)
            if not banner_palette:
                continue

            display_img = banner[0] if isinstance(banner, list) else banner

            cache[file.name] = {
                'palette':  banner_palette,
                'image':    display_img.copy(),
                'is_gif':   is_animated,
            }

            if not isinstance(banner, list):
                banner.close()

        except Exception as e:
            st.warning(f"تعذر معالجة '{file.name}': {e}")


def compute_scores(avatar_palette: list, uploaded_banners: list) -> list:
    """
    حساب درجات التناسق فقط — البنرات محللة مسبقاً في الكاش.
    سريع جداً لأنه لا يفتح أي صورة.
    """
    cache   = st.session_state.banners_cache
    results = []

    for file in uploaded_banners:
        cached = cache.get(file.name)
        if not cached:
            continue

        score   = match_palettes(avatar_palette, cached['palette'])
        harmony = get_harmony_colors(avatar_palette, cached['palette'])

        results.append({
            'filename': file.name,
            'score':    score,
            'image':    cached['image'],
            'harmony':  harmony,
        })

    results.sort(key=lambda x: x['score'], reverse=True)
    return results


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

    st.markdown("### 🏆 أفضل البنرات المتناسقة")
    _show_grid(matches[:6])

    if len(matches) > 6:
        with st.expander(f"عرض باقي النتائج ({len(matches) - 6} بنر)"):
            _show_grid(matches[6:])


def _show_grid(items: list) -> None:
    """عرض شبكة 3 أعمدة مع ألوان التناسق"""
    cols = st.columns(3)
    for i, match in enumerate(items):
        with cols[i % 3]:
            st.image(match['image'], use_container_width=True)
            st.caption(f"📄 {match['filename']}")
            st.caption(f"⭐ التناسق: {match['score']:.1f}%")

            if match.get('harmony'):
                swatches = "".join(
                    f'<span title="{h}" style="display:inline-block;width:28px;height:28px;'
                    f'background:{h};border-radius:50%;margin:2px;border:2px solid #fff;'
                    f'box-shadow:0 0 3px #0003;"></span>'
                    for h in match['harmony']
                )
                labels = " ".join(
                    f'<code style="font-size:10px;">{h}</code>'
                    for h in match['harmony']
                )
                st.markdown(
                    f'<div style="margin-top:4px;">🎨 ألوان التناسق:</div>'
                    f'<div style="margin:4px 0;">{swatches}</div>'
                    f'<div style="line-height:1.8;">{labels}</div>',
                    unsafe_allow_html=True,
                )

# ============= واجهة المستخدم =============

st.title("🎨 مطابقة الأفاتار مع البنرات")

# --- رفع البنرات أولاً ---
st.markdown("### 📤 1. اختر البنرات")

uploaded_banners = st.file_uploader(
    "اختر البنرات",
    type=["png", "jpg", "jpeg", "webp", "gif"],
    accept_multiple_files=True,
    label_visibility="collapsed",
    key="banners_uploader",
)

if uploaded_banners:
    if len(uploaded_banners) > MAX_BANNERS:
        st.warning(f"⚠️ الحد الأقصى {MAX_BANNERS} بنر — سيتم تحليل أول {MAX_BANNERS} فقط")
        uploaded_banners = uploaded_banners[:MAX_BANNERS]

    # عدد البنرات الجديدة (غير محللة)
    cache     = st.session_state.banners_cache
    new_count = sum(1 for f in uploaded_banners if f.name not in cache)

    if new_count > 0:
        st.info(f"📊 {len(uploaded_banners)} بنر — {new_count} جديد يحتاج تحليل، {len(uploaded_banners) - new_count} محلل مسبقاً")
    else:
        st.success(f"✅ {len(uploaded_banners)} بنر — كلهم محللون مسبقاً ⚡")

    if new_count > 0:
        if st.button("⚙️ حلل البنرات", use_container_width=True):
            st.session_state.gif_count  = 0
            st.session_state.gif_frames = 0
            progress_bar = st.progress(0)
            status_text  = st.empty()

            analyze_banners(uploaded_banners, progress_bar, status_text)

            progress_bar.empty()
            status_text.empty()

            if st.session_state.gif_count > 0:
                st.info(
                    f"ℹ️ تم العثور على {st.session_state.gif_count} GIF "
                    f"— تم تحليل {st.session_state.gif_frames} إطار إجمالاً"
                )

    # زر مسح الكاش
    if cache:
        if st.button("🗑️ مسح كاش البنرات", help="يجبر التطبيق على إعادة تحليل كل البنرات"):
            st.session_state.banners_cache = {}
            st.rerun()

st.markdown("---")

# --- رفع الأفاتار ---
st.markdown("### 📤 2. ارفع أفاتارك")

uploaded_avatar = st.file_uploader(
    "أضف الأفاتار",
    type=["png", "jpg", "jpeg", "webp", "jfif", "gif"],
    label_visibility="collapsed",
    key=f"avatar_{st.session_state.uploader_key}",
)

if uploaded_avatar:
    avatar, avatar_animated = handle_animated_image(Image.open(uploaded_avatar))
    avatar_palette          = get_palette(avatar)
    display_img             = avatar[0] if isinstance(avatar, list) else avatar

    col1, col2 = st.columns([1, 1])
    with col1:
        st.image(display_img, width=200)
        if avatar_animated:
            st.caption(f"🎞️ GIF — تم تحليل {len(avatar)} إطار")
    with col2:
        st.markdown("**🎨 ألوان الأفاتار:**")
        show_palette(avatar_palette)

    if st.button("🗑️ حذف الأفاتار", use_container_width=True):
        st.session_state.uploader_key += 1
        st.rerun()

    st.markdown("---")

    # --- ابدأ البحث ---
    cache = st.session_state.banners_cache
    ready = uploaded_banners and all(f.name in cache for f in uploaded_banners)

    if not uploaded_banners:
        st.warning("⚠️ أضف البنرات أولاً")
    elif not ready:
        st.warning("⚠️ اضغط 'حلل البنرات' أولاً")
    else:
        if st.button("🔍 ابدأ البحث", use_container_width=True, type="primary"):
            with st.spinner("جاري حساب التناسق..."):
                results = compute_scores(avatar_palette, uploaded_banners)
            show_results(results)
