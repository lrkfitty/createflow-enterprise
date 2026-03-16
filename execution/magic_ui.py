import streamlit as st

def inject_magic_css():
    """Injects the global CSS for Aurora Background and Magic UI primitives."""
    css = """
    <style>
        /* --- GLOBAL RESET & TYPOGRAPHY --- */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800&display=swap');
        
        :root {
            --bg-color: #000000; /* Pure Black */
            --text-color: #FFFFFF; /* Pure White */
            --card-bg: rgba(255, 255, 255, 0.05);
            --border-color: rgba(255, 255, 255, 0.15); /* Stronger Border */
            --primary-glow: conic-gradient(from 180deg at 50% 50%, #2a8af6 0deg, #a853ba 180deg, #e92a67 360deg);
        }
        
        html, body {
            font-family: 'Inter', sans-serif;
            color: var(--text-color) !important;
        }
        
        /* Force background to black for main container */
        .stApp {
            background-color: var(--bg-color) !important;
            background-image: 
                radial-gradient(circle at 15% 50%, rgba(76, 29, 149, 0.15), transparent 25%), 
                radial-gradient(circle at 85% 30%, rgba(14, 165, 233, 0.15), transparent 25%);
            background-attachment: fixed;
        }

        /* --- TEXT READABILITY --- */
        h1, h2, h3, h4, h5, h6, label, .stMarkdown p, .stCaption {
            color: #FFFFFF !important;
            text-shadow: 0 1px 2px rgba(0,0,0,0.5); /* separation from bg */
        }
        
        .stCaption {
            color: #A3A3A3 !important; /* Slightly dimmer for hierarchy */
        }

        /* --- GLASSMOPHISM CARD (The "Aura") --- */
        /* We target the container directly if possible, or use our wrapper */
        .glass-card {
            background: rgba(20, 20, 20, 0.6); /* Darker base */
            backdrop-filter: blur(8px) saturate(180%);
            -webkit-backdrop-filter: blur(8px) saturate(180%);
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 
                0 4px 6px -1px rgba(0, 0, 0, 0.1), 
                0 2px 4px -1px rgba(0, 0, 0, 0.06),
                inset 0 1px 0 rgba(255, 255, 255, 0.05);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 24px;
            transition: transform 0.3s ease, box-shadow 0.3s ease, border-color 0.3s ease;
        }
        
        .glass-card:hover {
            border-color: rgba(255, 255, 255, 0.3);
            box-shadow: 
                0 20px 25px -5px rgba(0, 0, 0, 0.2), 
                0 10px 10px -5px rgba(0, 0, 0, 0.1),
                0 0 15px rgba(56, 189, 248, 0.2); /* Blue Glow */
            transform: translateY(-2px);
        }

        /* --- MAGIC TEXT (Aurora Gradient) --- */
        @keyframes aurora-text {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        
        .magic-text {
            background: linear-gradient(
                90deg, 
                #FFFFFF 0%, 
                #38BDF8 25%, 
                #C084FC 50%, 
                #F472B6 75%, 
                #FFFFFF 100%
            );
            background-size: 200% auto;
            color: transparent !important;
            -webkit-text-fill-color: transparent !important;
            -webkit-background-clip: text;
            background-clip: text;
            font-weight: 900;
            letter-spacing: -0.03em;
        }
        
        /* --- SHINY BUTTONS (Aggressive Override) --- */
        div.stButton > button {
             background: linear-gradient(110deg, #1e293b 0%, #334155 25%, #475569 50%, #334155 75%, #1e293b 100%);
             color: #FFF !important;
             border: 1px solid rgba(255,255,255,0.2) !important;
             border-radius: 8px !important;
             font-weight: 600 !important;
             transition: all 0.3s ease !important;
             box-shadow: 0 1px 2px 0 rgba(0,0,0,0.05);
        }
        div.stButton > button:hover {
             color: #FFFFFF !important;
             border-color: #60A5FA !important; /* Blue highlight */
             transform: translateY(-2px);
             box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05), 0 0 20px rgba(96, 165, 250, 0.5); /* Blue Glow */
        }
        
        div.stButton > button[kind="primary"] {
             background: linear-gradient(135deg, #2563EB 0%, #7C3AED 100%) !important;
             border: none !important;
             box-shadow: 0 0 15px rgba(124, 58, 237, 0.4);
        }

        /* --- GRID & HOVER IMAGES --- */
        [data-testid="stImage"] img {
             border-radius: 12px;
             transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275), filter 0.3s ease;
             border: 1px solid rgba(255,255,255,0.1);
        }
        
        [data-testid="stImage"]:hover img {
             transform: scale(1.05);
             filter: brightness(1.1);
             border-color: rgba(255,255,255,0.5);
             box-shadow: 0 10px 40px -10px rgba(0,0,0,0.5);
             z-index: 10;
        }

        /* --- INPUT FIELDS (Seamless) --- */
        .stTextInput input, 
        .stSelectbox div[data-baseweb="select"] > div,
        .stMultiSelect div[data-baseweb="select"] > div,
        .stTextArea textarea {
            background-color: #0F172A !important; /* Opaque Dark Slate */
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
            color: #FFFFFF !important;
            caret-color: #38BDF8; /* Cyan Cursor */
            border-radius: 8px !important;
        }
        
        .stTextInput input:focus,
        .stTextArea textarea:focus {
            border-color: #38BDF8 !important; /* Cyan Focus */
            background-color: #1E293B !important; /* Slightly lighter opaque */
            box-shadow: 0 0 0 1px #38BDF8;
        }
        
        /* Sidebar Glass */
        [data-testid="stSidebar"] {
            background-color: rgba(0, 0, 0, 0.7) !important;
            backdrop-filter: blur(8px);
            border-right: 1px solid rgba(255,255,255,0.1);
        }
        
        /* --- DROPDOWNS & MENUS (NUCLEAR OPTION) --- */
        /* Force EVERYTHING inside the dropdown menu to be Black Bg / White Text */
        
        div[data-baseweb="popover"],
        div[data-baseweb="menu"],
        ul[data-baseweb="menu"] {
             background-color: #000000 !important;
             color: #FFFFFF !important;
             border: 1px solid #333 !important;
        }

        li[data-baseweb="option"] {
             background-color: #000000 !important;
             color: #E0E0E0 !important; /* Slightly off-white for contrast */
        }
        
        li[data-baseweb="option"] * {
             color: #E0E0E0 !important;
        }

        li[data-baseweb="option"]:hover,
        li[data-baseweb="option"][aria-selected="true"] {
             background-color: #222222 !important;
             color: #FFFFFF !important;
        }
        
        li[data-baseweb="option"]:hover *,
        li[data-baseweb="option"][aria-selected="true"] * {
             color: #FFFFFF !important;
        }

        /* The container box */
        .stSelectbox div[data-baseweb="select"] > div {
             background-color: #000000 !important;
             color: #FFFFFF !important;
             border: 1px solid #444 !important;
        }
        
        .stSelectbox div[data-baseweb="select"] > div * {
             color: #FFFFFF !important;
        }

        
        /* --- CIRCULAR PROGRESS --- */
        @keyframes spin {
             0% { transform: rotate(0deg); }
             100% { transform: rotate(360deg); }
        }
        
        .circular-loader {
             width: 48px;
             height: 48px;
             border-radius: 50%;
             background: conic-gradient(#FFFFFF 0%, transparent 40%);
             position: relative;
             animation: spin 1s linear infinite;
        }
        .circular-loader::before {
             content: "";
             position: absolute;
             inset: 4px;
             background: #000;
             border-radius: 50%;
        }
        
        /* --- HOVER DOWNLOAD BUTTON --- */
        .hover-btn-wrap {
            position: relative;
            display: inline-block;
            overflow: hidden;
            border-radius: 8px;
            cursor: pointer;
        }
        
        .hover-btn {
            display: flex;
            align-items: center;
            justify-content: center;
            background: #111;
            color: #FFF;
            border: 1px solid #333;
            padding: 8px 16px;
            font-weight: 500;
            transition: all 0.3s ease;
            width: 100%;
        }
        
        .hover-btn-wrap:hover .hover-btn {
             background: #FFF;
             color: #000;
             transform: translateY(-100%);
        }
        
        .hover-btn-reveal {
             position: absolute;
             inset: 0;
             display: flex;
             align-items: center;
             justify-content: center;
             background: #FFF;
             color: #000;
             transform: translateY(100%);
             transition: all 0.3s ease;
        }
        
        .hover-btn-wrap:hover .hover-btn-reveal {
             transform: translateY(0);
        }

        /* --- BRAND OVERLINE --- */
        .brand-overline {
            text-align: center;
            color: #94A3B8;
            font-size: 0.85rem;
            font-weight: 600;
            letter-spacing: 0.25em;
            text-transform: uppercase;
            margin-bottom: 0;
        }

        /* --- BOLD WIDGET LABELS (Global) --- */
        .stSelectbox label,
        .stMultiSelect label,
        .stTextInput label,
        .stTextArea label,
        .stSlider label,
        .stCheckbox label,
        .stRadio label,
        .stNumberInput label,
        .stFileUploader label,
        .stDateInput label,
        .stTimeInput label,
        .stColorPicker label,
        [data-testid="stWidgetLabel"] {
            color: #FFFFFF !important;
            font-weight: 600 !important;
            font-size: 0.9rem !important;
            text-shadow: 0 1px 2px rgba(0,0,0,0.5);
        }

        /* --- SLIDER STYLING --- */
        .stSlider [data-baseweb="slider"] [role="slider"] {
            background: #38BDF8 !important;
            border: 2px solid #FFFFFF !important;
            box-shadow: 0 0 10px rgba(56, 189, 248, 0.5);
        }
        .stSlider [data-baseweb="slider"] [data-testid="stTickBar"] > div {
            background: rgba(255,255,255,0.2) !important;
        }
        .stSlider div[data-baseweb="slider"] > div > div {
            background: linear-gradient(90deg, #2563EB, #38BDF8) !important;
        }
        .stSlider div[data-baseweb="slider"] > div {
            background: rgba(255,255,255,0.15) !important;
        }
        .stSlider [data-testid="stThumbValue"],
        .stSlider [data-testid="stTickBarMin"],
        .stSlider [data-testid="stTickBarMax"] {
            color: #FFFFFF !important;
            font-weight: 600 !important;
        }

        /* --- CHECKBOX & RADIO --- */
        .stCheckbox label span,
        .stCheckbox p,
        .stRadio label span,
        .stRadio p,
        .stRadio div[role="radiogroup"] label p {
            color: #FFFFFF !important;
            font-weight: 500 !important;
        }
        .stCheckbox [data-testid="stCheckbox"] > label > div[role="checkbox"] {
            border-color: rgba(255,255,255,0.4) !important;
            background: rgba(255,255,255,0.05) !important;
        }
        .stCheckbox [data-testid="stCheckbox"] > label > div[role="checkbox"][aria-checked="true"] {
            background: #2563EB !important;
            border-color: #2563EB !important;
        }

        /* --- EXPANDERS --- */
        .streamlit-expanderHeader,
        [data-testid="stExpander"] summary,
        [data-testid="stExpander"] summary span,
        [data-testid="stExpander"] summary p {
            color: #FFFFFF !important;
            font-weight: 700 !important;
            font-size: 1rem !important;
        }
        [data-testid="stExpander"] {
            background: rgba(15, 23, 42, 0.6) !important;
            border: 1px solid rgba(255,255,255,0.12) !important;
            border-radius: 12px !important;
        }
        [data-testid="stExpander"] details {
            border: none !important;
        }

        /* --- FORMS --- */
        [data-testid="stForm"] {
            background: rgba(15, 23, 42, 0.4) !important;
            border: 1px solid rgba(255,255,255,0.1) !important;
            border-radius: 12px !important;
            padding: 16px !important;
        }
        /* Form Submit Button */
        [data-testid="stForm"] button[kind="secondaryFormSubmit"],
        [data-testid="stForm"] button[type="submit"] {
            background: linear-gradient(110deg, #1e293b, #334155, #1e293b) !important;
            color: #FFFFFF !important;
            font-weight: 700 !important;
            border: 1px solid rgba(255,255,255,0.2) !important;
        }

        /* --- MULTISELECT TAGS --- */
        .stMultiSelect span[data-baseweb="tag"] {
            background: rgba(37, 99, 235, 0.3) !important;
            border: 1px solid rgba(56, 189, 248, 0.4) !important;
            border-radius: 6px !important;
        }
        .stMultiSelect span[data-baseweb="tag"] span {
            color: #FFFFFF !important;
            font-weight: 500 !important;
        }
        .stMultiSelect span[data-baseweb="tag"] span[role="presentation"] {
            color: #FFFFFF !important;
        }
        /* Multiselect container */
        .stMultiSelect div[data-baseweb="select"] > div {
            background-color: #0F172A !important;
            border: 1px solid rgba(255,255,255,0.2) !important;
            color: #FFFFFF !important;
        }

        /* --- DIVIDERS --- */
        hr, [data-testid="stDecoration"],
        .stDivider {
            border-color: rgba(255,255,255,0.1) !important;
            background-color: rgba(255,255,255,0.1) !important;
        }

        /* --- METRIC WIDGETS --- */
        [data-testid="stMetricValue"] {
            color: #FFFFFF !important;
            font-weight: 800 !important;
        }
        [data-testid="stMetricLabel"] {
            color: #94A3B8 !important;
            font-weight: 600 !important;
        }
        [data-testid="stMetricDelta"] svg {
            fill: currentColor !important;
        }

        /* --- ALERT BOXES (info, warning, success, error) --- */
        .stAlert, [data-testid="stAlert"] {
            border-radius: 10px !important;
            font-weight: 500 !important;
        }
        div[data-testid="stAlert"] p {
            font-weight: 500 !important;
        }

        /* --- CAPTION --- */
        .stCaption, [data-testid="stCaptionContainer"] p {
            color: #94A3B8 !important;
            font-weight: 500 !important;
        }

        /* --- NUMBER INPUT --- */
        .stNumberInput input {
            background-color: #0F172A !important;
            border: 1px solid rgba(255,255,255,0.2) !important;
            color: #FFFFFF !important;
            border-radius: 8px !important;
        }
        .stNumberInput button {
            color: #FFFFFF !important;
            border-color: rgba(255,255,255,0.2) !important;
        }

        /* --- FILE UPLOADER --- */
        [data-testid="stFileUploader"] section {
            background: rgba(15, 23, 42, 0.6) !important;
            border: 1px dashed rgba(255,255,255,0.2) !important;
            border-radius: 10px !important;
        }
        [data-testid="stFileUploader"] section small,
        [data-testid="stFileUploader"] section span {
            color: #94A3B8 !important;
        }

        /* --- TABS --- */
        .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
            font-size: 1.2rem !important;
            font-weight: 700 !important;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .stTabs [data-baseweb="tab-list"] button {
            color: #94A3B8 !important;
        }
        .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
             color: #FFFFFF !important;
             border-bottom-color: #38BDF8 !important;
        }
        .stTabs [data-baseweb="tab-list"] button:hover {
            color: #FFFFFF !important;
        }
        .stTabs [data-baseweb="tab-list"] {
            border-bottom: 1px solid rgba(255,255,255,0.1) !important;
        }

        /* --- TOAST --- */
        [data-testid="stToast"] {
            background: rgba(15, 23, 42, 0.95) !important;
            border: 1px solid rgba(255,255,255,0.15) !important;
            color: #FFFFFF !important;
            backdrop-filter: blur(10px);
        }
        [data-testid="stToast"] p {
            color: #FFFFFF !important;
            font-weight: 500 !important;
        }

        /* --- MARKDOWN BOLD TEXT (inside widgets) --- */
        .stMarkdown strong, .stMarkdown b {
            color: #FFFFFF !important;
            font-weight: 700 !important;
        }

        /* --- SELECTBOX PLACEHOLDER TEXT --- */
        .stSelectbox [data-baseweb="select"] input::placeholder,
        .stMultiSelect [data-baseweb="select"] input::placeholder {
            color: #64748B !important;
        }

        /* --- DOWNLOAD BUTTON --- */
        .stDownloadButton button {
            background: linear-gradient(110deg, #1e293b, #334155, #1e293b) !important;
            color: #FFFFFF !important;
            font-weight: 600 !important;
            border: 1px solid rgba(255,255,255,0.2) !important;
        }
        .stDownloadButton button:hover {
            border-color: #38BDF8 !important;
            box-shadow: 0 0 15px rgba(56, 189, 248, 0.3);
        }

        /* --- ICON GRID SELECTOR --- */
        .icon-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
            gap: 8px;
            margin: 8px 0;
        }
        .icon-card {
            position: relative;
            border-radius: 10px;
            overflow: hidden;
            border: 2px solid rgba(255,255,255,0.1);
            cursor: pointer;
            transition: all 0.3s ease;
            aspect-ratio: 1;
            background: rgba(15, 23, 42, 0.6);
        }
        .icon-card:hover {
            border-color: rgba(56, 189, 248, 0.5);
            transform: scale(1.05);
            box-shadow: 0 0 15px rgba(56, 189, 248, 0.3);
        }
        .icon-card.selected {
            border-color: #38BDF8;
            box-shadow: 0 0 20px rgba(56, 189, 248, 0.5), 0 0 40px rgba(56, 189, 248, 0.2);
            transform: scale(1.03);
        }
        .icon-card img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        .icon-card-label {
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            background: linear-gradient(transparent, rgba(0,0,0,0.85));
            color: #FFFFFF;
            font-size: 0.65rem;
            font-weight: 600;
            padding: 16px 6px 5px 6px;
            text-align: center;
            line-height: 1.2;
        }
        .icon-card-text-only {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            height: 100%;
            color: #CBD5E1;
            font-size: 0.7rem;
            font-weight: 600;
            text-align: center;
            padding: 6px;
            background: rgba(15, 23, 42, 0.8);
        }

    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

def magic_text(text, type="h1"):
    """Renders text with the Aurora Gradient animation."""
    st.markdown(f"<{type} class='magic-text'>{text}</{type}>", unsafe_allow_html=True)

def card_begin():
    """Starts a Glassmorphism Card Wrapper."""
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)

def card_end():
    st.markdown('</div>', unsafe_allow_html=True)

def circular_progress():
    st.markdown('<div class="circular-loader"></div>', unsafe_allow_html=True)

def hover_button(label="Download", key=None):
    """(Visual Only) Renders the CSS for the hover button. 
       For actual functionality, we still need st.button or st.download_button overlaid or handled via callbacks.
       Since Streamlit doesn't allow custom HTML to trigger Python callbacks easily, 
       we will use this for visual flair on links or static actions, 
       or wrap a transparent download button on top if possible (tricky).
       
       For now, returning HTML string."""
    return f"""
    <div class="hover-btn-wrap">
        <div class="hover-btn">{label}</div>
        <div class="hover-btn-reveal">⬇</div>
    </div>
    """


def icon_grid_selector(label, options, icons_dir, key, cols_per_row=4):
    """Visual grid selector with photorealistic thumbnails.
    
    Args:
        label: Section header label
        options: List of option strings (e.g. ["Eye Level (Neutral)", "Low Angle (Heroic/Power)"])  
        icons_dir: Path to directory containing icon images (e.g. "assets/ui_icons/camera_angles")
        key: Session state key for storing selection
        cols_per_row: Number of columns in the grid
    
    Returns:
        Selected option string (or "Auto" if none selected)
    """
    import os
    import base64
    
    st.markdown(f"**{label}**")
    
    # Initialize session state
    state_key = f"icon_grid_{key}"
    if state_key not in st.session_state:
        st.session_state[state_key] = "Auto"
    
    # Auto option
    if st.button("✨ Auto", key=f"{key}_auto", 
                 type="primary" if st.session_state[state_key] == "Auto" else "secondary",
                 use_container_width=True):
        st.session_state[state_key] = "Auto"
        st.rerun()
    
    # Build grid
    abs_icons_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), icons_dir)
    
    rows = [options[i:i+cols_per_row] for i in range(0, len(options), cols_per_row)]
    
    for row_opts in rows:
        cols = st.columns(cols_per_row)
        for idx, opt in enumerate(row_opts):
            with cols[idx]:
                is_selected = st.session_state[state_key] == opt
                
                # Find icon file
                safe_name = opt.lower()
                for char in "()/ &'":
                    safe_name = safe_name.replace(char, "_")
                safe_name = safe_name.strip("_")
                while "__" in safe_name:
                    safe_name = safe_name.replace("__", "_")
                
                icon_path = None
                for ext in ['.png', '.jpg', '.jpeg', '.webp']:
                    candidate = os.path.join(abs_icons_dir, safe_name + ext)
                    if os.path.exists(candidate):
                        icon_path = candidate
                        break
                
                # Render card
                if icon_path:
                    # Image card with overlay label
                    with open(icon_path, "rb") as f:
                        img_data = base64.b64encode(f.read()).decode()
                    
                    ext_type = os.path.splitext(icon_path)[1].lstrip('.')
                    if ext_type == 'jpg': ext_type = 'jpeg'
                    
                    border_style = "border: 2px solid #38BDF8; box-shadow: 0 0 15px rgba(56,189,248,0.5);" if is_selected else "border: 2px solid rgba(255,255,255,0.1);"
                    
                    # Short label (remove parenthetical) 
                    short_label = opt.split("(")[0].strip() if "(" in opt else opt
                    
                    st.markdown(f"""
                    <div style="position:relative; border-radius:10px; overflow:hidden; {border_style} 
                                transition: all 0.3s ease; aspect-ratio:1; cursor:pointer;">
                        <img src="data:image/{ext_type};base64,{img_data}" 
                             style="width:100%; height:100%; object-fit:cover;">
                        <div style="position:absolute; bottom:0; left:0; right:0; 
                                    background: linear-gradient(transparent, rgba(0,0,0,0.85));
                                    color:#FFF; font-size:0.65rem; font-weight:600; 
                                    padding:16px 4px 4px 4px; text-align:center; line-height:1.2;">
                            {short_label}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    # Text-only fallback card
                    border_style = "border: 2px solid #38BDF8; box-shadow: 0 0 15px rgba(56,189,248,0.5); background: rgba(37,99,235,0.2);" if is_selected else "border: 2px solid rgba(255,255,255,0.1); background: rgba(15,23,42,0.8);"
                    short_label = opt.split("(")[0].strip() if "(" in opt else opt
                    
                    st.markdown(f"""
                    <div style="display:flex; align-items:center; justify-content:center;
                                border-radius:10px; {border_style} aspect-ratio:1; 
                                transition: all 0.3s ease; cursor:pointer;">
                        <span style="color:#CBD5E1; font-size:0.7rem; font-weight:600; 
                                     text-align:center; padding:6px;">{short_label}</span>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Actual clickable button (small, below card)
                btn_label = "●" if is_selected else "○"
                if st.button(btn_label, key=f"{key}_{idx}_{opt[:15]}", use_container_width=True):
                    st.session_state[state_key] = opt
                    st.rerun()
    
    selected = st.session_state[state_key]
    st.caption(f"Selected: **{selected}**")
    return selected


def thumbnail_carousel(label, items_dict, state_key, thumb_cols=3, show_label=True):
    """
    Paginated photo-gallery carousel — shows `thumb_cols` items at a time
    with ◀ / ▶ navigation. Uses st.image() for local files (no base64 crash).

    Args:
        label:       Section header
        items_dict:  Dict {display_name: value}  value can be a path string,
                     a dict with 'default_img'/'name', or None.
        state_key:   Session-state key storing the currently selected name.
        thumb_cols:  Items visible per page (default 3).
        show_label:  Whether to render the section header.

    Returns:
        Currently selected key (display name) or None.
    """
    import os

    if show_label:
        st.markdown(f"**{label}**")

    if not items_dict:
        st.caption("No items available.")
        return st.session_state.get(state_key)

    items   = list(items_dict.items())
    total   = len(items)
    page_key = f"_tc_page_{state_key}"

    if page_key not in st.session_state:
        st.session_state[page_key] = 0

    # Keep page in bounds
    max_page = max(0, (total - 1) // thumb_cols)
    if st.session_state[page_key] > max_page:
        st.session_state[page_key] = max_page

    page     = st.session_state[page_key]
    start    = page * thumb_cols
    end      = min(start + thumb_cols, total)
    page_items = items[start:end]

    # ── Navigation bar ────────────────────────────────────────────────────────
    nav_l, nav_mid, nav_r = st.columns([1, 6, 1])
    with nav_l:
        if st.button("◀", key=f"_tc_prev_{state_key}", disabled=(page == 0),
                     use_container_width=True):
            st.session_state[page_key] -= 1
            st.rerun()
    with nav_mid:
        st.caption(f"{start + 1}–{end} of {total}   |   {'✅ ' + str(st.session_state.get(state_key, '')) if st.session_state.get(state_key) else 'None selected'}")
    with nav_r:
        if st.button("▶", key=f"_tc_next_{state_key}", disabled=(page >= max_page),
                     use_container_width=True):
            st.session_state[page_key] += 1
            st.rerun()

    # ── Gallery row ───────────────────────────────────────────────────────────
    current = st.session_state.get(state_key)
    cols    = st.columns(thumb_cols)

    for col_idx, (name, val) in enumerate(page_items):
        with cols[col_idx]:
            is_selected  = (current == name)

            # Resolve metadata
            img_path     = None
            is_celeb     = False
            display_name = name

            if isinstance(val, dict):
                display_name = val.get("name", name)
                img_path     = val.get("default_img")
                is_celeb     = val.get("is_celebrity", False)
            elif isinstance(val, str) and val:
                img_path = val

            star  = "⭐ " if is_celeb else ""
            short = display_name.replace("⭐ ", "")
            short = (short[:16] + "…") if len(short) > 16 else short

            # Selected border/glow via container markdown
            border = "#38BDF8" if is_selected else "rgba(255,255,255,0.1)"
            shadow = "0 0 16px rgba(56,189,248,0.5)" if is_selected else "none"
            st.markdown(
                f'<div style="border-radius:12px;border:2px solid {border};'
                f'box-shadow:{shadow};padding:4px;margin-bottom:4px;transition:all 0.2s;">',
                unsafe_allow_html=True
            )

            # Image — use st.image() for local, <img> for URLs (no base64)
            if img_path:
                try:
                    if isinstance(img_path, str) and img_path.startswith("http"):
                        st.markdown(
                            f'<img src="{img_path}" style="width:100%;border-radius:8px;'
                            f'aspect-ratio:1;object-fit:cover;" loading="lazy">',
                            unsafe_allow_html=True
                        )
                    elif os.path.exists(str(img_path)):
                        st.image(img_path, use_container_width=True)
                except Exception:
                    pass  # No image fallback — just show name + button

            st.markdown("</div>", unsafe_allow_html=True)

            # Name label
            st.caption(f"{star}{short}")

            # Select button — state update only, no manual rerun
            btn_label = "✔ Selected" if is_selected else "Select"
            btn_type  = "primary" if is_selected else "secondary"
            if st.button(btn_label, key=f"tc_{state_key}_{start}_{col_idx}",
                         use_container_width=True, type=btn_type):
                st.session_state[state_key] = name
                st.rerun()

    return st.session_state.get(state_key)



def fidelity_mode_selector(state_key="fidelity_mode"):
    """
    Renders the Content Fidelity selector row.
    Returns (selected_label, prompt_modifier_string)
    """
    modes = {
        "🎬 Cinematic": ("ultra high fidelity, professional cinematography, perfect studio lighting, flawless editorial retouching, luxury production value, sharp focus, masterful color grade",
                          "Perfect lighting, flawless retouching, luxury polish"),
        "📱 UGC / Raw": ("authentic user-generated content style, slightly handheld, natural imperfections, no retouching, raw and real, casual framing, phone camera feel, genuine candid energy, unfiltered, lived-in",
                          "Handheld, no retouching, real imperfections"),
        "🌟 Influencer": ("ring light glow, clean polished background, Instagram-ready, soft natural lighting, effortlessly styled, beauty-tuned but approachable, socially optimized framing",
                           "Ring light glow, polished but approachable"),
        "🏃 Lifestyle": ("candid motion energy, authentic real-life moments, slight motion blur, dynamic angles, documentary feel, unposed and genuine, natural environment",
                          "Candid energy, authentic moments, doc feel"),
        "🎞️ Editorial": ("fashion editorial precision, dramatic studio shadows, avant-garde composition, high contrast, magazine-quality retouching, artistic direction, high concept",
                           "Dramatic studio, magazine-quality, high concept"),
    }

    if state_key not in st.session_state:
        st.session_state[state_key] = "🎬 Cinematic"

    st.markdown("**🎨 Content Look & Fidelity**")

    labels = list(modes.keys())
    cols = st.columns(len(labels))
    for i, lbl in enumerate(labels):
        modifier, desc = modes[lbl]
        with cols[i]:
            is_active = st.session_state[state_key] == lbl
            if st.button(lbl, key=f"fid_{state_key}_{i}", use_container_width=True,
                         type="primary" if is_active else "secondary", help=desc):
                st.session_state[state_key] = lbl
                st.rerun()

    selected_label = st.session_state[state_key]
    modifier, desc = modes[selected_label]
    st.caption(f"*{desc}*")
    return selected_label, modifier
