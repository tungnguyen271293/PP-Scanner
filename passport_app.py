
import importlib.metadata
import sys
import os
import json
import time
import datetime
import re
import base64

# Patch importlib.metadata for Python 3.9 compatibility
try:
    import importlib_metadata
    if not hasattr(importlib.metadata, 'packages_distributions'):
        importlib.metadata.packages_distributions = importlib_metadata.packages_distributions
except ImportError:
    pass

import streamlit as st
import google.generativeai as genai
from PIL import Image
from openai import OpenAI
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from google_drive import upload_screenshot_to_drive

# --- CONFIGURATION ---

# 1. API Key Config
# Try secrets (local/Streamlit Cloud) -> then Env Var (Hugging Face) -> then Default
DEFAULT_API_KEY = st.secrets.get("default", {}).get("api_key", os.getenv("AI_API_KEY", ""))

# 2. Listings Config
LISTINGS = st.secrets.get("listings", {})

if not LISTINGS:
    # Check environment variable 'LISTINGS_JSON'
    env_listings = os.getenv("LISTINGS_JSON")
    if env_listings:
        try:
            LISTINGS = json.loads(env_listings)
        except json.JSONDecodeError:
            pass
            
# 3. Fallback for testing
if not LISTINGS:
    # If no secrets found, use a placeholder (User must configure secrets!)
    LISTINGS = {
        "Example Villa": {"username": "demo", "password": "demo"},
    }

