
import streamlit as st
import streamlit.components.v1 as components


def render_mission_header():

    html = """
    <!DOCTYPE html>
    <html>
    <head>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/animejs/3.2.2/anime.min.js"></script>

    <style>
    * {
        box-sizing: border-box;
    }

    body {
        margin: 0;
        background: transparent;
        font-family: Arial, sans-serif;
        color: #F1F5F9;
        overflow: hidden;
    }

    .mission {
        height: 250px;
        width: 100%;
        background:
            radial-gradient(circle at 78% 48%, #203C55 0%, transparent 34%),
            linear-gradient(110deg, #101C2D, #14283B);
        border: 1px solid #30465D;
        border-radius: 16px;
        position: relative;
        overflow: hidden;
        display: flex;
        align-items: center;
        padding: 30px 38px;
    }

    .mission-content {
        position: relative;
        z-index: 3;
        max-width: 65%;
    }

    .eyebrow {
        color: #F5A623;
        font-size: 11px;
        font-weight: bold;
        letter-spacing: 3px;
        margin-bottom: 17px;
    }

    .title {
        font-size: clamp(25px, 4vw, 42px);
        font-weight: 800;
        letter-spacing: -1px;
        margin: 0;
        color: #F8FAFC;
    }

    .subtitle {
        color: #A9BACB;
        font-size: 14px;
        margin-top: 12px;
        line-height: 1.6;
    }

    .mission-tag {
        display: inline-block;
        margin-top: 19px;
        padding: 7px 12px;
        border: 1px solid #52657A;
        border-radius: 5px;
        color: #D5E1ED;
        font-size: 10px;
        letter-spacing: 1px;
    }

    .visual {
        position: absolute;
        right: 4%;
        top: 0;
        width: 300px;
        height: 250px;
    }

    .earth {
        position: absolute;
        width: 130px;
        height: 130px;
        top: 59px;
        left: 90px;
        border-radius: 50%;
        background:
            radial-gradient(circle at 32% 30%, #73B8D2, #235477 55%, #10263C 85%);
        box-shadow:
            0 0 30px #3185AD55,
            inset -15px -8px 25px #061525;
    }

    .earth::before {
        content: "";
        position: absolute;
        inset: 0;
        border-radius: 50%;
        background: repeating-linear-gradient(
            90deg,
            transparent 0px,
            transparent 22px,
            #9DD9E722 23px,
            transparent 25px
        );
    }

    .orbit {
        position: absolute;
        width: 250px;
        height: 145px;
        left: 30px;
        top: 50px;
        border: 1px solid #8AB8D455;
        border-radius: 50%;
        transform: rotate(-25deg);
    }

    .satellite {
        position: absolute;
        top: 0;
        left: 0;
        font-size: 22px;
        filter: drop-shadow(0 0 7px #F5A623);
    }

    .radar {
        position: absolute;
        width: 165px;
        height: 165px;
        top: 42px;
        left: 72px;
        border-radius: 50%;
        border: 1px solid #F5A62333;
        overflow: hidden;
    }

    .radar-sweep {
        position: absolute;
        width: 50%;
        height: 50%;
        left: 50%;
        top: 0;
        transform-origin: bottom left;
        background: linear-gradient(
            45deg,
            #F5A62300,
            #F5A62366
        );
        border-right: 1px solid #F5A623;
    }

    .status {
        position: absolute;
        bottom: 18px;
        right: 25px;
        color: #8DA5BA;
        font-size: 9px;
        letter-spacing: 1px;
    }

    @media(max-width: 650px) {
        .mission {
            padding: 20px;
        }

        .mission-content {
            max-width: 100%;
        }

        .visual {
            opacity: 0.22;
            right: -100px;
        }
    }
    </style>
    </head>

    <body>
    <div class="mission">

        <div class="mission-content">
            <div class="eyebrow">EARTH OBSERVATION / FIRE ANALYTICS</div>

            <h1 class="title">Fire Intelligence</h1>

            <div class="subtitle">
                Punjab–Haryana Regional Monitoring<br>
                Historical Satellite Observations · Oct–Nov 2024
            </div>

            <div class="mission-tag">
                MODIS AQUA &nbsp; / &nbsp; SUOMI-NPP VIIRS
            </div>
        </div>

        <div class="visual">
            <div class="orbit" id="orbit-path"></div>
            <div class="earth"></div>

            <div class="satellite" id="satellite">
                🛰
            </div>

            <div class="radar">
                <div class="radar-sweep" id="sweep"></div>
            </div>
        </div>

        <div class="status">
            HISTORICAL DATA MODE
        </div>
    </div>

    <script>
    if (typeof anime !== "undefined") {

        anime({
            targets: ".mission-content",
            translateY: [18, 0],
            opacity: [0, 1],
            duration: 1100,
            easing: "easeOutExpo"
        });

        anime({
            targets: "#sweep",
            rotate: 360,
            duration: 5000,
            loop: true,
            easing: "linear"
        });

        const orbit = anime.path("#orbit-path");

        anime({
            targets: "#satellite",
            translateX: orbit("x"),
            translateY: orbit("y"),
            rotate: orbit("angle"),
            duration: 12000,
            loop: true,
            easing: "linear"
        });
    }
    </script>

    </body>
    </html>
    """

    components.html(
        html,
        height=265,
        scrolling=False,
    )
