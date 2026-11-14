
import streamlit as st


def apply_theme():
    st.markdown(
        """
        <style>
        @import url(
          'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap'
        );

        :root {
            color-scheme: dark;
        }

        .stApp {
            background: #0B1220;
            color: #E5E7EB;
            font-family: 'Inter', sans-serif;
        }

        [data-testid="stHeader"] {
            background: transparent;
        }

        [data-testid="stSidebar"] {
            background: #111C2E;
            border-right: 1px solid #263449;
        }

        [data-testid="stSidebar"] * {
            color: #E5E7EB;
        }

        [data-testid="stSidebar"] [data-testid="stRadio"] label {
            padding: 5px 0;
        }

        .block-container {
            max-width: 1550px;
            padding-top: 1.6rem;
            padding-bottom: 3rem;
        }

        h1, h2, h3, h4 {
            color: #F8FAFC !important;
            font-weight: 700 !important;
            letter-spacing: -0.35px;
        }

        h2 {
            margin-top: 0.6rem;
        }

        p, li {
            color: #CBD5E1;
        }

        [data-testid="stCaptionContainer"] {
            color: #94A3B8;
        }

        hr {
            border-color: #263449;
        }

        /* Hero styles retained for optional use. */

        .hero {
            position: relative;
            overflow: hidden;
            padding: 2.2rem;
            border: 1px solid #34445C;
            border-radius: 20px;
            background: linear-gradient(
                120deg,
                #17243A,
                #202D42,
                #182238
            );
            background-size: 200% 200%;
            animation: gradientMove 12s ease infinite,
                       fadeUp 0.8s ease both;
            margin-bottom: 1.5rem;
        }

        .hero:after {
            content: "";
            position: absolute;
            width: 240px;
            height: 240px;
            right: -70px;
            top: -100px;
            border-radius: 50%;
            background: #F59E0B;
            opacity: 0.10;
            filter: blur(65px);
            pointer-events: none;
        }

        .hero-label {
            color: #FBBF24;
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 3px;
        }

        .hero-title {
            color: #F8FAFC;
            font-size: 2.5rem;
            font-weight: 800;
            margin: 0.6rem 0 0.3rem 0;
        }

        .hero-subtitle {
            color: #A9B8CC;
            font-size: 0.95rem;
        }

        /* Metric cards */

        div[data-testid="stMetric"] {
            background: #17243A;
            border: 1px solid #30415A;
            border-radius: 14px;
            padding: 16px;
            transition: border-color 0.2s ease;
            animation: fadeUp 0.5s ease both;
        }

        div[data-testid="stMetric"]:hover {
            border-color: #D97706;
        }

        div[data-testid="stMetricLabel"] {
            color: #A9B8CC;
        }

        div[data-testid="stMetricValue"] {
            color: #F8FAFC;
            font-weight: 700;
        }

        /* Charts and maps */

        [data-testid="stPlotlyChart"],
        [data-testid="stPydeckDeckGlJsonChart"] {
            background: #111C2E;
            border: 1px solid #263449;
            border-radius: 14px;
            padding: 8px;
            overflow: hidden;
        }

        /* Tables */

        div[data-testid="stDataFrame"] {
            border: 1px solid #30415A;
            border-radius: 12px;
            overflow: hidden;
        }

        /* Inputs */

        div[data-baseweb="input"] > div,
        div[data-baseweb="select"] > div,
        div[data-baseweb="textarea"] {
            background: #111C2E;
            border-color: #34445C;
            border-radius: 9px;
        }

        div[data-baseweb="input"] input,
        div[data-baseweb="textarea"] textarea {
            color: #E5E7EB;
        }

        div[data-baseweb="select"] span {
            color: #E5E7EB;
        }

        /* Buttons */

        .stButton button,
        .stDownloadButton button {
            border-radius: 9px;
            border: 1px solid #D97706;
            background: #B45309;
            color: white;
            font-weight: 600;
            transition: all 0.2s ease;
        }

        .stButton button:hover,
        .stDownloadButton button:hover {
            background: #D97706;
            border-color: #FBBF24;
            color: white;
        }

        /* Expanders and tabs */

        [data-testid="stExpander"] {
            background: #111C2E;
            border: 1px solid #30415A;
            border-radius: 12px;
        }

        [data-testid="stTabs"] button {
            color: #A9B8CC;
        }

        [data-testid="stTabs"] button[aria-selected="true"] {
            color: #FBBF24;
        }

        /* Intelligence panel */

        .st-key-intelligence_panel [data-testid="stMetric"] {
            padding: 10px 12px;
            min-height: 85px;
        }

        .st-key-intelligence_panel [data-testid="stMetricValue"],
        .st-key-intelligence_panel [data-testid="stMetricValue"] div {
            font-size: 1.25rem !important;
            line-height: 1.3 !important;
        }

        .st-key-intelligence_panel [data-testid="stMetricLabel"] {
            font-size: 0.72rem !important;
        }

        .st-key-intelligence_panel h3 {
            font-size: 1.05rem !important;
        }

        /* Animations */

        @keyframes fadeUp {
            from {
                opacity: 0;
                transform: translateY(10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @keyframes gradientMove {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }

        /* Responsive layout */

        @media (max-width: 900px) {
            .block-container {
                padding-top: 1rem;
                padding-left: 1rem;
                padding-right: 1rem;
            }

            .hero {
                padding: 1.4rem;
            }

            .hero-title {
                font-size: 1.8rem;
            }
        }

        @media (max-width: 600px) {
            .block-container {
                padding-left: 0.7rem;
                padding-right: 0.7rem;
            }

            div[data-testid="stMetric"] {
                padding: 10px;
            }

            .hero-title {
                font-size: 1.5rem;
            }
        }

        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after {
                animation: none !important;
                transition: none !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero():
    st.markdown(
        """
        <div class="hero">
            <div class="hero-label">
                SATELLITE EARTH OBSERVATION
            </div>
            <div class="hero-title">
                Fire Intelligence Monitor
            </div>
            <div class="hero-subtitle">
                Punjab–Haryana | Historical Fire Activity
                | October–November 2024
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