# Map codes to the exact text in the dropdown
NATIONALITY_MAP = {
    "0RQ": "0RQ - Không rõ quốc tịch",
    "ABW": "ABW - A-ru-ba",
    "AFG": "AFG - Ap-ga-ni-xtan",
    "AGO": "AGO - Ăng-gô-la",
    "AIA": "AIA - Ăng-gui-la",
    "ALB": "ALB - An-ba-ni",
    "AND": "AND - Công quốc An-đơ-ra",
    "ANT": "ANT - Quần đảo An-ti thuộc Hà Lan",
    "ARE": "ARE - A-rập thống nhất",
    "ARG": "ARG - Ac-hen-ti-na",
    "ARM": "ARM - Ac-mê-ni-a",
    "ASM": "ASM - Đông Sa-moa",
    "ATA": "ATA - Nam Cực",
    "ATF": "ATF - Vùng Nam bán cầu thuộc Pháp",
    "ATG": "ATG - Ăng-ti-gua và Bác-bu-da",
    "AUS": "AUS - Ô-xtrây-li-a",
    "AUT": "AUT - Áo",
    "AZE": "AZE - A-đéc-bai-gian",
    "BDI": "BDI - Bu-run-đi",
    "BEL": "BEL - Bỉ",
    "BEN": "BEN - Bê-nanh",
    "BFA": "BFA - Buốc-ki-na Pha-xô",
    "BGD": "BGD - Băng-la-đét",
    "BGR": "BGR - Bun-ga-ri",
    "BHR": "BHR - Ba-ra-in",
    "BHS": "BHS - Ba-ha-ma",
    "BIH": "BIH - Bô-xni-a Héc-dê-gô-vi-na",
    "BLR": "BLR - Bê-la-rút",
    "BLZ": "BLZ - Bê-li-xê",
    "BMU": "BMU - Béc-mu-đa",
    "BOL": "BOL - Bô-li-vi-a",
    "BRA": "BRA - Bra-din",
    "BRB": "BRB - Bác-ba-đốt",
    "BRN": "BRN - Brunei",
    "BTN": "BTN - Bu-tan",
    "BVT": "BVT - Đảo Bô-u-vet",
    "BWA": "BWA - Bốt-xoa-na",
    "CAF": "CAF - Cộng hoà Trung Phi",
    "CAN": "CAN - Ca-na-da",
    "CCK": "CCK - Quần đảo Dừa",
    "CHE": "CHE - Thuỵ Sĩ",
    "CHL": "CHL - Chi-lê",
    "CHN": "CHN - Trung Quốc",
    "CIV": "CIV - Cốt Đi-voa",
    "CMR": "CMR - Ca-mơ-run",
    "COG": "COG - Công-gô",
    "COK": "COK - Quần đảo Cúc",
    "COL": "COL - Cô-lôm-bi-a",
    "COM": "COM - Cô-mo",
    "CPV": "CPV - Cáp-ve",
    "CRI": "CRI - Cô-xta Ri-ca",
    "CUB": "CUB - Cu Ba",
    "CXR": "CXR - Đảo Chri-xma",
    "CYM": "CYM - Quần đảo Cây-man",
    "CYP": "CYP - Đảo Síp",
    "CZE": "CZE - Cộng hoà Séc",
    "D": "D - CH Liên bang Đức",
    "DEU": "DEU - CH Liên bang Đức",
    "DJI": "DJI - Đi-bô-u-ti",
    "DMA": "DMA - Đô-mi-ni-ca",
    "DNK": "DNK - Đan Mạch",
    "DOM": "DOM - CH Đô-mi-ni-ca-na",
    "DZA": "DZA - An-giê-ri",
    "ECU": "ECU - Ê-cu-a-đo",
    "EGY": "EGY - Ai Cập",
    "ERI": "ERI - Ê-ri-tơ-ri-a",
    "ESH": "ESH - Tây Xa-ha-ra",
    "ESP": "ESP - Tây Ban Nha",
    "EST": "EST - Ê-xtô-ni-a",
    "ETH": "ETH - Ê-ti-ô-pi-a",
    "FIN": "FIN - Phần Lan",
    "FJI": "FJI - Fi-ji",
    "FLK": "FLK - Quần đảo Man-vi-na",
    "FRA": "FRA - Pháp",
    "FRO": "FRO - Fa-rô",
    "FSM": "FSM - Mi-crô-nê-si-a",
    "FXX": "FXX - Vùng Thủ đô Pháp",
    "GAB": "GAB - Ga-bông",
    "GBD": "GBD - Công dân các địa phận thuộc Vương quốc Liên hiệp Anh",
    "GBN": "GBN - Địa phận thuộc Liên hiệp Anh",
    "GBO": "GBO - Địa phận hải ngoại thuộc Liên hiệp Anh",
    "GBP": "GBP - Người được Liên hiệp Anh bảo hộ",
    "GBR": "GBR - Vương quốc Anh",
    "GBS": "GBS - Thần dân của Vương quốc Liên hiệp Anh",
    "GEO": "GEO - Gru-đi-a",
    "GHA": "GHA - Ga-na",
    "GIB": "GIB - Gi-bran-ta",
    "GIN": "GIN - Ghi-nê",
    "GLP": "GLP - Gua-đơ-lúp",
    "GMB": "GMB - Găm-bi-a",
    "GNB": "GNB - Ghi-nê Bít-xao",
    "GNQ": "GNQ - Ghi-nê Xích đạo",
    "GRC": "GRC - Hy Lạp",
    "GRD": "GRD - Grê-na-đa",
    "GRL": "GRL - Grin-lơn",
    "GTM": "GTM - Goa-tê-ma-la",
    "GUF": "GUF - Guy-a-na thuộc Pháp",
    "GUM": "GUM - Gu-am",
    "GUY": "GUY - Gui-na",
    "HKG": "HKG - Hồng-công",
    "HMD": "HMD - Quần đảo Hớt và Mac-đô-nan",
    "HND": "HND - Hon-du-rat",
    "HRV": "HRV - Crô-a-ti-a",
    "HTI": "HTI - Ha-i-ti",
    "HUN": "HUN - Hung-ga-ri",
    "IDN": "IDN - In-đô-nê-xi-a",
    "IND": "IND - Ấn Độ",
    "IOT": "IOT - Vùng đất thuộc Anh ở Ấn Độ Dương",
    "IRL": "IRL - Ai-rơ-len",
    "IRN": "IRN - CH Hồi giáo I-ran",
    "IRQ": "IRQ - I-rắc",
    "ISL": "ISL - Ai-xơ-len",
    "ISR": "ISR - I-xra-en",
    "ITA": "ITA - I-ta-li-a",
    "JAM": "JAM - Ja-mai-ca",
    "JOR": "JOR - Joc-đan",
    "JPN": "JPN - Nhật Bản",
    "KAZ": "KAZ - Ka-dắc-xtan",
    "KEN": "KEN - Kê-ni-a",
    "KGZ": "KGZ - Kiếc-ghi-di-a",
    "KHM": "KHM - Căm-pu-chia",
    "KIR": "KIR - Ki-ri-ba-ti",
    "KNA": "KNA - Liên bang Xanh Kít và Nê-vít",
    "KOR": "KOR - CH Hàn Quốc",
    "KWT": "KWT - Cô-oét",
    "LAO": "LAO - CHDCND Lào",
    "LBN": "LBN - Li-ban",
    "LBR": "LBR - Li-bê-ri-a",
    "LBY": "LBY - Gia-ma-hi-ri-i-a A-rập Li-bi Nhân dân",
    "LCA": "LCA - Xanh Lu-xi-a",
    "LIE": "LIE - Công quốc Lích-ten-xtên",
    "LKA": "LKA - Xri-Lan-ca",
    "LSO": "LSO - Lê-xô-thô",
    "LTU": "LTU - Lít-hua-ni-a",
    "LUX": "LUX - Luých-xem-bua",
    "LVA": "LVA - Lát-vi-a",
    "MAC": "MAC - Ma cao",
    "MAR": "MAR - Ma-rốc",
    "MCO": "MCO - Công quốc Mô-na-cô",
    "MDA": "MDA - Môn-đô-va",
    "MDG": "MDG - Ma-đa-ga-xca",
    "MDV": "MDV - Man-đi-vơ",
    "MEX": "MEX - Mê-xi-cô",
    "MHL": "MHL - Quần đảo Mác-san",
    "MKD": "MKD - CH Ma-xê-đô-ni-a",
    "MLI": "MLI - Ma-li",
    "MLT": "MLT - Man-ta",
    "MMR": "MMR - Mi-an-ma",
    "MNE": "MNE - Môn-tê-nê-grô",
    "MNG": "MNG - Mông Cổ",
    "MNP": "MNP - Quần đảo Bắc Ma-ri-a-na",
    "MOZ": "MOZ - Mô-dăm-bích",
    "MRT": "MRT - Mô-ra-ta-ni",
    "MSR": "MSR - Môn-xê-rat",
    "MTQ": "MTQ - Mac-ti-nic",
    "MUS": "MUS - Mô-ri-xơ",
    "MWI": "MWI - Ma-la-uy",
    "MYS": "MYS - Ma-lai-xi-a",
    "MYT": "MYT - May-ốt",
    "NAM": "NAM - Na-mi-bi-a",
    "NCL": "NCL - Niu Ca-le-đô-ni-a",
    "NER": "NER - Ni-giê",
    "NFK": "NFK - Đảo Nô-rốc",
    "NGA": "NGA - Ni-giê-ri-a",
    "NIC": "NIC - Ni-ca-ra-goa",
    "NIU": "NIU - Ni-u-ê",
    "NLD": "NLD - Hà Lan",
    "NOR": "NOR - Vương quốc Na-uy",
    "NPL": "NPL - Nê-pan",
    "NRU": "NRU - Na-u-ru",
    "NTZ": "NTZ - Vùng Trung lập",
    "NZL": "NZL - Niu Di-lân",
    "OMN": "OMN - Ô-man",
    "PAK": "PAK - Pa-ki-xtan",
    "PAN": "PAN - Pa-na-ma",
    "PCN": "PCN - Pi-ca-in",
    "PER": "PER - Pê-ru",
    "PHL": "PHL - Phi-líp-pin",
    "PLW": "PLW - Pa-lau",
    "PLX": "PLX - Pa-le-xtin",
    "PNG": "PNG - Pa-pua Niu Ghi-nê",
    "POL": "POL - Ba Lan",
    "PRI": "PRI - Pu-éc-tô Ri-cô",
    "PRK": "PRK - CHDCND Triều Tiên",
    "PRT": "PRT - Bổ Đào Nha",
    "PRY": "PRY - Pa-ra-goay",
    "PSE": "PSE - Pa-le-xtin",
    "PYF": "PYF - Po-ly-nê-si-a",
    "QAT": "QAT - Qua-ta",
    "REU": "REU - Rê-u-ni-on",
    "RKS": "RKS - Kô-xô-vô",
    "ROM": "ROM - Ru-ma-ni",
    "ROU": "ROU - Ru-ma-ni",
    "RUS": "RUS - Liên bang Nga",
    "RWA": "RWA - Ru-an-đa",
    "SAU": "SAU - A-rập Xau-đi",
    "SC-": "SC- - Xcô-lent",
    "SDN": "SDN - Xu-đăng",
    "SEN": "SEN - Xe-ne-gan",
    "SGP": "SGP - Xin-ga-po",
    "SGS": "SGS - Quần đảo Nam Gru-di-a và Nam San-uých",
    "SHN": "SHN - Đào Xanh Hê-lê-na",
    "SJM": "SJM - Quần đảo Xvan-ba và Gan Mai-en",
    "SLB": "SLB - Quần đảo Xa-lô-mông",
    "SLE": "SLE - Xi-ê-ra Li-ôn",
    "SLV": "SLV - En Xan-va-đo",
    "SMR": "SMR - Xan Ma-ri-nô",
    "SOM": "SOM - Xô-ma-li",
    "SPM": "SPM - Xanh Pi-ê và Mi-cơ-lông",
    "SRB": "SRB - Xéc-bi-a",
    "STP": "STP - Xao Tô-mê và Prin-xi-pê",
    "SUR": "SUR - Xu-ri-nam",
    "SVK": "SVK - Xlô-va-ki-a",
    "SVN": "SVN - Slo-vê-ni-a",
    "SWE": "SWE - Thuỵ Điển",
    "SWZ": "SWZ - Xoa-di-len",
    "SYC": "SYC - Quần đảo Xây-sen",
    "SYR": "SYR - CH A-rập Xy-ri",
    "TCA": "TCA - Quần đảo Tuc và Ca-i-ô",
    "TCD": "TCD - Sát",
    "TGO": "TGO - Tô-gô",
    "THA": "THA - Thái Lan",
    "TJK": "TJK - Ta-gi-ki-xtan",
    "TKL": "TKL - Tô-ke-lau",
    "TKM": "TKM - Tuốc-mê-ni-xtan",
    "TLS": "TLS - Đông Ti-mo",
    "TMP": "TMP - Đông Ti-mo",
    "TON": "TON - Tôn-ga",
    "TTO": "TTO - CH Tớ-ri-ni-đát và Tô-ba-gô",
    "TUN": "TUN - Tu-ni-di",
    "TUR": "TUR - Thổ Nhĩ Kỳ",
    "TUV": "TUV - Tu-va-lu",
    "TWN": "TWN - Trung Quốc (Đài Loan)",
    "TZA": "TZA - CH thống nhất Tan-da-ni-a",
    "UGA": "UGA - U-gan-da",
    "UKR": "UKR - U-crai-na",
    "UMI": "UMI - Quần đảo nhỏ thuộc Mỹ",
    "UNO": "UNO - HC Liên hiệp quốc",
    "URY": "URY - U-ru-goay",
    "USA": "USA - Mỹ",
    "UZB": "UZB - U-dơ-bê-ki-xtan",
    "VAT": "VAT - Va-ti-căng",
    "VCT": "VCT - Xanh Vin-xen và Grê-na-din",
    "VEN": "VEN - Vê-nê-du-ê-la",
    "VGB": "VGB - Quần đảo Vi-gin (Anh)",
    "VIR": "VIR - Quần đảo Vi-gin (Mỹ)",
    "VNM": "VNM - Việt Nam",
    "VUT": "VUT - Va-nu-a-tu",
    "WLF": "WLF - Quần đảo Oa-li và Fu-tu-na",
    "WSM": "WSM - Xa-moa",
    "YEM": "YEM - Y-ê-men",
    "YUG": "YUG - Nam-tư",
    "ZAF": "ZAF - Nam Phi",
    "ZAR": "ZAR - Da-i-re",
    "ZMB": "ZMB - Dăm-bi-a",
    "ZWE": "ZWE - Dim-ba-bu-ê",
}

