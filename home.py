import streamlit as st

# Page configuration
st.set_page_config(
    page_title="Quantem - The Future of Free Market Intelligence",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for dark theme and improved table
st.markdown("""
<style>
/* Overall background */
.stApp {
    background-color: #0c1929 !important;
    background-image: url("ChatGPT Image Apr 5, 2025, 03_30_12 PM.png");
    background-size: cover;
    background-position: center;
    background-blend-mode: overlay;
}

/* Make containers transparent */
.main .block-container {
    background-color: transparent !important;
}

/* Text colors */
p, h1, h2, h3, h4, h5, h6, span, li, td, th {
    color: white !important;
}

/* Hide Streamlit branding */
#MainMenu, footer, header {
    visibility: hidden;
}

/* Custom table styling */
.custom-table {
    width: 100%;
    border-collapse: collapse;
    margin: 25px 0;
    font-size: 16px;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 0 20px rgba(0, 0, 0, 0.3);
}

.custom-table thead tr {
    background-color: rgba(255, 215, 0, 0.8);
    color: #0c1929 !important;
    text-align: left;
    font-weight: bold;
}

.custom-table th,
.custom-table td {
    padding: 14px 18px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.2);
}

.custom-table th {
    color: #0c1929 !important;
}

.custom-table tbody tr {
    background-color: rgba(255, 255, 255, 0.07);
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.custom-table tbody tr:nth-of-type(even) {
    background-color: rgba(255, 255, 255, 0.05);
}

.custom-table tbody tr:last-of-type {
    border-bottom: 2px solid rgba(255, 215, 0, 0.5);
}

.custom-table tbody tr:hover {
    background-color: rgba(255, 255, 255, 0.15);
}

/* Button styling */
div.stButton > button {
    background-color: #FFD700 !important;
    color: #0c1929 !important;
    font-size: 18px !important;
    font-weight: 600 !important;
    padding: 12px 24px !important;
    border-radius: 6px !important;
    border: none !important;
    cursor: pointer !important;
    transition: all 0.3s ease !important;
}

div.stButton > button:hover {
    background-color: #ffeb3b !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(255, 215, 0, 0.3) !important;
}

/* Center button */
.center-button {
    display: flex;
    justify-content: center;
    margin-top: 40px;
}

/* Content container */
.content-container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

/* Spacing */
.section-spacer {
    margin-top: 40px;
    margin-bottom: 40px;
}
</style>
""", unsafe_allow_html=True)

# Title and main content
st.markdown("<h1 style='text-align: center; font-size: 48px; margin-bottom: 20px;'>Quantem: The Future of Free Market Intelligence</h1>", unsafe_allow_html=True)

st.markdown("<p style='text-align: center; font-size: 18px; max-width: 900px; margin: 0 auto; margin-bottom: 20px;'>Unlock high-level trading insights that most platforms hide behind paywalls. We're breaking all those rules—because, frankly, we can.</p>", unsafe_allow_html=True)

st.markdown("<p style='text-align: center; font-size: 16px; max-width: 1000px; margin: 0 auto; margin-bottom: 50px;'>At Quantem, we believe advanced analytics and AI-driven strategies should be accessible to every investor. Our open-source approach ensures transparency, flexibility, and a cost-free toolkit that puts you ahead of the market. No hidden fees, no watered-down features—just pure market intelligence at your fingertips.</p>", unsafe_allow_html=True)

# Comparison section with custom HTML table
st.markdown("<h2 style='text-align: center; margin-top: 50px; margin-bottom: 30px;'>How Quantem Compares</h2>", unsafe_allow_html=True)

# Create custom HTML table
table_html = """
<table class="custom-table">
    <thead>
        <tr>
            <th>Feature</th>
            <th>Quantem</th>
            <th>Typical Platforms</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>Access</td>
            <td>Open source, built to be shared</td>
            <td>Closed, proprietary systems</td>
        </tr>
        <tr>
            <td>Cost</td>
            <td>Completely free</td>
            <td>Subscriptions of tiered plans</td>
        </tr>
        <tr>
            <td>Advanced Analytics</td>
            <td>AI-driven, real-time insights</td>
            <td>Paywalled or limited advanced features</td>
        </tr>
        <tr>
            <td>Technical Indicators</td>
            <td>28+ Indicators, continuously growing</td>
            <td>Usually limited or locked behind add-ons</td>
        </tr>
        <tr>
            <td>Built-In Strategies</td>
            <td>6 Core Strategies (plus user-defined)</td>
            <td>Minimal or premium-only strategies</td>
        </tr>
        <tr>
            <td>Benchmark Comparisons</td>
            <td>Includes SPY, QQQ, DIA, IWM, etc</td>
            <td>Often unavailable or paywalled</td>
        </tr>
        <tr>
            <td>Customization Control</td>
            <td>Full transparency; user-driven options</td>
            <td>Frequently locked behind premium tiers</td>
        </tr>
    </tbody>
</table>
"""

st.markdown(table_html, unsafe_allow_html=True)

# Call to action section
st.markdown("<h2 style='text-align: center; margin-top: 60px; margin-bottom: 30px;'>Ready to Experience Markets on Your Own Terms?</h2>", unsafe_allow_html=True)

# Button centered with custom styling
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("Get Started with Quantem", key="get_started", use_container_width=True):
        st.switch_page("pages/0_API_Setup.py")

# Add extra space at the bottom for better spacing
st.markdown("<div style='height: 60px;'></div>", unsafe_allow_html=True)