import streamlit as st
from PIL import Image
import numpy as np
from sklearn.cluster import KMeans
import os
from skimage import filters
from skimage.color import rgb2hsv
import warnings
from datetime import datetime
import time
from coloraide import Color

warnings.filterwarnings('ignore')

st.set_page_config(layout="wide", page_title="مطابقة الأفاتار مع البنرات", page_icon="🎨")

if 'gif_warning_shown' not in st.session_state:
    st.session_state.gif_warning_shown = False
if 'gif_count' not in st.session_state:
    st.session_state.gif_count = 0

def handle_animated_image(image, image_type="الصورة"):
    try:
        if hasattr(image, "is_animated") and image.is_animated:
            st.session_state.gif_count += 1
            image.seek(0)
        return image.convert("RGB")
    except:
        return image.convert("RGB")

def analyze_image_quality(image):
    try:
        img = np.array(image.convert("L"))
        laplacian_var = np.var(filters.laplace(img))
        sharpness_score = min(100, laplacian_var / 50)
        contrast = np.std(img)
        contrast_score = min(100, contrast / 2)
        return (sharpness_score + contrast_score) / 2
    except:
        return 50

def get_weighted_palette(image, n_colors=5):
    try:
        image = image.convert("RGB")
        img = image.resize((200, 200))
        pixels = np.array(img).reshape(-1, 3)
        hsv = rgb2hsv(pixels / 255.0)
        weights = 1 + (hsv[:, 1] * 2) + (hsv[:, 2] * 1.5)

        kmeans = KMeans(n_clusters=min(n_colors, len(pixels)), n_init=10, random_state=42)
        kmeans.fit(pixels, sample_weight=weights)

        colors = kmeans.cluster_centers_.astype(int)
        labels = kmeans.labels_

        weighted_counts = {}
        for i, label in enumerate(labels):
            weighted_counts[label] = weighted_counts.get(label, 0) + weights[i]

        total_weight = sum(weighted_counts.values())
        percentages = [weighted_counts[i] / total_weight for i in range(len(colors))]

        palette = list(zip(colors, percentages))
        palette.sort(key=lambda x: x[1], reverse=True)
        return palette[:5]
    except:
        return get_palette_basic(image, 5)

def get_palette_basic(image, n_colors=5):
    image = image.convert("RGB")
    img = image.resize((150, 150))
    pixels = np.array(img).reshape(-1, 3)
    kmeans = KMeans(n_clusters=n_colors, n_init=10, random_state=42)
    kmeans.fit(pixels)
    colors = kmeans.cluster_centers_.astype(int)
    labels = kmeans.labels_
    counts = np.bincount(labels)
    percentages = counts / counts.sum()
    palette = list(zip(colors, percentages))
    palette.sort(key=lambda x: x[1], reverse=True)
    return palette

def rgb_to_hex(color):
    return '#%02x%02x%02x' % tuple(color)

def color_distance(c1, c2):
    c1_arr = np.array(c1) if isinstance(c1, tuple) else c1
    c2_arr = np.array(c2) if isinstance(c2, tuple) else c2
    return np.linalg.norm(c1_arr - c2_arr)

def get_color_temperature(color):
    return (color[0] - color[2]) / 255

def get_color_vibrance(color):
    r, g, b = color[0] / 255, color[1] / 255, color[2] / 255
    max_rgb = max(r, g, b)
    min_rgb = min(r, g, b)
    if max_rgb == 0:
        return 0
    return (max_rgb - min_rgb) / max_rgb

def enhanced_palette_match(palette1, palette2):
    total_score = 0
    total_weight = 0

    for a_color, a_weight in palette1:
        best_score = 0
        for b_color, b_weight in palette2:
            color_dist = color_distance(a_color, b_color)
            color_score = max(0, 100 - color_dist / 3)
            temp_a = get_color_temperature(a_color)
            temp_b = get_color_temperature(b_color)
            temp_match = 100 - (abs(temp_a - temp_b) * 50)
            vibrance_a = get_color_vibrance(a_color)
            vibrance_b = get_color_vibrance(b_color)
            vibrance_match = 100 - (abs(vibrance_a - vibrance_b) * 60)
            weight_match = min(a_weight, b_weight) / max(a_weight, b_weight) if max(a_weight, b_weight) > 0 else 0
            final_score = (color_score * 0.4 + temp_match * 0.25 + vibrance_match * 0.2 + weight_match * 0.15)
            best_score = max(best_score, final_score)
        total_score += best_score * a_weight
        total_weight += a_weight

    return total_score / total_weight if total_weight > 0 else 0