# --- 1. THE BRAIN (Passport Reader - Hybrid Version) ---
def extract_passport_data(uploaded_file, api_key):
    """Detects API key type and extracts data using Gemini or OpenAI"""
    
    # Common helper to clean and parse JSON
    def clean_and_parse_json(text_content):
        text_content = text_content.strip()
        # Find first { and last }
        match = re.search(r'(\{.*\})', text_content, re.DOTALL)
        if match:
            text_content = match.group(1)
        return json.loads(text_content)

    # 1. Choose Engine based on API Key
    if api_key.startswith("sk-"):
        # OpenAI Version
        st.info("💡 Using OpenAI engine (GPT-4o)")
        client = OpenAI(api_key=api_key)
        base64_image = base64.b64encode(uploaded_file.getvalue()).decode('utf-8')
        
        prompt = """
        Extract data from this passport into this JSON structure:
        {
          "full_name": "STRING (UPPERCASE)",
          "passport_number": "STRING",
          "nationality_code": "3-letter ISO code (e.g. BGR, USA, KOR)",
          "dob": "DD/MM/YYYY",
          "sex": "F or M"
        }
        """

        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a passport extraction API. Output only JSON."},
                    {"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]}
                ],
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            return clean_and_parse_json(content)
        except Exception as e:
            st.error(f"OpenAI Error: {e}")
            raise e
    
    else:
        # Gemini Version
        st.info("💡 Using Google Gemini engine")
        genai.configure(api_key=api_key)
        
        # Try a wider variety of model names
        model_names = [
            'gemini-2.5-flash',
            'gemini-2.5-pro',
            'gemini-2.0-flash',
            'gemini-1.5-flash', 
            'gemini-1.5-pro'
        ]
        
        last_err = None
        for name in model_names:
            try:
                model = genai.GenerativeModel(name)
                image = Image.open(uploaded_file)
                prompt = """
                Analyze this passport image and extract data into strict JSON:
                {
                  "full_name": "STRING (UPPERCASE)",
                  "passport_number": "STRING",
                  "nationality_code": "3-letter ISO code (e.g. BGR, USA, KOR)",
                  "dob": "DD/MM/YYYY",
                  "sex": "F or M"
                }
                Return ONLY the JSON. No markdown.
                """
                response = model.generate_content([prompt, image])
                
                try:
                    data = clean_and_parse_json(response.text)
                except json.JSONDecodeError:
                    # Retry or skip if JSON is malformed
                    continue
                
                if "passport_number" in data:
                    st.success(f"✅ Success using model: {name}")
                    return data
            except Exception as e:
                last_err = e
                continue
        
        # If we reach here, all models failed. Let's list what's available.
        st.error(f"❌ All attempted models failed. Last error: {last_err}")
        try:
            available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            st.write("### 🛠 Diagnostic: Available models for your key:")
            st.code("\n".join(available_models))
            st.info("Please copy an available model name from the list above and let me know.")
        except Exception as list_err:
            st.error(f"Could not list models: {list_err}")
        
        raise Exception("Model compatibility error. See diagnostic info above.")

