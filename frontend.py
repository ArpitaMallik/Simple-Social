import streamlit as st
import requests
import base64
import urllib.parse
from datetime import datetime

API_BASE = "http://localhost:8000"

st.set_page_config(page_title="Simple Social", page_icon="📸", layout="wide")

# ---------- Session state ----------
if "token" not in st.session_state:
    st.session_state.token = None
if "user" not in st.session_state:
    st.session_state.user = None


def get_headers():
    if st.session_state.token:
        return {"Authorization": f"Bearer {st.session_state.token}"}
    return {}


# ---------- Small helpers ----------
def fmt_date(iso_str: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y")
    except Exception:
        return iso_str[:10]


def encode_text_for_overlay(text):
    if not text:
        return ""
    base64_text = base64.b64encode(text.encode("utf-8")).decode("utf-8")
    return urllib.parse.quote(base64_text)


def create_transformed_url(original_url, transformation_params, caption=None):
    if caption:
        encoded_caption = encode_text_for_overlay(caption)
        # bottom overlay with semi-transparent background
        text_overlay = (
            f"l-text,ie-{encoded_caption},ly-N20,lx-20,fs-100,co-white,"
            f"bg-000000A0,l-end"
        )
        transformation_params = text_overlay

    if not transformation_params:
        return original_url

    parts = original_url.split("/")
    base_url = "/".join(parts[:4])
    file_path = "/".join(parts[4:])
    return f"{base_url}/tr:{transformation_params}/{file_path}"


# ---------- UI ----------
def login_page():
    st.markdown("## 📸 Simple Social")
    st.caption("Log in to post and see your feed. Minimal vibes, maximum function.")

    # Centered-ish card
    left, mid, right = st.columns([1, 2, 1])
    with mid:
        with st.container(border=True):
            tab_login, tab_signup = st.tabs(["Login", "Sign up"])

            with tab_login:
                email = st.text_input("Email", key="login_email", placeholder="you@example.com")
                password = st.text_input("Password", type="password", key="login_pw")

                if st.button("Login", type="primary", use_container_width=True):
                    if not email or not password:
                        st.warning("Please enter both email and password.")
                        return

                    with st.spinner("Signing you in..."):
                        login_data = {"username": email, "password": password}
                        response = requests.post(
                            "http://localhost:8000/auth/jwt/login",
                            data=login_data,
                        )

                    if response.status_code == 200:
                        token_data = response.json()
                        st.session_state.token = token_data["access_token"]

                        user_response = requests.get(
                            "http://localhost:8000/users/me",
                            headers=get_headers(),
                        )
                        if user_response.status_code == 200:
                            st.session_state.user = user_response.json()
                            # st.success("Logged in successfully!")
                            st.success("Welcome back.")
                            st.rerun()
                        else:
                            st.error("Login succeeded, but failed to fetch user profile.")
                    else:
                        st.error("Invalid email or password.")


            with tab_signup:
                email = st.text_input("Email", key="signup_email", placeholder="you@example.com")
                password = st.text_input("Password", type="password", key="signup_pw",
                                         help="Use a real password. Even for demos. Future you will thank you.")

                can_submit = bool(email and password)
                if st.button("Create account", use_container_width=True):
                    if not email or not password:
                        st.warning("Please enter both email and password.")
                        return

                    with st.spinner("Creating your account..."):
                        signup_data = {"email": email, "password": password}
                        response = requests.post("http://localhost:8000/auth/register", json=signup_data)

                    if response.status_code in (200, 201):
                        st.success("Account created! Go to the Login tab to sign in.")
                    else:
                        try:
                            detail = response.json().get("detail", "Registration failed")
                        except Exception:
                            detail = "Registration failed"
                        st.error(f"Registration failed: {detail}")



def upload_page():
    st.markdown("## 📤 Create a post")
    st.caption("Share an image or video. Keep it classy. Or don’t. I’m not your editor.")

    with st.container(border=True):
        uploaded_file = st.file_uploader(
            "Media",
            type=["png", "jpg", "jpeg", "mp4", "avi", "mov", "mkv", "webm"],
            help="Images and common video formats supported.",
        )
        caption = st.text_area("Caption", placeholder="What's on your mind?", height=90)

        col1, col2 = st.columns([1, 3])
        with col1:
            share = st.button("Share", type="primary", use_container_width=True, disabled=uploaded_file is None)
        with col2:
            st.caption("Tip: captions show as an overlay on images in the feed.")

    if uploaded_file and share:
        with st.spinner("Uploading..."):
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
            data = {"caption": caption}
            resp = requests.post(f"{API_BASE}/upload", files=files, data=data, headers=get_headers())

        if resp.status_code == 200:
            st.success("Posted.")
            st.rerun()
        else:
            try:
                detail = resp.json().get("detail", "Upload failed")
            except Exception:
                detail = "Upload failed"
            st.error(detail)


def feed_page():
    st.markdown("## 🏠 Feed")
    st.caption("Latest posts first.")

    resp = requests.get(f"{API_BASE}/feed", headers=get_headers())
    if resp.status_code != 200:
        st.error("Failed to load feed.")
        return

    posts = resp.json().get("posts", [])
    if not posts:
        st.info("No posts yet. Go be the first.")
        return

    # Slightly tighter layout
    for post in posts:
        with st.container(border=True):
            top = st.columns([6, 1])
            with top[0]:
                email = post.get("email", "unknown")
                created = fmt_date(post.get("created_at", ""))
                st.markdown(f"**{email}** · {created}")
            with top[1]:
                if post.get("is_owner", False):
                    if st.button("🗑️", key=f"delete_{post['id']}", help="Delete post", use_container_width=True):
                        d = requests.delete(f"{API_BASE}/posts/{post['id']}", headers=get_headers())
                        if d.status_code == 200:
                            st.success("Deleted.")
                            st.rerun()
                        else:
                            st.error("Delete failed.")

            caption = post.get("caption", "").strip()

            # Media
            if post.get("file_type") == "image":
                uniform_url = create_transformed_url(post["url"], "", caption)
                st.image(uniform_url, use_container_width=False, width=420)
            else:
                # simple uniform-ish transform for videos
                uniform_video_url = create_transformed_url(post["url"], "w-700,h-380,cm-pad_resize,bg-blurred")
                st.video(uniform_video_url)

            if caption and post.get("file_type") != "image":
                st.caption(caption)


# ---------- Main ----------
if st.session_state.user is None:
    login_page()
else:
    st.sidebar.markdown("### 👋 Signed in")
    st.sidebar.write(st.session_state.user.get("email", ""))

    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.user = None
        st.session_state.token = None
        st.rerun()

    st.sidebar.markdown("---")
    page = st.sidebar.radio("Navigate", ["🏠 Feed", "📸 Upload"], label_visibility="collapsed")

    if page == "🏠 Feed":
        feed_page()
    else:
        upload_page()