def find_banners_for_avatar(avatar_palette, banners_folder):
    matches = []
    supported = ('.png', '.jpg', '.jpeg', '.webp', '.gif')

    if not os.path.exists(banners_folder):
        return []

    files = [f for f in os.listdir(banners_folder) if f.lower().endswith(supported)]

    st.session_state.gif_count = 0

    for file in files:
        path = os.path.join(banners_folder, file)
        try:
            banner = Image.open(path)
            banner = handle_animated_image(banner, file)
            banner_palette = get_weighted_palette(banner)

            if banner_palette:
                score = enhanced_palette_match(avatar_palette, banner_palette)

                matches.append({
                    'path': path,
                    'score': score,
                    'filename': file,
                    'image': banner
                })
        except:
            continue

    matches.sort(key=lambda x: x['score'], reverse=True)
    return matches

def save_combo(avatar, banner, banners_folder, avatar_filename):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    avatar_name = os.path.splitext(avatar_filename)[0]
    banner_name = os.path.splitext(os.path.basename(banner.filename))[0] if hasattr(banner, 'filename') else "banner"
    folder_name = f"{avatar_name}_{banner_name}_{timestamp}"
    output_folder = os.path.join(banners_folder, folder_name)

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    avatar.save(os.path.join(output_folder, "avatar.png"))
    banner.save(os.path.join(output_folder, "banner.png"))

    return output_folder

st.title("🎨 مطابقة الأفاتار مع البنرات")

st.markdown("### 📤 ارفع أفاتارك")

uploaded_avatar = st.file_uploader(
    "أضف الأفاتار",
    type=["png", "jpg", "jpeg", "webp", "jfif"],
    help="اختر صورة الأفاتار من جهازك",
    label_visibility="collapsed"
)

if uploaded_avatar:
    st.session_state.gif_warning_shown = False
    
    avatar = Image.open(uploaded_avatar)
    avatar = handle_animated_image(avatar, "الأفاتار")
    avatar_palette = get_weighted_palette(avatar)

    col1, col2 = st.columns([1, 1])
    with col1:
        st.image(avatar, width=200)
    with col2:
        st.markdown("**🎨 ألوان الأفاتار:**")
        for color, pct in avatar_palette:
            st.markdown(f"""
                <div style="background:{rgb_to_hex(color)}; height:30px; border-radius:5px; margin-bottom:5px;"></div>
                {rgb_to_hex(color)} — {pct * 100:.1f}%
            """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 📁 مسار مجلد البنرات")

    banners_folder = st.text_input(
        "مسار مجلد البنرات",
        placeholder="مثال: C:/Users/اسم المستخدم/Pictures/banners",
        label_visibility="collapsed"
    )

    if banners_folder:
        with st.spinner("جاري البحث عن بنرات مناسبة..."):
            time.sleep(0.5)
            banner_matches = find_banners_for_avatar(avatar_palette, banners_folder)
        
        if st.session_state.gif_count > 0:
            st.info(f"ℹ️ تم العثور على {st.session_state.gif_count} صورة متحركة (GIF) - تم استخدام أول إطار فقط للمقارنة")

        if banner_matches:
            st.markdown("---")
            st.markdown("### 🏆 أفضل البنرات المتناسقة")

            cols = st.columns(3)
            for i, match in enumerate(banner_matches[:6]):
                with cols[i % 3]:
                    st.image(match['image'], use_container_width=True)
                    st.caption(f"📄 {match['filename']}")
                    st.caption(f"⭐ التناسق: {match['score']:.1f}%")

                    if st.button(f"💾 حفظ", key=f"save_{i}"):
                        folder = save_combo(
                            avatar,
                            match['image'],
                            banners_folder,
                            uploaded_avatar.name
                        )
                        st.success(f"✅ تم الحفظ في:\n`{folder}`")
        else:
            st.error("❌ لم يتم العثور على بنرات في المسار المحدد")