# --- 2. THE HANDS (Selenium Automation) ---
def run_automation(guests_list, username, password, arrival_date_str, departure_date_str, listing_name, headless_mode=True):
    """Runs the browser automation with a list of extracted guest data"""
    
    st.info("🚀 Starting automation engine...")
    
    # Setup Browser
    options = webdriver.ChromeOptions()
    options.add_experimental_option("detach", True) # Keep browser open
    if headless_mode:
        st.info("👻 Running in Headless Mode (Invisible Browser)")
        options.add_argument("--headless")
        options.add_argument("--window-size=1920,1080")
    
    # Stability Flags for macOS/Linux
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")
    
    # Platform-specific binary location (Only for Mac)
    if sys.platform == "darwin":
        chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        if os.path.exists(chrome_path):
            options.binary_location = chrome_path
    
    try:
        # Selenium 4.6+ automatically handles driver management via Selenium Manager
        service = Service() 
        driver = webdriver.Chrome(service=service, options=options)
    except Exception as init_err:
        st.error(f"❌ Failed to initialize Chrome: {init_err}")
        st.info("💡 Tip: Ensure Google Chrome is installed and updated.")
        return

    wait = WebDriverWait(driver, 30)

    try:
        # Login
        st.info("🌐 Navigating to portal and logging in...")
        driver.get("https://danang.xuatnhapcanh.gov.vn/faces/index.jsf")
        
        # 1. Click "Đăng nhập" to reveal form
        login_reveal = wait.until(EC.element_to_be_clickable((By.ID, "pt1:pt_l1")))
        login_reveal.click()
        
        # 2. WAIT for Username field to be VISIBLE
        st.write("⏳ Waiting for login form to appear...")
        user_field = wait.until(EC.visibility_of_element_located((By.ID, "pt1:s1:it1::content")))
        user_field.clear()
        user_field.send_keys(username)
        
        pass_field = driver.find_element(By.ID, "pt1:s1:it2::content")
        pass_field.clear()
        pass_field.send_keys(password)
        
        # 3. Click Login Button
        st.write("🖱 Attempting login click...")
        login_btn_wrapper = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[id='pt1:s1:b1'] a")))
        driver.execute_script("arguments[0].click();", login_btn_wrapper)
        
        # 4. Verify Login Success
        st.write("🔍 Verifying login result...")
        try:
            wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'CHỨC NĂNG')] | //*[contains(text(), 'Đăng xuất')]")))
        except TimeoutException:
            try:
                error_msg = driver.find_element(By.ID, "pt1:s1:pfl5").text
                st.error(f"❌ Login Error: {error_msg}")
            except NoSuchElementException:
                st.error("⏰ Login failed or timed out. Please check your credentials manually.")
            return
        
        st.success("✅ Login successful!")
        time.sleep(1)

        # 1. Navigate to Guest Declaration form ONCE
        st.write("🔄 Navigating to declaration form...")
        driver.get("https://danang.xuatnhapcanh.gov.vn/faces/manage_kbtt.jsf")
        
        # 2. Click Add New ONCE to enter the form
        st.write("🖱 Opening 'Thêm mới' form...")
        try:
            add_btn_xpath = "//*[contains(text(), 'Thêm mới')] | //a[contains(., 'Thêm mới')]"
            add_btn = wait.until(EC.presence_of_element_located((By.XPATH, add_btn_xpath)))
            driver.execute_script("arguments[0].scrollIntoView(true);", add_btn)
            driver.execute_script("arguments[0].click();", add_btn)
        except Exception as e:
            st.error(f"❌ Failed to click 'Thêm mới': {e}")
            return

        # Batch Loop
        for i, guest_data in enumerate(guests_list):
            st.divider()
            st.write(f"### 👤 Processing Guest {i+1}/{len(guests_list)}: {guest_data['full_name']}")
            
            # Wait for form to be ready (look for any field)
            wait.until(EC.presence_of_element_located((By.ID, "pt1:r1:1:it1::content")))

            # --- FILL/OVERWRITE FORM ---
            # 1. Passport Number
            field_pass = driver.find_element(By.ID, "pt1:r1:1:it3::content")
            field_pass.clear()
            field_pass.send_keys(guest_data['passport_number'])

            # 2. Nationality
            nat_element = driver.find_element(By.ID, "pt1:r1:1:soc4::content")
            nat_select = Select(nat_element)
            target_code = guest_data['nationality_code']
            found = False

            # Optimized Selection via Map
            if target_code in NATIONALITY_MAP:
                try:
                    nat_select.select_by_visible_text(NATIONALITY_MAP[target_code])
                    found = True
                except Exception:
                    pass
            
            # Fallback Loop
            if not found:
                for option in nat_select.options:
                    if target_code in option.text:
                        nat_select.select_by_visible_text(option.text)
                        found = True
                        break
            
            if not found:
                st.error(f"Could not find nationality code: {target_code}")

            # 3. Full Name
            field_name = driver.find_element(By.ID, "pt1:r1:1:it2::content")
            field_name.clear()
            # Sanitize name: Remove special chars, digits, ensure Uppercase
            raw_name = guest_data['full_name']
            clean_name = re.sub(r'[^a-zA-Z\s]', '', raw_name).upper()
            # Reduce multiple spaces to one
            clean_name = re.sub(r'\s+', ' ', clean_name).strip()
            
            field_name.send_keys(clean_name)

            # 4. Gender
            gender_select = Select(driver.find_element(By.ID, "pt1:r1:1:soc1::content"))
            target_sex = "F - Nữ" if guest_data['sex'] == "F" else "M - Nam"
            gender_select.select_by_visible_text(target_sex)

            # 5. DOB
            dob_input = driver.find_element(By.ID, "pt1:r1:1:id1::content")
            dob_input.clear()
            dob_input.send_keys(guest_data['dob'])
            dob_input.send_keys(Keys.ESCAPE)

            # 6. Arrival Date
            try:
                # Find input near label "Ngày đến cơ sở lưu trú"
                # Strategy: Find the label row, then the input in that row or following it
                arrival_xpath = "//*[contains(text(), 'Ngày đến cơ sở lưu trú')]/following::input[1]" 
                arrival_field = driver.find_element(By.XPATH, arrival_xpath)
                arrival_field.clear()
                arrival_field.send_keys(arrival_date_str)
                arrival_field.send_keys(Keys.ESCAPE)
            except Exception as e:
                st.warning(f"⚠️ Could not auto-fill Arrival Date: {e}")

            # 7. Departure Date
            try:
                # Find input near label "Ngày đi dự kiến"
                departure_xpath = "//*[contains(text(), 'Ngày đi dự kiến')]/following::input[1]"
                departure_field = driver.find_element(By.XPATH, departure_xpath)
                departure_field.clear()
                departure_field.send_keys(departure_date_str)
                departure_field.send_keys(Keys.ESCAPE)
            except Exception as e:
                st.warning(f"⚠️ Could not auto-fill Departure Date: {e}")

            # 8. Room Number (For ALC listings)
            if listing_name.strip().startswith("ALC"):
                try:
                    # Extract room number (e.g. "ALC 1710" -> "1710")
                    parts = listing_name.strip().split()
                    if len(parts) >= 2:
                        room_number = parts[1]
                        
                        # Find input near label "Số phòng"
                        room_xpath = "//*[contains(text(), 'Số phòng')]/following::input[1]"
                        room_field = driver.find_element(By.XPATH, room_xpath)
                        room_field.clear()
                        room_field.send_keys(room_number)
                except Exception as e:
                    st.warning(f"⚠️ Could not auto-fill Room Number for {listing_name}: {e}")

            st.info(f"💾 Auto-Saving Guest {i+1}...")

            try:
                # 1. Click "Lưu thông tin"
                # Locate button by text
                save_xpath = "//*[contains(text(), 'Lưu thông tin')] | //button[contains(., 'Lưu')]"
                save_btn = wait.until(EC.element_to_be_clickable((By.XPATH, save_xpath)))
                driver.execute_script("arguments[0].click();", save_btn)
                
                # 2. Handle "OK" Success Dialog
                st.write("⏳ Waiting for confirmation...")
                ok_xpath = "//*[normalize-space(text())='OK'] | //button[contains(., 'OK')]"
                ok_btn = wait.until(EC.element_to_be_clickable((By.XPATH, ok_xpath)))
                driver.execute_script("arguments[0].click();", ok_btn)
                st.success(f"✅ Guest {i+1} Saved!")
                
                time.sleep(2) # Allow transition back to list
                
                # 3. Prepare for Next Guest (if any)
                if i < len(guests_list) - 1:
                    st.write("🔄 Preparing next guest...")
                    # Wait for "Thêm mới" to confirm we are back on the list page
                    add_btn_xpath = "//*[contains(text(), 'Thêm mới')] | //a[contains(., 'Thêm mới')]"
                    add_btn = wait.until(EC.presence_of_element_located((By.XPATH, add_btn_xpath)))
                    driver.execute_script("arguments[0].scrollIntoView(true);", add_btn)
                    driver.execute_script("arguments[0].click();", add_btn)

            except Exception as e:
                st.error(f"❌ Automated Save Failed: {type(e).__name__} - {e}")
                
                # Capture Screenshot for Debugging
                try:
                    screenshot_path = "error_screenshot.png"
                    driver.save_screenshot(screenshot_path)
                    st.toast("📸 Screenshot captured for debugging")
                    st.image(screenshot_path, caption="Error State Screenshot")
                except Exception as shot_err:
                    st.warning(f"Could not capture screenshot: {shot_err}")

                # Try to read page source for error messages
                try:
                    # Generic lookup for JSF/PrimeFaces error messages
                    errors = driver.find_elements(By.CSS_SELECTOR, ".ui-messages-error-summary, .ui-message-error-detail, .ui-messages-error")
                    if errors:
                        st.error("⚠️ Website Error Messages Found:")
                        for err in errors:
                            st.error(f"- {err.text}")
                except:
                    pass
                
                break

        st.balloons()
        st.success("🏁 All guests in the batch have been processed!")
        
        # --- SCREENSHOT & GOOGLE DRIVE UPLOAD ---
        st.info("📸 Taking a final screenshot of the guest list...")
        try:
            # 1. Xử lý triệt để các cảnh báo (Alert) đang bị kẹt trước khi chuyển trang
            try:
                alert = driver.switch_to.alert
                alert.accept()
                time.sleep(1)
            except Exception:
                pass # Không có alert nào thì bỏ qua

            # Navigate to the main list view
            driver.get("https://danang.xuatnhapcanh.gov.vn/faces/manage_kbtt.jsf")
            
            # Wait for list to load
            wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Thêm mới')] | //a[contains(., 'Thêm mới')]")))
            
            # Additional wait to ensure data table populates
            time.sleep(3) 
            
            # Dùng đường dẫn tuyệt đối an toàn hơn trên các môi trường Cloud
            import tempfile
            temp_dir = tempfile.gettempdir()
            screenshot_name = os.path.join(temp_dir, f"guest_list_{int(time.time())}.png")
            
            # 2. Xử lý lấy chiều cao an toàn
            try:
                height = driver.execute_script("return document.body.scrollHeight")
                driver.set_window_size(1920, int(height) + 200)
            except Exception as resize_err:
                st.warning(f"⚠️ Không thể mở rộng toàn màn hình: {resize_err}. Đang chụp ảnh ở kích thước mặc định.")
            
            # 3. Chụp và lưu ảnh
            driver.save_screenshot(screenshot_name)
            
            st.success(f"🖼 Screenshot saved locally as `{screenshot_name}`")
            st.image(screenshot_name, caption="Final Guest List")
            
            # 4. Upload to Google Drive
            st.info("☁️ Uploading screenshot to Google Drive...")
            file_id = upload_screenshot_to_drive(screenshot_name)
            
            if file_id:
                drive_link = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
                st.success(f"✅ Uploaded to Google Drive successfully!")
                st.markdown(f"**[🔗 Click here to view the screenshot on Google Drive]({drive_link})**")
            else:
                st.error("❌ Failed to upload screenshot to Google Drive. Check `upload_screenshot_to_drive` logic or credentials.")
                
        except Exception as ss_err:
            st.error(f"Failed to capture or upload the final screenshot: {ss_err}")

# --- 3. THE APP INTERFACE ---
st.title("🛂 Da Nang Guest Registration Bot")
st.write("Upload a passport photo to auto-fill the police declaration.")

# Sidebar Configuration
st.sidebar.header("🛠 Configuration")
api_key = DEFAULT_API_KEY # Hidden from users, loaded automatically
use_headless = st.sidebar.checkbox("👻 Run in Headless Mode", value=True, help="Uncheck to see the browser window popup locally.")

st.sidebar.divider()
st.sidebar.subheader("🏠 Listing Settings")
selected_listing = st.sidebar.selectbox("Select Listing", options=list(LISTINGS.keys()))
credentials = LISTINGS[selected_listing]

st.sidebar.divider()
st.sidebar.subheader("🗓 Stay Details")
# Default to Today for Arrival
arrival_dt = datetime.date.today()
# Default to Tomorrow for Departure
default_dep = arrival_dt + datetime.timedelta(days=1)
departure_dt = st.sidebar.date_input("Expected Departure", value=default_dep, min_value=arrival_dt)

str_arrival = arrival_dt.strftime("%d/%m/%Y")
str_departure = departure_dt.strftime("%d/%m/%Y")
st.sidebar.info(f"**Arrival:** {str_arrival}\n\n**Departure:** {str_departure}")

# File Uploader
uploaded_files = st.file_uploader("Choose passport images...", type=["jpg", "png", "jpeg"], accept_multiple_files=True)

if uploaded_files and api_key:
    # Show the images in a grid or carousel
    st.write(f"📂 {len(uploaded_files)} files uploaded.")
    
    if st.button("🚀 Extract & Register Batch"):
        all_extracted_data = []
        progress_bar = st.progress(0)
        
        with st.spinner("👀 Reading all passports..."):
            for i, file in enumerate(uploaded_files):
                try:
                    st.write(f"Reading {file.name}...")
                    data = extract_passport_data(file, api_key)
                    all_extracted_data.append(data)
                    progress_bar.progress((i + 1) / len(uploaded_files))
                except Exception as e:
                    st.error(f"Error reading {file.name}: {e}")
            
            if all_extracted_data:
                st.write("### ✅ Extracted Data Overview")
                st.dataframe(all_extracted_data)
                
                # Step 2: Run Bot for the whole list
                run_automation(all_extracted_data, credentials['username'], credentials['password'], str_arrival, str_departure, selected_listing, use_headless)
elif not api_key:
    st.warning("⚠️ API Key not found. Please ensure it is configured in your Streamlit Cloud Secrets.")
